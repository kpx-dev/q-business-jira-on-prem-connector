"""
Configuration classes for Jira Q Business Connector
"""
import os
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class JiraConfig:
    """Jira configuration"""
    server_url: str
    username: str
    password: str
    verify_ssl: bool = True
    timeout: int = 30

@dataclass
class AWSConfig:
    """AWS configuration"""
    region: str = "us-east-1"

@dataclass
class QBusinessConfig:
    """Amazon Q Business configuration"""
    application_id: str
    data_source_id: str
    index_id: str

@dataclass
class ConnectorConfig:
    """Connector configuration"""
    jira: JiraConfig
    aws: AWSConfig
    qbusiness: QBusinessConfig
    
    # Sync options
    sync_mode: str = "full"
    batch_size: int = 10
    include_comments: bool = True
    include_history: bool = False
    
    # Filtering options
    projects: Optional[List[str]] = None
    issue_types: Optional[List[str]] = None
    jql_filter: Optional[str] = None
    
    # Caching options
    # Access Control is always enabled
    
    @classmethod
    def from_env(cls):
        """Create configuration from environment variables"""
        # Jira configuration
        jira_config = JiraConfig(
            server_url=os.environ.get("JIRA_SERVER_URL", ""),
            username=os.environ.get("JIRA_USERNAME", ""),
            password=os.environ.get("JIRA_PASSWORD", ""),
            verify_ssl=os.environ.get("JIRA_VERIFY_SSL", "true").lower() == "true",
            timeout=int(os.environ.get("JIRA_TIMEOUT", "30"))
        )
        
        # AWS configuration
        aws_config = AWSConfig(
            region=os.environ.get("AWS_REGION", "us-east-1")
        )
        
        # Q Business configuration
        qbusiness_config = QBusinessConfig(
            application_id=os.environ.get("Q_APPLICATION_ID", ""),
            data_source_id=os.environ.get("Q_DATA_SOURCE_ID", ""),
            index_id=os.environ.get("Q_INDEX_ID", "")
        )
        
        # Create connector configuration
        config = cls(
            jira=jira_config,
            aws=aws_config,
            qbusiness=qbusiness_config,
            
            # Sync options
            sync_mode=os.environ.get("SYNC_MODE", "full"),
            batch_size=int(os.environ.get("BATCH_SIZE", "10")),
            include_comments=os.environ.get("INCLUDE_COMMENTS", "true").lower() == "true",
            include_history=os.environ.get("INCLUDE_HISTORY", "false").lower() == "true",
            
            # Filtering options
            projects=os.environ.get("PROJECTS", "").split(",") if os.environ.get("PROJECTS") else None,
            issue_types=os.environ.get("ISSUE_TYPES", "").split(",") if os.environ.get("ISSUE_TYPES") else None,
            jql_filter=os.environ.get("JQL_FILTER")
        )
        
        return config