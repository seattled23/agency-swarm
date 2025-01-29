from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import sqlite3
from pathlib import Path
import numpy as np
from collections import defaultdict
import torch
import torch.nn as nn
import torch.nn.functional as F

load_dotenv()

class TitanTransformerBlock(nn.Module):
    """
    Implementation inspired by Google DeepMind's Titan architecture.
    Incorporates mixture-of-experts and gated attention mechanisms.
    """
    def __init__(self, d_model, n_heads, d_ff, n_experts=4):
        super().__init__()
        self.attention = nn.MultiheadAttention(d_model, n_heads)
        self.experts = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model, d_ff),
                nn.ReLU(),
                nn.Linear(d_ff, d_model)
            ) for _ in range(n_experts)
        ])
        self.gate = nn.Linear(d_model, n_experts)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        
    def forward(self, x, mask=None):
        # Multi-head attention with residual connection
        attended = self.attention(x, x, x, attn_mask=mask)[0]
        x = self.norm1(x + attended)
        
        # Mixture of experts with gating
        gate_weights = F.softmax(self.gate(x), dim=-1)
        expert_outputs = torch.stack([expert(x) for expert in self.experts])
        output = torch.sum(gate_weights.unsqueeze(-1) * expert_outputs, dim=0)
        
        return self.norm2(x + output)

class Transformer2Router:
    """
    Implementation inspired by Sakana AI's Transformer-2 architecture.
    Focuses on dynamic routing and adaptive computation.
    """
    def __init__(self, n_agents, context_dim):
        self.n_agents = n_agents
        self.context_dim = context_dim
        self.routing_table = defaultdict(dict)
        self.importance_scores = defaultdict(float)
        
    def update_routing(self, from_agent, to_agent, context, importance):
        """
        Update routing information between agents.
        """
        key = f"{from_agent}_{to_agent}"
        self.routing_table[key]['context'] = context
        self.routing_table[key]['last_update'] = datetime.now()
        self.importance_scores[key] = importance
        
    def get_route(self, from_agent, to_agent):
        """
        Get routing information between agents.
        """
        key = f"{from_agent}_{to_agent}"
        return self.routing_table.get(key, None)
        
    def prune_routes(self, threshold=0.3):
        """
        Remove low-importance routes to optimize context usage.
        """
        keys_to_remove = []
        for key, score in self.importance_scores.items():
            if score < threshold:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.routing_table[key]
            del self.importance_scores[key]

