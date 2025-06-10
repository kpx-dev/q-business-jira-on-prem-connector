#!/usr/bin/env python3
"""
Allow running jira_q_connector as a module with `python -m jira_q_connector`
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main()) 