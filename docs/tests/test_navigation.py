"""
Navigation test suite for documentation validation.
Tests cross-references and navigation paths between documents.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional

class DocumentValidator:
    def __init__(self, docs_root: str = "docs"):
        self.docs_root = Path(docs_root)
        self.cache = {}

    def get_file_content(self, filepath: str) -> Optional[str]:
        """Read and cache file content"""
        abs_path = self.docs_root / filepath
        if not abs_path.exists():
            return None

        if filepath not in self.cache:
            self.cache[filepath] = abs_path.read_text(encoding='utf-8')
        return self.cache[filepath]

    def file_exists(self, filepath: str) -> bool:
        """Check if file exists"""
        return (self.docs_root / filepath).exists()

    def section_exists(self, filepath: str, section: str) -> bool:
        """Check if section exists in file"""
        content = self.get_file_content(filepath)
        if not content:
            return False

        # Look for markdown headings
        section_pattern = f"^#+\\s*{re.escape(section)}\\s*$"
        return bool(re.search(section_pattern, content, re.MULTILINE))

    def link_valid(self, from_file: str, to_file: str) -> bool:
        """Check if link between files is valid"""
        content = self.get_file_content(from_file)
        if not content:
            return False

        # Look for markdown links
        link_pattern = f"\\[.*?\\]\\(.*?{re.escape(to_file)}.*?\\)"
        return bool(re.search(link_pattern, content))

    def get_all_links(self, filepath: str) -> List[str]:
        """Get all links from a file"""
        content = self.get_file_content(filepath)
        if not content:
            return []

        # Extract markdown links
        link_pattern = r"\[.*?\]\((.*?)\)"
        return [m.group(1) for m in re.finditer(link_pattern, content)]

    def path_complete(self, path: List[str]) -> bool:
        """Check if navigation path is complete"""
        for i in range(len(path) - 1):
            if not self.link_valid(path[i], path[i + 1]):
                return False
        return True

    def bidirectional_links_exist(self, path: List[str]) -> bool:
        """Check if bidirectional links exist between documents"""
        for i in range(len(path) - 1):
            if not (self.link_valid(path[i], path[i + 1]) and
                   self.link_valid(path[i + 1], path[i])):
                return False
        return True

class TestNavigation:
    def setup_method(self):
        self.validator = DocumentValidator()

    def test_cross_references(self):
        """Test cross-references between documents"""
        references = [
            {
                "from": "cursor_rules.md",
                "to": "sops/tool_creation.md",
                "section": "Tool Usage"
            },
            {
                "from": "cursor_rules.md",
                "to": "sops/tool_selection.md",
                "section": "Quick Reference"
            },
            {
                "from": "cursor_rules.md",
                "to": "sops/agent_creation.md",
                "section": "Agent Coordination"
            },
            {
                "from": "cursor_rules.md",
                "to": "sops/context_management.md",
                "section": "Information Management"
            },
        ]

        for ref in references:
            assert self.validator.file_exists(ref["to"]), \
                f"File {ref['to']} does not exist"

            assert self.validator.section_exists(ref["from"], ref["section"]), \
                f"Section {ref['section']} not found in {ref['from']}"

            assert self.validator.link_valid(ref["from"], ref["to"]), \
                f"Link from {ref['from']} to {ref['to']} is invalid"

    def test_navigation_paths(self):
        """Test navigation paths between documents"""
        paths = [
            ["cursor_rules.md", "tool_selection.md", "tool_creation.md"],
            ["cursor_rules.md", "agent_creation.md", "context_management.md"],
            ["tool_selection.md", "context_management.md", "cursor_rules.md"],
        ]

        for path in paths:
            assert self.validator.path_complete(path), \
                f"Navigation path {' -> '.join(path)} is incomplete"

            assert self.validator.bidirectional_links_exist(path), \
                f"Bidirectional links missing in path {' -> '.join(path)}"

    def test_orphaned_documents(self):
        """Test for orphaned documents"""
        docs = [f for f in os.listdir(self.validator.docs_root) if f.endswith('.md')]
        for doc in docs:
            incoming_links = []
            for other_doc in docs:
                if other_doc != doc and self.validator.link_valid(other_doc, doc):
                    incoming_links.append(other_doc)

            assert incoming_links, f"Document {doc} is orphaned (no incoming links)"

    def test_broken_links(self):
        """Test for broken links"""
        docs = [f for f in os.listdir(self.validator.docs_root) if f.endswith('.md')]
        for doc in docs:
            links = self.validator.get_all_links(doc)
            for link in links:
                if link.endswith('.md'):  # Only check internal doc links
                    assert self.validator.file_exists(link), \
                        f"Broken link in {doc}: {link}"

def main():
    """Run navigation tests"""
    validator = DocumentValidator()
    test = TestNavigation()
    test.setup_method()

    print("Running navigation tests...")

    try:
        test.test_cross_references()
        print("✅ Cross-references test passed")
    except AssertionError as e:
        print(f"❌ Cross-references test failed: {e}")

    try:
        test.test_navigation_paths()
        print("✅ Navigation paths test passed")
    except AssertionError as e:
        print(f"❌ Navigation paths test failed: {e}")

    try:
        test.test_orphaned_documents()
        print("✅ Orphaned documents test passed")
    except AssertionError as e:
        print(f"❌ Orphaned documents test failed: {e}")

    try:
        test.test_broken_links()
        print("✅ Broken links test passed")
    except AssertionError as e:
        print(f"❌ Broken links test failed: {e}")

if __name__ == "__main__":
    main()