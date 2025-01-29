from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import sqlite3
from pathlib import Path
import networkx as nx
from typing import List, Dict
import yaml

load_dotenv()

class WorkflowManagementTool(BaseTool):
    """
    A tool for managing, generating, and modifying agent workflows.
    Handles workflow creation, optimization, and validation.
    """
    
    action: str = Field(
        ..., description="Action to perform ('create_workflow', 'modify_workflow', 'analyze_workflow', 'validate_workflow')"
    )
    workflow_name: str = Field(
        None, description="Name of the workflow (optional)"
    )
    workflow_data: dict = Field(
        None, description="Workflow configuration data (optional)"
    )
    modifications: List[Dict] = Field(
        None, description="List of modifications to apply (optional)"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.db_path = Path('project_data/workflows.db')
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_database()

    def initialize_database(self):
        """
        Initialize the SQLite database for workflow management.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                configuration TEXT,
                status TEXT,
                created_at TEXT,
                updated_at TEXT,
                version INTEGER,
                dependencies TEXT,
                validation_status TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_history (
                id INTEGER PRIMARY KEY,
                workflow_id INTEGER,
                modification TEXT,
                timestamp TEXT,
                author TEXT,
                version INTEGER,
                FOREIGN KEY (workflow_id) REFERENCES workflows (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def create_workflow(self, name: str, configuration: dict):
        """
        Create a new workflow with specified configuration.
        """
        # Validate workflow configuration
        if not self.validate_workflow_config(configuration):
            return "Invalid workflow configuration"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO workflows
                (name, configuration, status, created_at, updated_at, version, validation_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                name,
                json.dumps(configuration),
                'active',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                1,
                'validated'
            ))
            
            workflow_id = cursor.lastrowid
            
            # Create workflow graph
            self.create_workflow_graph(configuration, workflow_id)
            
            conn.commit()
            return f"Workflow '{name}' created successfully"
            
        except Exception as e:
            conn.rollback()
            return f"Error creating workflow: {str(e)}"
        finally:
            conn.close()

    def modify_workflow(self, name: str, modifications: List[Dict]):
        """
        Modify an existing workflow with specified changes.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get current workflow
            cursor.execute('SELECT configuration, version FROM workflows WHERE name = ?', (name,))
            result = cursor.fetchone()
            
            if not result:
                return f"Workflow '{name}' not found"
            
            current_config = json.loads(result[0])
            current_version = result[1]
            
            # Apply modifications
            modified_config = self.apply_modifications(current_config, modifications)
            
            # Validate modified configuration
            if not self.validate_workflow_config(modified_config):
                return "Invalid workflow modifications"
            
            # Update workflow
            cursor.execute('''
                UPDATE workflows
                SET configuration = ?, updated_at = ?, version = version + 1
                WHERE name = ?
            ''', (
                json.dumps(modified_config),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                name
            ))
            
            # Record modifications
            for mod in modifications:
                cursor.execute('''
                    INSERT INTO workflow_history
                    (workflow_id, modification, timestamp, author, version)
                    VALUES (
                        (SELECT id FROM workflows WHERE name = ?),
                        ?, ?, ?, ?
                    )
                ''', (
                    name,
                    json.dumps(mod),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'system',
                    current_version + 1
                ))
            
            conn.commit()
            return f"Workflow '{name}' modified successfully"
            
        except Exception as e:
            conn.rollback()
            return f"Error modifying workflow: {str(e)}"
        finally:
            conn.close()

    def analyze_workflow(self, name: str):
        """
        Analyze workflow structure and performance.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT w.*, GROUP_CONCAT(h.modification) as history
                FROM workflows w
                LEFT JOIN workflow_history h ON w.id = h.workflow_id
                WHERE w.name = ?
                GROUP BY w.id
            ''', (name,))
            
            result = cursor.fetchone()
            if not result:
                return f"Workflow '{name}' not found"
            
            config = json.loads(result[2])
            history = result[8]
            
            # Create graph representation
            G = nx.DiGraph()
            self.build_graph_from_config(G, config)
            
            # Analyze workflow
            analysis = {
                'name': name,
                'version': result[6],
                'status': result[3],
                'metrics': {
                    'node_count': G.number_of_nodes(),
                    'edge_count': G.number_of_edges(),
                    'complexity': nx.density(G),
                    'critical_path_length': len(nx.dag_longest_path(G))
                },
                'bottlenecks': self.identify_bottlenecks(G),
                'modification_history': json.loads(f"[{history}]") if history else [],
                'recommendations': self.generate_workflow_recommendations(G, config)
            }
            
            return analysis
            
        except Exception as e:
            return f"Error analyzing workflow: {str(e)}"
        finally:
            conn.close()

    def validate_workflow(self, name: str):
        """
        Validate workflow configuration and dependencies.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT configuration FROM workflows WHERE name = ?', (name,))
            result = cursor.fetchone()
            
            if not result:
                return f"Workflow '{name}' not found"
            
            config = json.loads(result[0])
            
            validation_results = {
                'structure_valid': self.validate_workflow_config(config),
                'dependency_check': self.validate_dependencies(config),
                'cycle_check': self.check_for_cycles(config),
                'resource_check': self.validate_resource_requirements(config),
                'security_check': self.validate_security_constraints(config)
            }
            
            # Update validation status
            status = 'valid' if all(validation_results.values()) else 'invalid'
            cursor.execute('''
                UPDATE workflows
                SET validation_status = ?
                WHERE name = ?
            ''', (status, name))
            
            conn.commit()
            return validation_results
            
        except Exception as e:
            return f"Error validating workflow: {str(e)}"
        finally:
            conn.close()

    def validate_workflow_config(self, config: dict) -> bool:
        """
        Validate workflow configuration structure.
        """
        required_fields = ['nodes', 'edges', 'parameters']
        if not all(field in config for field in required_fields):
            return False
        
        # Validate nodes
        for node in config['nodes']:
            if 'id' not in node or 'type' not in node:
                return False
        
        # Validate edges
        for edge in config['edges']:
            if 'source' not in edge or 'target' not in edge:
                return False
        
        return True

    def apply_modifications(self, config: dict, modifications: List[Dict]) -> dict:
        """
        Apply modifications to workflow configuration.
        """
        modified_config = config.copy()
        
        for mod in modifications:
            if mod['type'] == 'add_node':
                modified_config['nodes'].append(mod['data'])
            elif mod['type'] == 'remove_node':
                modified_config['nodes'] = [n for n in modified_config['nodes'] 
                                         if n['id'] != mod['node_id']]
            elif mod['type'] == 'modify_node':
                for node in modified_config['nodes']:
                    if node['id'] == mod['node_id']:
                        node.update(mod['data'])
            elif mod['type'] == 'add_edge':
                modified_config['edges'].append(mod['data'])
            elif mod['type'] == 'remove_edge':
                modified_config['edges'] = [e for e in modified_config['edges']
                                         if e['source'] != mod['source'] or 
                                         e['target'] != mod['target']]
        
        return modified_config

    def create_workflow_graph(self, config: dict, workflow_id: int):
        """
        Create and store workflow graph representation.
        """
        G = nx.DiGraph()
        self.build_graph_from_config(G, config)
        
        # Store graph data
        graph_data = nx.node_link_data(G)
        with open(f'project_data/workflow_graphs/{workflow_id}.json', 'w') as f:
            json.dump(graph_data, f)

    def build_graph_from_config(self, G: nx.DiGraph, config: dict):
        """
        Build networkx graph from workflow configuration.
        """
        # Add nodes
        for node in config['nodes']:
            G.add_node(node['id'], **node)
        
        # Add edges
        for edge in config['edges']:
            G.add_edge(edge['source'], edge['target'], **edge)

    def identify_bottlenecks(self, G: nx.DiGraph) -> List[str]:
        """
        Identify potential bottlenecks in workflow.
        """
        bottlenecks = []
        
        # Check for high centrality nodes
        centrality = nx.betweenness_centrality(G)
        for node, score in centrality.items():
            if score > 0.5:  # High centrality threshold
                bottlenecks.append({
                    'node': node,
                    'type': 'high_centrality',
                    'score': score
                })
        
        # Check for critical paths
        critical_path = nx.dag_longest_path(G)
        if len(critical_path) > 5:  # Long critical path threshold
            bottlenecks.append({
                'type': 'long_critical_path',
                'path': critical_path
            })
        
        return bottlenecks

    def generate_workflow_recommendations(self, G: nx.DiGraph, config: dict) -> List[str]:
        """
        Generate recommendations for workflow optimization.
        """
        recommendations = []
        
        # Check for parallel execution opportunities
        components = list(nx.weakly_connected_components(G))
        if len(components) > 1:
            recommendations.append("Consider parallel execution for independent components")
        
        # Check for redundant paths
        if nx.number_of_edges(G) > 2 * nx.number_of_nodes(G):
            recommendations.append("Consider simplifying workflow structure")
        
        # Check for resource optimization
        if 'parameters' in config and 'resources' in config['parameters']:
            resources = config['parameters']['resources']
            if any(r.get('utilization', 0) < 0.5 for r in resources):
                recommendations.append("Consider optimizing resource allocation")
        
        return recommendations

    def run(self):
        """
        Execute the workflow management action.
        """
        try:
            if self.action == 'create_workflow':
                return str(self.create_workflow(self.workflow_name, self.workflow_data))
            elif self.action == 'modify_workflow':
                return str(self.modify_workflow(self.workflow_name, self.modifications))
            elif self.action == 'analyze_workflow':
                return str(self.analyze_workflow(self.workflow_name))
            elif self.action == 'validate_workflow':
                return str(self.validate_workflow(self.workflow_name))
            else:
                return f"Unknown action: {self.action}"
            
        except Exception as e:
            return f"Error in workflow management: {str(e)}"

if __name__ == "__main__":
    # Test the tool
    tool = WorkflowManagementTool(
        action="create_workflow",
        workflow_name="test_workflow",
        workflow_data={
            "nodes": [
                {"id": "start", "type": "start"},
                {"id": "process", "type": "task"},
                {"id": "end", "type": "end"}
            ],
            "edges": [
                {"source": "start", "target": "process"},
                {"source": "process", "target": "end"}
            ],
            "parameters": {
                "resources": [
                    {"name": "cpu", "utilization": 0.7}
                ]
            }
        }
    )
    print(tool.run()) 