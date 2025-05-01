#!/usr/bin/env python3
"""
AWS Bedrock Access Verification Tool - Compatibility script

This is a compatibility script that imports and runs the main CLI
from the package. This allows users to run the tool directly without
installing it.
"""

from bedrock_access_checker.cli import main

if __name__ == "__main__":
    main()