from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import sqlite3
from pathlib import Path
import ast
import astor
import autopep8
from typing import List, Dict
import difflib

load_dotenv()

class SelfImprovementTool(BaseTool):
    """
    A tool for analyzing, modifying, and upgrading agent code.
    Implements self-improvement capabilities using code analysis and transformation.
    """
    
    action: str = Field(
        ..., description="Action to perform ('analyze_code', 'propose_improvements', 'apply_improvements', 'validate_changes')"
    )
    target_file: str = Field(
        None, description="Path to the target file (optional)"
    )
    improvements: List[Dict] = Field(
        None, description="List of improvements to apply (optional)"
    )
    code_content: str = Field(
        None, description="Code content to analyze (optional)"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.db_path = Path('project_data/code_improvements.db')
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_database()

    def initialize_database(self):
        """
        Initialize the SQLite database for code improvements.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_improvements (
                id INTEGER PRIMARY KEY,
                file_path TEXT,
                improvement_type TEXT,
                description TEXT,
                changes TEXT,
                status TEXT,
                created_at TEXT,
                applied_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS improvement_history (
                id INTEGER PRIMARY KEY,
                improvement_id INTEGER,
                previous_version TEXT,
                new_version TEXT,
                timestamp TEXT,
                validation_result TEXT,
                FOREIGN KEY (improvement_id) REFERENCES code_improvements (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def analyze_code(self, file_path: str = None, code_content: str = None):
        """
        Analyze code structure and identify potential improvements.
        """
        try:
            # Parse code
            if file_path:
                with open(file_path, 'r') as f:
                    code_content = f.read()
            
            tree = ast.parse(code_content)
            analyzer = CodeAnalyzer()
            analyzer.visit(tree)
            
            # Generate analysis report
            analysis = {
                'complexity_metrics': analyzer.complexity_metrics,
                'potential_improvements': analyzer.get_improvement_suggestions(),
                'code_structure': {
                    'classes': len(analyzer.classes),
                    'functions': len(analyzer.functions),
                    'imports': analyzer.imports
                },
                'quality_metrics': self.calculate_quality_metrics(code_content)
            }
            
            return analysis
            
        except Exception as e:
            return f"Error analyzing code: {str(e)}"

    def propose_improvements(self, analysis_result: dict):
        """
        Propose code improvements based on analysis results.
        """
        improvements = []
        
        # Check complexity metrics
        if analysis_result['complexity_metrics']['cyclomatic_complexity'] > 10:
            improvements.append({
                'type': 'refactor',
                'target': 'complexity',
                'suggestion': 'Split complex functions into smaller units'
            })
        
        # Check code quality
        if analysis_result['quality_metrics']['maintainability_index'] < 65:
            improvements.append({
                'type': 'quality',
                'target': 'maintainability',
                'suggestion': 'Improve code documentation and structure'
            })
        
        # Check potential optimizations
        for improvement in analysis_result['potential_improvements']:
            improvements.append({
                'type': 'optimization',
                'target': improvement['target'],
                'suggestion': improvement['description']
            })
        
        return improvements

    def apply_improvements(self, file_path: str, improvements: List[Dict]):
        """
        Apply proposed improvements to the code.
        """
        try:
            with open(file_path, 'r') as f:
                original_code = f.read()
            
            # Create AST
            tree = ast.parse(original_code)
            transformer = CodeTransformer(improvements)
            modified_tree = transformer.visit(tree)
            
            # Generate modified code
            modified_code = astor.to_source(modified_tree)
            
            # Format code
            formatted_code = autopep8.fix_code(modified_code)
            
            # Generate diff
            diff = difflib.unified_diff(
                original_code.splitlines(keepends=True),
                formatted_code.splitlines(keepends=True),
                fromfile='original',
                tofile='modified'
            )
            
            # Store improvement record
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO code_improvements
                (file_path, improvement_type, description, changes, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                file_path,
                'multiple',
                json.dumps([imp['type'] for imp in improvements]),
                ''.join(diff),
                'pending',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            improvement_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO improvement_history
                (improvement_id, previous_version, new_version, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (
                improvement_id,
                original_code,
                formatted_code,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'status': 'success',
                'diff': ''.join(diff),
                'improvement_id': improvement_id
            }
            
        except Exception as e:
            return f"Error applying improvements: {str(e)}"

    def validate_changes(self, file_path: str, improvement_id: int):
        """
        Validate applied code improvements.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get improvement history
            cursor.execute('''
                SELECT new_version
                FROM improvement_history
                WHERE improvement_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (improvement_id,))
            
            result = cursor.fetchone()
            if not result:
                return "Improvement not found"
            
            modified_code = result[0]
            
            # Validate syntax
            try:
                ast.parse(modified_code)
            except SyntaxError as e:
                return f"Syntax validation failed: {str(e)}"
            
            # Run static analysis
            analysis = self.analyze_code(code_content=modified_code)
            
            # Update validation status
            cursor.execute('''
                UPDATE improvement_history
                SET validation_result = ?
                WHERE improvement_id = ?
            ''', (
                json.dumps(analysis),
                improvement_id
            ))
            
            cursor.execute('''
                UPDATE code_improvements
                SET status = ?, applied_at = ?
                WHERE id = ?
            ''', (
                'validated',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                improvement_id
            ))
            
            conn.commit()
            
            return {
                'status': 'success',
                'validation_result': analysis
            }
            
        except Exception as e:
            return f"Error validating changes: {str(e)}"
        finally:
            conn.close()

    def calculate_quality_metrics(self, code_content: str) -> dict:
        """
        Calculate code quality metrics.
        """
        metrics = {
            'maintainability_index': 0,
            'code_to_comment_ratio': 0,
            'average_function_length': 0
        }
        
        try:
            tree = ast.parse(code_content)
            
            # Calculate maintainability index
            # This is a simplified version
            loc = len(code_content.splitlines())
            comment_lines = len([l for l in code_content.splitlines() if l.strip().startswith('#')])
            
            metrics['maintainability_index'] = 100 - (loc * 0.1) + (comment_lines * 0.2)
            metrics['code_to_comment_ratio'] = comment_lines / loc if loc > 0 else 0
            
            # Calculate average function length
            function_lengths = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    end_lineno = node.end_lineno if hasattr(node, 'end_lineno') else node.lineno
                    function_lengths.append(end_lineno - node.lineno)
            
            metrics['average_function_length'] = (
                sum(function_lengths) / len(function_lengths)
                if function_lengths else 0
            )
            
        except Exception:
            pass
        
        return metrics

    def run(self):
        """
        Execute the self-improvement action.
        """
        try:
            if self.action == 'analyze_code':
                return str(self.analyze_code(self.target_file, self.code_content))
            elif self.action == 'propose_improvements':
                analysis = self.analyze_code(self.target_file, self.code_content)
                return str(self.propose_improvements(analysis))
            elif self.action == 'apply_improvements':
                return str(self.apply_improvements(self.target_file, self.improvements))
            elif self.action == 'validate_changes':
                return str(self.validate_changes(self.target_file, self.improvements[0]['improvement_id']))
            else:
                return f"Unknown action: {self.action}"
            
        except Exception as e:
            return f"Error in self-improvement: {str(e)}"

class CodeAnalyzer(ast.NodeVisitor):
    """
    AST visitor for analyzing code structure and metrics.
    """
    def __init__(self):
        self.complexity_metrics = {
            'cyclomatic_complexity': 0,
            'cognitive_complexity': 0
        }
        self.classes = []
        self.functions = []
        self.imports = []
        self.improvement_suggestions = []
        
    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        self.generic_visit(node)
        
    def visit_FunctionDef(self, node):
        self.functions.append(node.name)
        # Analyze function complexity
        self.analyze_complexity(node)
        self.generic_visit(node)
        
    def visit_Import(self, node):
        for name in node.names:
            self.imports.append(name.name)
            
    def visit_ImportFrom(self, node):
        for name in node.names:
            self.imports.append(f"{node.module}.{name.name}")
            
    def analyze_complexity(self, node):
        """
        Analyze function complexity metrics.
        """
        # Count branches
        branches = sum(1 for _ in ast.walk(node) if isinstance(_, (ast.If, ast.For, ast.While)))
        self.complexity_metrics['cyclomatic_complexity'] += branches + 1
        
        # Analyze cognitive complexity
        nesting_level = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While)):
                nesting_level += 1
                self.complexity_metrics['cognitive_complexity'] += nesting_level
            elif isinstance(child, ast.FunctionDef):
                nesting_level = 0
                
    def get_improvement_suggestions(self):
        """
        Generate improvement suggestions based on analysis.
        """
        suggestions = []
        
        # Check complexity
        if self.complexity_metrics['cyclomatic_complexity'] > 10:
            suggestions.append({
                'target': 'complexity',
                'description': 'High cyclomatic complexity detected'
            })
            
        # Check cognitive complexity
        if self.complexity_metrics['cognitive_complexity'] > 15:
            suggestions.append({
                'target': 'cognitive_complexity',
                'description': 'High cognitive complexity detected'
            })
            
        # Check number of imports
        if len(self.imports) > 15:
            suggestions.append({
                'target': 'imports',
                'description': 'Consider organizing imports'
            })
            
        return suggestions

class CodeTransformer(ast.NodeTransformer):
    """
    AST transformer for applying code improvements.
    """
    def __init__(self, improvements):
        self.improvements = improvements
        
    def visit_FunctionDef(self, node):
        """
        Transform function definitions based on improvements.
        """
        # Apply function-level improvements
        for improvement in self.improvements:
            if improvement['type'] == 'refactor' and improvement['target'] == 'complexity':
                # Split complex functions (simplified example)
                if len(node.body) > 10:
                    # Create helper function
                    helper = ast.FunctionDef(
                        name=f"{node.name}_helper",
                        args=node.args,
                        body=node.body[5:],
                        decorator_list=[]
                    )
                    # Update original function
                    node.body = node.body[:5] + [ast.Call(
                        func=ast.Name(id=helper.name, ctx=ast.Load()),
                        args=[ast.Name(id=arg.arg, ctx=ast.Load()) for arg in node.args.args],
                        keywords=[]
                    )]
                    return [helper, node]
        
        return node

if __name__ == "__main__":
    # Test the tool
    tool = SelfImprovementTool(
        action="analyze_code",
        target_file="example.py",
        code_content="""
def complex_function(x, y):
    result = 0
    for i in range(x):
        for j in range(y):
            if i % 2 == 0:
                if j % 2 == 0:
                    result += i * j
    return result
"""
    )
    print(tool.run()) 