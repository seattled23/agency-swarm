from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
import asyncio
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import deque

load_dotenv()

class BehaviorCategory(str, Enum):
    NORMAL = "normal"
    ANOMALOUS = "anomalous"
    SUSPICIOUS = "suspicious"
    DANGEROUS = "dangerous"

class ActionType(str, Enum):
    OPERATION = "operation"
    COMMUNICATION = "communication"
    RESOURCE_USE = "resource_use"
    SYSTEM_CALL = "system_call"

@dataclass
class BehaviorMetrics:
    pattern_score: float
    anomaly_score: float
    risk_indicators: List[str]
    recent_actions: List[dict]
    behavior_category: BehaviorCategory

class BehaviorAnalysisTool(BaseTool):
    """
    Advanced tool for analyzing agent behavior patterns and detecting
    potential anomalies or misalignment in real-time.
    """
    
    agent_id: str = Field(
        ..., description="ID of the agent to analyze"
    )
    analysis_window: int = Field(
        100, description="Number of recent actions to analyze"
    )
    anomaly_threshold: float = Field(
        0.8, description="Threshold for anomaly detection (0-1)"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.db_path = Path('project_data/behavior_analysis.db')
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_database()
        
        # Initialize behavior tracking
        self.recent_actions = deque(maxlen=self.analysis_window)
        self.behavior_patterns = {}
        self.anomaly_scores = []

    def initialize_database(self):
        """Initialize the SQLite database for behavior analysis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_actions (
                id INTEGER PRIMARY KEY,
                agent_id TEXT,
                action_type TEXT,
                action_data TEXT,
                timestamp TEXT,
                context TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS behavior_patterns (
                id INTEGER PRIMARY KEY,
                agent_id TEXT,
                pattern_type TEXT,
                pattern_data TEXT,
                frequency REAL,
                timestamp TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomaly_records (
                id INTEGER PRIMARY KEY,
                agent_id TEXT,
                anomaly_type TEXT,
                severity REAL,
                details TEXT,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    async def analyze_behavior(self) -> BehaviorMetrics:
        """Analyze agent behavior patterns and detect anomalies."""
        try:
            # Get recent actions
            recent_actions = await self.get_recent_actions()
            
            # Update behavior patterns
            self.update_behavior_patterns(recent_actions)
            
            # Calculate pattern score
            pattern_score = self.calculate_pattern_score(recent_actions)
            
            # Detect anomalies
            anomaly_score = self.detect_anomalies(recent_actions)
            
            # Identify risk indicators
            risk_indicators = self.identify_risk_indicators(
                recent_actions,
                pattern_score,
                anomaly_score
            )
            
            # Determine behavior category
            behavior_category = self.categorize_behavior(
                pattern_score,
                anomaly_score,
                risk_indicators
            )
            
            # Create metrics
            metrics = BehaviorMetrics(
                pattern_score=pattern_score,
                anomaly_score=anomaly_score,
                risk_indicators=risk_indicators,
                recent_actions=recent_actions,
                behavior_category=behavior_category
            )
            
            # Record analysis results
            self.record_behavior_analysis(metrics)
            
            return metrics
            
        except Exception as e:
            return f"Error analyzing behavior: {str(e)}"

    async def get_recent_actions(self) -> List[dict]:
        """Get recent agent actions from the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT action_type, action_data, timestamp, context
                FROM agent_actions
                WHERE agent_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (
                self.agent_id,
                self.analysis_window
            ))
            
            actions = []
            for row in cursor.fetchall():
                actions.append({
                    'type': row[0],
                    'data': json.loads(row[1]),
                    'timestamp': row[2],
                    'context': json.loads(row[3])
                })
            
            conn.close()
            return actions
            
        except Exception as e:
            return []

    def update_behavior_patterns(self, actions: List[dict]):
        """Update known behavior patterns based on recent actions."""
        try:
            # Extract patterns from actions
            new_patterns = self.extract_patterns(actions)
            
            # Update pattern frequencies
            for pattern in new_patterns:
                pattern_key = json.dumps(pattern)
                if pattern_key in self.behavior_patterns:
                    self.behavior_patterns[pattern_key]['frequency'] += 1
                else:
                    self.behavior_patterns[pattern_key] = {
                        'pattern': pattern,
                        'frequency': 1,
                        'first_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
            
            # Record updated patterns
            self.record_behavior_patterns()
            
        except Exception as e:
            logging.error(f"Error updating behavior patterns: {str(e)}")

    def extract_patterns(self, actions: List[dict]) -> List[dict]:
        """Extract behavior patterns from actions."""
        patterns = []
        
        # Analyze action sequences
        for i in range(len(actions) - 1):
            pattern = {
                'action_sequence': [actions[i]['type'], actions[i+1]['type']],
                'context': actions[i]['context'],
                'time_delta': self.calculate_time_delta(
                    actions[i]['timestamp'],
                    actions[i+1]['timestamp']
                )
            }
            patterns.append(pattern)
        
        return patterns

    def calculate_time_delta(self, timestamp1: str, timestamp2: str) -> float:
        """Calculate time difference between timestamps in seconds."""
        t1 = datetime.strptime(timestamp1, '%Y-%m-%d %H:%M:%S')
        t2 = datetime.strptime(timestamp2, '%Y-%m-%d %H:%M:%S')
        return abs((t2 - t1).total_seconds())

    def calculate_pattern_score(self, actions: List[dict]) -> float:
        """Calculate pattern matching score for recent actions."""
        try:
            if not actions:
                return 1.0
            
            # Extract current patterns
            current_patterns = self.extract_patterns(actions)
            
            # Calculate pattern match ratio
            matched_patterns = 0
            for pattern in current_patterns:
                pattern_key = json.dumps(pattern)
                if pattern_key in self.behavior_patterns:
                    matched_patterns += 1
            
            return matched_patterns / len(current_patterns) if current_patterns else 1.0
            
        except Exception as e:
            logging.error(f"Error calculating pattern score: {str(e)}")
            return 0.0

    def detect_anomalies(self, actions: List[dict]) -> float:
        """Detect anomalies in recent actions."""
        try:
            if not actions:
                return 0.0
            
            # Calculate action frequencies
            action_freq = {}
            for action in actions:
                action_type = action['type']
                action_freq[action_type] = action_freq.get(action_type, 0) + 1
            
            # Calculate entropy
            total_actions = len(actions)
            entropy = 0
            for freq in action_freq.values():
                prob = freq / total_actions
                entropy -= prob * np.log2(prob)
            
            # Normalize entropy to 0-1 range
            max_entropy = np.log2(len(action_freq))
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
            
            # Update anomaly scores
            self.anomaly_scores.append(normalized_entropy)
            if len(self.anomaly_scores) > self.analysis_window:
                self.anomaly_scores.pop(0)
            
            # Calculate anomaly score as deviation from mean
            mean_entropy = np.mean(self.anomaly_scores)
            std_entropy = np.std(self.anomaly_scores)
            
            if std_entropy == 0:
                return 0.0
            
            z_score = abs(normalized_entropy - mean_entropy) / std_entropy
            anomaly_score = 1 - (1 / (1 + z_score))
            
            return anomaly_score
            
        except Exception as e:
            logging.error(f"Error detecting anomalies: {str(e)}")
            return 0.0

    def identify_risk_indicators(self, actions: List[dict], pattern_score: float, anomaly_score: float) -> List[str]:
        """Identify potential risk indicators in behavior."""
        risk_indicators = []
        
        # Check pattern score
        if pattern_score < 0.6:
            risk_indicators.append("Unusual behavior patterns detected")
        
        # Check anomaly score
        if anomaly_score > self.anomaly_threshold:
            risk_indicators.append("High anomaly score detected")
        
        # Check action frequencies
        action_freq = {}
        for action in actions:
            action_type = action['type']
            action_freq[action_type] = action_freq.get(action_type, 0) + 1
            
            # Check for high-frequency actions
            if action_freq[action_type] > len(actions) * 0.5:
                risk_indicators.append(f"High frequency of {action_type} actions")
        
        # Check for rapid sequences
        for i in range(len(actions) - 1):
            time_delta = self.calculate_time_delta(
                actions[i]['timestamp'],
                actions[i+1]['timestamp']
            )
            if time_delta < 0.1:  # Less than 100ms between actions
                risk_indicators.append("Rapid action sequence detected")
                break
        
        return risk_indicators

    def categorize_behavior(self, pattern_score: float, anomaly_score: float, risk_indicators: List[str]) -> BehaviorCategory:
        """Categorize behavior based on analysis results."""
        if anomaly_score > 0.9 or len(risk_indicators) > 3:
            return BehaviorCategory.DANGEROUS
        elif anomaly_score > 0.7 or len(risk_indicators) > 1:
            return BehaviorCategory.SUSPICIOUS
        elif anomaly_score > self.anomaly_threshold:
            return BehaviorCategory.ANOMALOUS
        else:
            return BehaviorCategory.NORMAL

    def record_behavior_analysis(self, metrics: BehaviorMetrics):
        """Record behavior analysis results."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Record anomaly if detected
            if metrics.anomaly_score > self.anomaly_threshold:
                cursor.execute('''
                    INSERT INTO anomaly_records
                    (agent_id, anomaly_type, severity, details, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    self.agent_id,
                    metrics.behavior_category.value,
                    metrics.anomaly_score,
                    json.dumps(metrics.risk_indicators),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error recording behavior analysis: {str(e)}")

    def record_behavior_patterns(self):
        """Record updated behavior patterns."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for pattern_data in self.behavior_patterns.values():
                cursor.execute('''
                    INSERT INTO behavior_patterns
                    (agent_id, pattern_type, pattern_data, frequency, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    self.agent_id,
                    'sequence',
                    json.dumps(pattern_data['pattern']),
                    pattern_data['frequency'],
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error recording behavior patterns: {str(e)}")

    async def run(self):
        """Execute the behavior analysis action."""
        try:
            # Perform behavior analysis
            metrics = await self.analyze_behavior()
            
            return {
                'agent_id': self.agent_id,
                'behavior_metrics': metrics,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return f"Error in behavior analysis: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    analyzer = BehaviorAnalysisTool(
        agent_id="test_agent",
        analysis_window=100,
        anomaly_threshold=0.8
    )
    asyncio.run(analyzer.run()) 