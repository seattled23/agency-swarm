from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import ast
import json
from datetime import datetime
import sqlite3
from pathlib import Path
import radon.complexity as cc
import radon.metrics as rm
import radon.raw as rr
from pylint import epylint as lint
import networkx as nx
from typing import List, Dict
import torch
import torch.nn as nn

load_dotenv()

class CodeAnalysisTool(BaseTool):
    """
    Advanced code analysis tool that evaluates code quality, complexity,
    and identifies potential improvement opportunities.
    """
    
    action: str = Field(
        ..., description="Action to perform ('analyze_code', 'suggest_improvements', 'evaluate_architecture')"
    )
    target_path: str = Field(
        None, description="Path to the code file or directory to analyze"
    )
    analysis_type: str = Field(
        None, description="Type of analysis to perform ('quality', 'complexity', 'architecture', 'all')"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.db_path = Path('project_data/code_analysis.db')
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_database()

    def initialize_database(self):
        """
        Initialize the SQLite database for storing analysis results.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_metrics (
                id INTEGER PRIMARY KEY,
                file_path TEXT,
                metrics TEXT,
                timestamp TEXT,
                suggestions TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS architecture_analysis (
                id INTEGER PRIMARY KEY,
                component TEXT,
                analysis TEXT,
                timestamp TEXT,
                improvement_suggestions TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def analyze_code(self, path: str):
        """
        Perform comprehensive code analysis.
        """
        if not os.path.exists(path):
            return f"Path not found: {path}"
        
        analysis_results = {
            'quality_metrics': self.analyze_code_quality(path),
            'complexity_metrics': self.analyze_complexity(path),
            'maintainability': self.calculate_maintainability_index(path),
            'dependencies': self.analyze_dependencies(path),
            'potential_issues': self.identify_potential_issues(path),
            'improvement_opportunities': self.identify_improvements(path)
        }
        
        # Store analysis results
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO code_metrics (file_path, metrics, timestamp, suggestions)
            VALUES (?, ?, ?, ?)
        ''', (
            path,
            json.dumps(analysis_results),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            json.dumps(analysis_results['improvement_opportunities'])
        ))
        
        conn.commit()
        conn.close()
        
        return analysis_results

    def analyze_code_quality(self, path: str) -> dict:
        """
        Analyze code quality using various metrics.
        """
        # Run pylint
        (pylint_stdout, pylint_stderr) = lint.py_run(path, return_std=True)
        pylint_output = pylint_stdout.getvalue()
        
        # Calculate raw metrics
        with open(path, 'r') as file:
            code = file.read()
            raw_metrics = rr.analyze(code)
        
        return {
            'pylint_score': self.extract_pylint_score(pylint_output),
            'loc': raw_metrics.loc,
            'lloc': raw_metrics.lloc,
            'sloc': raw_metrics.sloc,
            'comments': raw_metrics.comments,
            'multi': raw_metrics.multi,
            'blank': raw_metrics.blank,
            'single_comments': raw_metrics.single_comments
        }

    def analyze_complexity(self, path: str) -> dict:
        """
        Analyze code complexity using various metrics.
        """
        with open(path, 'r') as file:
            code = file.read()
        
        # Calculate complexity metrics
        complexity_metrics = {
            'cyclomatic_complexity': cc.cc_visit(code),
            'cognitive_complexity': self.calculate_cognitive_complexity(code),
            'halstead_metrics': rm.h_visit(code)
        }
        
        return complexity_metrics

    def calculate_cognitive_complexity(self, code: str) -> int:
        """
        Calculate cognitive complexity of the code.
        """
        tree = ast.parse(code)
        visitor = CognitiveComplexityVisitor()
        visitor.visit(tree)
        return visitor.complexity

    def calculate_maintainability_index(self, path: str) -> float:
        """
        Calculate maintainability index for the code.
        """
        with open(path, 'r') as file:
            code = file.read()
        
        # Calculate Halstead metrics
        h = rm.h_visit(code)
        
        # Calculate maintainability index
        mi = rm.mi_visit(code, True)
        
        return mi

    def analyze_dependencies(self, path: str) -> dict:
        """
        Analyze code dependencies and imports.
        """
        with open(path, 'r') as file:
            code = file.read()
        
        tree = ast.parse(code)
        
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for name in node.names:
                    imports.append(f"{module}.{name.name}")
        
        return {
            'direct_imports': imports,
            'dependency_graph': self.create_dependency_graph(imports)
        }

    def create_dependency_graph(self, imports: List[str]) -> dict:
        """
        Create a dependency graph from imports.
        """
        G = nx.DiGraph()
        
        for imp in imports:
            parts = imp.split('.')
            for i in range(len(parts)):
                if i > 0:
                    G.add_edge(parts[i-1], parts[i])
        
        return nx.node_link_data(G)

    def identify_potential_issues(self, path: str) -> List[dict]:
        """
        Identify potential code issues and anti-patterns.
        """
        with open(path, 'r') as file:
            code = file.read()
        
        tree = ast.parse(code)
        issues = []
        
        # Check for various code issues
        for node in ast.walk(tree):
            # Check for long functions
            if isinstance(node, ast.FunctionDef):
                if len(node.body) > 50:
                    issues.append({
                        'type': 'long_function',
                        'name': node.name,
                        'line': node.lineno,
                        'suggestion': 'Consider breaking down into smaller functions'
                    })
            
            # Check for deep nesting
            if isinstance(node, (ast.If, ast.For, ast.While)):
                nesting_level = self.get_nesting_level(node)
                if nesting_level > 3:
                    issues.append({
                        'type': 'deep_nesting',
                        'line': node.lineno,
                        'nesting_level': nesting_level,
                        'suggestion': 'Consider restructuring to reduce nesting'
                    })
        
        return issues

    def get_nesting_level(self, node: ast.AST) -> int:
        """
        Calculate the nesting level of an AST node.
        """
        level = 0
        parent = node
        while hasattr(parent, 'parent'):
            if isinstance(parent, (ast.If, ast.For, ast.While)):
                level += 1
            parent = parent.parent
        return level

    def identify_improvements(self, path: str) -> List[dict]:
        """
        Identify potential improvements and optimizations.
        """
        improvements = []
        
        # Analyze code quality
        quality_metrics = self.analyze_code_quality(path)
        if quality_metrics['pylint_score'] < 8.0:
            improvements.append({
                'type': 'code_quality',
                'description': 'Code quality score is below threshold',
                'suggestion': 'Review and address pylint warnings'
            })
        
        # Analyze complexity
        complexity_metrics = self.analyze_complexity(path)
        for func in complexity_metrics['cyclomatic_complexity']:
            if func.complexity > 10:
                improvements.append({
                    'type': 'complexity',
                    'function': func.name,
                    'description': f'High cyclomatic complexity ({func.complexity})',
                    'suggestion': 'Consider refactoring to reduce complexity'
                })
        
        # Analyze maintainability
        mi = self.calculate_maintainability_index(path)
        if mi < 65:
            improvements.append({
                'type': 'maintainability',
                'description': 'Low maintainability index',
                'suggestion': 'Improve code structure and documentation'
            })
        
        return improvements

    def extract_pylint_score(self, pylint_output: str) -> float:
        """
        Extract the pylint score from output.
        """
        try:
            score_line = [line for line in pylint_output.split('\n') 
                         if 'Your code has been rated at' in line][0]
            return float(score_line.split()[6].split('/')[0])
        except:
            return 0.0

    def run(self):
        """
        Execute the code analysis action.
        """
        try:
            if self.action == 'analyze_code':
                return str(self.analyze_code(self.target_path))
            elif self.action == 'suggest_improvements':
                return str(self.identify_improvements(self.target_path))
            elif self.action == 'evaluate_architecture':
                return str(self.analyze_dependencies(self.target_path))
            else:
                return f"Unknown action: {self.action}"
            
        except Exception as e:
            return f"Error in code analysis: {str(e)}"

class CognitiveComplexityVisitor(ast.NodeVisitor):
    """
    AST visitor for calculating cognitive complexity.
    """
    def __init__(self):
        self.complexity = 0
        self.nesting = 0
    
    def visit_If(self, node):
        self.complexity += (1 + self.nesting)
        self.nesting += 1
        self.generic_visit(node)
        self.nesting -= 1
    
    def visit_For(self, node):
        self.complexity += (1 + self.nesting)
        self.nesting += 1
        self.generic_visit(node)
        self.nesting -= 1
    
    def visit_While(self, node):
        self.complexity += (1 + self.nesting)
        self.nesting += 1
        self.generic_visit(node)
        self.nesting -= 1
    
    def visit_Try(self, node):
        self.complexity += (1 + self.nesting)
        self.nesting += 1
        self.generic_visit(node)
        self.nesting -= 1

if __name__ == "__main__":
    # Test the tool
    tool = CodeAnalysisTool(
        action="analyze_code",
        target_path="self_improvement_agent.py",
        analysis_type="all"
    )
    print(tool.run()) 