class ContextManagementTool(BaseTool):
    """
    Advanced context management tool incorporating Titan and Transformer-2 concepts.
    Manages context windows, routing, and information flow between agents.
    """
    
    action: str = Field(
        ..., description="Action to perform ('update_context', 'get_context', 'optimize_routing', 'analyze_context')"
    )
    agent_id: str = Field(
        None, description="ID of the agent (optional)"
    )
    context_data: dict = Field(
        None, description="Context data to update (optional)"
    )
    target_agent_id: str = Field(
        None, description="Target agent ID for routing (optional)"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.db_path = Path('project_data/context_management.db')
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize Titan and Transformer-2 components
        self.transformer = TitanTransformerBlock(
            d_model=512,  # Context embedding dimension
            n_heads=8,    # Number of attention heads
            d_ff=2048,    # Feed-forward dimension
            n_experts=4   # Number of expert networks
        )
        self.router = Transformer2Router(
            n_agents=5,       # Number of agents in the system
            context_dim=512   # Context dimension
        )
        
        self.initialize_database()

    def initialize_database(self):
        """
        Initialize the SQLite database for context management.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS context_windows (
                id INTEGER PRIMARY KEY,
                agent_id TEXT,
                context_data TEXT,
                importance_score REAL,
                timestamp TEXT,
                last_access TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS context_routes (
                id INTEGER PRIMARY KEY,
                from_agent TEXT,
                to_agent TEXT,
                route_data TEXT,
                importance_score REAL,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def update_context(self, agent_id, context_data):
        """
        Update context for an agent using Titan architecture for processing.
        """
        # Convert context data to tensor for Titan processing
        context_tensor = torch.tensor(self.encode_context(context_data)).float()
        processed_context = self.transformer(context_tensor.unsqueeze(0))
        
        # Store processed context
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO context_windows
            (agent_id, context_data, importance_score, timestamp, last_access)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            agent_id,
            json.dumps(context_data),
            float(torch.mean(processed_context).item()),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        conn.close()
        
        return "Context updated successfully"

    def get_context(self, agent_id, target_agent_id=None):
        """
        Get context for an agent, optionally with routing to target agent.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if target_agent_id:
            # Get routed context using Transformer-2 routing
            route = self.router.get_route(agent_id, target_agent_id)
            if route:
                cursor.execute('''
                    SELECT context_data, importance_score
                    FROM context_routes
                    WHERE from_agent = ? AND to_agent = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (agent_id, target_agent_id))
            else:
                return "No route found between agents"
        else:
            # Get agent's own context
            cursor.execute('''
                SELECT context_data, importance_score
                FROM context_windows
                WHERE agent_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (agent_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'context': json.loads(result[0]),
                'importance_score': result[1]
            }
        return "No context found"

    def optimize_routing(self):
        """
        Optimize context routing using Transformer-2 concepts.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all routes
        cursor.execute('SELECT * FROM context_routes')
        routes = cursor.fetchall()
        
        # Apply Transformer-2 routing optimization
        self.router.prune_routes()
        
        # Update routes in database
        cursor.execute('DELETE FROM context_routes WHERE importance_score < 0.3')
        conn.commit()
        conn.close()
        
        return "Routing optimized successfully"

    def analyze_context(self, agent_id):
        """
        Analyze context usage and patterns using Titan architecture.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT context_data, importance_score, timestamp
            FROM context_windows
            WHERE agent_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (agent_id,))
        
        contexts = cursor.fetchall()
        conn.close()
        
        if not contexts:
            return "No context history found"
        
        # Analyze context patterns using Titan
        context_tensors = [
            torch.tensor(self.encode_context(json.loads(ctx[0]))).float()
            for ctx in contexts
        ]
        context_stack = torch.stack(context_tensors)
        analyzed_context = self.transformer(context_stack)
        
        # Generate analysis results
        analysis = {
            'context_coherence': float(torch.mean(analyzed_context).item()),
            'importance_trend': [float(ctx[1]) for ctx in contexts],
            'usage_pattern': self.analyze_usage_pattern([ctx[2] for ctx in contexts]),
            'recommendations': self.generate_recommendations(analyzed_context)
        }
        
        return analysis

    def encode_context(self, context_data):
        """
        Encode context data for neural processing.
        """
        # Simple encoding for demonstration
        # In production, use more sophisticated encoding methods
        return np.array(list(str(context_data).encode())).reshape(-1, 512)

    def analyze_usage_pattern(self, timestamps):
        """
        Analyze context usage patterns over time.
        """
        timestamps = [datetime.strptime(ts, '%Y-%m-%d %H:%M:%S') for ts in timestamps]
        intervals = [(timestamps[i] - timestamps[i+1]).total_seconds() 
                    for i in range(len(timestamps)-1)]
        
        return {
            'average_interval': sum(intervals) / len(intervals) if intervals else 0,
            'pattern_type': 'regular' if np.std(intervals) < 3600 else 'irregular'
        }

    def generate_recommendations(self, analyzed_context):
        """
        Generate recommendations based on context analysis.
        """
        coherence = float(torch.mean(analyzed_context).item())
        
        recommendations = []
        if coherence < 0.3:
            recommendations.append("Consider consolidating context information")
        if coherence > 0.8:
            recommendations.append("Context information may be redundant")
        if torch.std(analyzed_context).item() > 0.5:
            recommendations.append("High context variability detected")
        
        return recommendations

    def run(self):
        """
        Execute the context management action.
        """
        try:
            if self.action == 'update_context':
                return str(self.update_context(self.agent_id, self.context_data))
            elif self.action == 'get_context':
                return str(self.get_context(self.agent_id, self.target_agent_id))
            elif self.action == 'optimize_routing':
                return str(self.optimize_routing())
            elif self.action == 'analyze_context':
                return str(self.analyze_context(self.agent_id))
            else:
                return f"Unknown action: {self.action}"
            
        except Exception as e:
            return f"Error in context management: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    tool = ContextManagementTool(
        action="analyze_context",
        agent_id="market_analyst"
    )
    print(tool.run()) 