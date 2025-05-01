"""
Basic tests for the AWS Bedrock Access Checker.
"""

import sys
import unittest
from importlib import import_module


class TestImports(unittest.TestCase):
    """Test that all modules can be imported."""

    def test_imports(self):
        """Test that all modules can be imported."""
        modules = [
            'bedrock_access_checker',
            'bedrock_access_checker.checker',
            'bedrock_access_checker.cli',
        ]
        for module_name in modules:
            try:
                import_module(module_name)
            except ImportError as e:
                self.fail(f"Failed to import {module_name}: {e}")


if __name__ == '__main__':
    unittest.main()