"""
Jira On-Premises Custom Connector for Amazon Q Business

A comprehensive Python-based custom connector that synchronizes 
Jira on-premises server with Amazon Q Business.
"""

__version__ = "1.0.0"
__author__ = "Jira Q Business Connector Team"

from .config import ConnectorConfig
from .jira_connector import JiraQBusinessConnector

__all__ = [
    "ConnectorConfig",
    "JiraQBusinessConnector",
] 