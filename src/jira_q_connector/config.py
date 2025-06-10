"""
Configuration module for Jira Custom Connector for Amazon Q Business
"""
import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class JiraConfig(BaseModel):
    """Jira server configuration"""
    server_url: str = Field(..., description="Jira server URL (e.g., https://your-jira.company.com)")
    username: str = Field(..., description="Jira username")
    password: str = Field(..., description="Jira password or API token")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    timeout: int = Field(default=30, description="Request timeout in seconds")


class AWSConfig(BaseModel):
    """AWS Q Business configuration"""
    region: str = Field(default="us-east-1", description="AWS region")
    application_id: str = Field(..., description="Q Business application ID")
    data_source_id: str = Field(..., description="Q Business data source ID")
    index_id: str = Field(..., description="Q Business index ID")
    role_arn: Optional[str] = Field(default=None, description="IAM role ARN for cross-account access")


class ConnectorConfig(BaseModel):
    """Main connector configuration"""
    jira: JiraConfig
    aws: AWSConfig
    
    # Sync settings
    sync_mode: str = Field(default="full", description="Sync mode: 'full' or 'incremental'")
    batch_size: int = Field(default=10, description="Batch size for document processing (max 10 for Q Business)")
    
    # Content settings
    include_comments: bool = Field(default=True, description="Include issue comments")
    include_history: bool = Field(default=False, description="Include issue change history")
    
    # Filtering
    jql_filter: Optional[str] = Field(default=None, description="JQL filter to limit issues")
    projects: Optional[list[str]] = Field(default=None, description="List of project keys to sync")
    issue_types: Optional[list[str]] = Field(default=None, description="List of issue types to sync")
    
    @classmethod
    def from_env(cls) -> "ConnectorConfig":
        """Create configuration from environment variables"""
        jira_config = JiraConfig(
            server_url=os.getenv("JIRA_SERVER_URL", ""),
            username=os.getenv("JIRA_USERNAME", ""),
            password=os.getenv("JIRA_PASSWORD", ""),
            verify_ssl=os.getenv("JIRA_VERIFY_SSL", "true").lower() == "true",
            timeout=int(os.getenv("JIRA_TIMEOUT", "30"))
        )
        
        aws_config = AWSConfig(
            region=os.getenv("AWS_REGION", "us-east-1"),
            application_id=os.getenv("Q_APPLICATION_ID", ""),
            data_source_id=os.getenv("Q_DATA_SOURCE_ID", ""),
            index_id=os.getenv("Q_INDEX_ID", ""),
            role_arn=os.getenv("AWS_ROLE_ARN")
        )
        
        return cls(
            jira=jira_config,
            aws=aws_config,
            sync_mode=os.getenv("SYNC_MODE", "full"),
            batch_size=int(os.getenv("BATCH_SIZE", "10")),
            include_comments=os.getenv("INCLUDE_COMMENTS", "true").lower() == "true",
            include_history=os.getenv("INCLUDE_HISTORY", "false").lower() == "true",
            jql_filter=os.getenv("JQL_FILTER"),
            projects=os.getenv("PROJECTS", "").split(",") if os.getenv("PROJECTS") else None,
            issue_types=os.getenv("ISSUE_TYPES", "").split(",") if os.getenv("ISSUE_TYPES") else None
        ) 