"""
Content validation test suite for documentation.
Tests pattern consistency and example verification.
"""

import re
from pathlib import Path
from typing import List, Dict, Set, Optional
from collections import defaultdict

class ContentValidator:
    def __init__(self, docs_root: str = "docs"):
        self.docs_root = Path(docs_root)
        self.cache = {}
        self.pattern_definitions = defaultdict(list)
        self.examples = defaultdict(list)

    def get_file_content(self, filepath: str) -> Optional[str]:
        """Read and cache file content"""
        abs_path = self.docs_root / filepath
        if not abs_path.exists():
            return None

        if filepath not in self.cache:
            self.cache[filepath] = abs_path.read_text(encoding='utf-8')
        return self.cache[filepath]

    def extract_patterns(self, content: str) -> Dict[str, List[Dict]]:
        """Extract pattern definitions from content"""
        patterns = defaultdict(list)
        current_pattern = None
        pattern_content = []

        for line in content.split('\n'):
            # Look for pattern headers
            if re.match(r'^###\s+\d+\.\s+(.+?)\s+Patterns?$', line):
                if current_pattern and pattern_content:
                    patterns[current_pattern].append('\n'.join(pattern_content))
                current_pattern = re.match(r'^###\s+\d+\.\s+(.+?)\s+Patterns?$', line).group(1)
                pattern_content = []
            elif current_pattern:
                pattern_content.append(line)

        if current_pattern and pattern_content:
            patterns[current_pattern].append('\n'.join(pattern_content))

        return patterns

    def extract_examples(self, content: str) -> Dict[str, List[str]]:
        """Extract examples from content"""
        examples = defaultdict(list)
        current_type = None
        example_content = []

        # Look for code blocks and example sections
        code_blocks = re.finditer(r'```(?:\w+)?\n(.*?)\n```', content, re.DOTALL)
        for block in code_blocks:
            example_content = block.group(1)
            # Try to determine example type from context
            context = content[max(0, block.start() - 100):block.start()]
            type_match = re.search(r'(?:Example|Pattern):\s*(\w+(?:\s+\w+)*)', context)
            if type_match:
                current_type = type_match.group(1)
                examples[current_type].append(example_content)

        return examples

    def pattern_consistent(self, pattern_name: str) -> bool:
        """Check if pattern is consistently defined across documents"""
        pattern_defs = []

        # Collect all pattern definitions
        for filepath in self.docs_root.glob('**/*.md'):
            content = self.get_file_content(filepath.name)
            if content:
                patterns = self.extract_patterns(content)
                if pattern_name in patterns:
                    pattern_defs.extend(patterns[pattern_name])

        if not pattern_defs:
            return False

        # Check for consistency in structure and key elements
        key_elements = set()
        for definition in pattern_defs:
            elements = set(re.findall(r'^\s*[-*]\s+(.+)$', definition, re.MULTILINE))
            if not key_elements:
                key_elements = elements
            elif not elements.intersection(key_elements):
                return False

        return True

    def examples_match(self, pattern_name: str) -> bool:
        """Check if examples match pattern definitions"""
        examples_found = False

        for filepath in self.docs_root.glob('**/*.md'):
            content = self.get_file_content(filepath.name)
            if content:
                patterns = self.extract_patterns(content)
                if pattern_name in patterns:
                    examples = self.extract_examples(content)
                    if not any(pattern_name in example for example in examples.values()):
                        return False
                    examples_found = True

        return examples_found

    def examples_valid(self, example_type: str) -> bool:
        """Check if examples are valid"""
        examples_found = False

        for filepath in self.docs_root.glob('**/*.md'):
            content = self.get_file_content(filepath.name)
            if content:
                examples = self.extract_examples(content)
                if example_type in examples:
                    for example in examples[example_type]:
                        if not self._validate_example(example, example_type):
                            return False
                    examples_found = True

        return examples_found

    def _validate_example(self, example: str, example_type: str) -> bool:
        """Validate specific example based on type"""
        if example_type == "Code Examples":
            return self._validate_code_example(example)
        elif example_type == "Workflow Examples":
            return self._validate_workflow_example(example)
        elif example_type == "Decision Trees":
            return self._validate_decision_tree(example)
        elif example_type == "Error Handling":
            return self._validate_error_handling(example)
        elif example_type == "Recovery Procedures":
            return self._validate_recovery_procedure(example)
        return True

    def _validate_code_example(self, example: str) -> bool:
        """Validate code example"""
        # Check for basic code structure
        return bool(re.search(r'^\s*(?:def|class|import|from)\s+\w+', example, re.MULTILINE))

    def _validate_workflow_example(self, example: str) -> bool:
        """Validate workflow example"""
        # Check for workflow steps
        return bool(re.search(r'^\s*\d+\.\s+\w+', example, re.MULTILINE))

    def _validate_decision_tree(self, example: str) -> bool:
        """Validate decision tree"""
        # Check for decision points and branches
        return bool(re.search(r'(?:if|else|switch|case|when)\b', example))

    def _validate_error_handling(self, example: str) -> bool:
        """Validate error handling example"""
        # Check for error handling patterns
        return bool(re.search(r'(?:try|catch|except|error|failure)\b', example))

    def _validate_recovery_procedure(self, example: str) -> bool:
        """Validate recovery procedure"""
        # Check for recovery steps
        return bool(re.search(r'(?:recover|restore|repair|fix|solve)\b', example))

class TestContent:
    def setup_method(self):
        self.validator = ContentValidator()

    def test_pattern_consistency(self):
        """Test pattern consistency across documents"""
        patterns = [
            "Task Execution",
            "Resource Scaling",
            "Error Recovery",
            "Context Management",
            "Integration",
            "Performance Optimization",
        ]

        for pattern in patterns:
            assert self.validator.pattern_consistent(pattern), \
                f"Pattern '{pattern}' is not consistently defined"

            assert self.validator.examples_match(pattern), \
                f"Pattern '{pattern}' lacks matching examples"

    def test_examples(self):
        """Test example validity"""
        example_types = [
            "Code Examples",
            "Workflow Examples",
            "Decision Trees",
            "Error Handling",
            "Recovery Procedures",
        ]

        for type in example_types:
            assert self.validator.examples_valid(type), \
                f"Invalid examples found for type '{type}'"

def main():
    """Run content validation tests"""
    validator = ContentValidator()
    test = TestContent()
    test.setup_method()

    print("Running content validation tests...")

    try:
        test.test_pattern_consistency()
        print("✅ Pattern consistency test passed")
    except AssertionError as e:
        print(f"❌ Pattern consistency test failed: {e}")

    try:
        test.test_examples()
        print("✅ Example validation test passed")
    except AssertionError as e:
        print(f"❌ Example validation test failed: {e}")

if __name__ == "__main__":
    main()