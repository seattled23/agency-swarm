"""
Root-level test runner for documentation validation.
"""

import sys
import os
from pathlib import Path

# Add docs directory to Python path
sys.path.append(str(Path(__file__).parent))

from docs.tests.run_tests import main

if __name__ == "__main__":
    # Ensure we're in the right directory
    os.chdir(Path(__file__).parent)
    sys.exit(main())