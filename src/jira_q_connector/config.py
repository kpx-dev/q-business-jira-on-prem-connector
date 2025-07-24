"""
Configuration classes for Jira Q Business Connector
"""
import os
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path
import json
import boto3
from dotenv import load_dotenv

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
    """Configuration for the Jira Q Business Connector"""
    
    # Component configurations
    jira: JiraConfig
    aws: AWSConfig
    qbusiness: QBusinessConfig
    
    # Sync options
    batch_size: int = 10
    include_comments: bool = True
    include_history: bool = False
    
    # Filtering options
    projects: Optional[List[str]] = None
    issue_types: Optional[List[str]] = None
    jql_filter: Optional[str] = None
    last_sync_date: Optional[str] = None
    cache_table_name: Optional[str] = None
    
    # Caching options
    # Access Control is always enabled
    
    @classmethod
    def from_env(cls, env_loaded: bool = False):
        """Create configuration from environment variables and .env file"""
        # Load .env file from current directory or project root

        if not env_loaded:
            env_paths = [
                Path(".env"),                    # Current directory
                Path("./.env"),                  # Explicit current directory
                Path("../.env"),                 # Parent directory
                Path("../../.env"),              # Two levels up
                Path.cwd() / ".env",             # Current working directory
            ]
            
            # Try to find and load .env file
            for env_path in env_paths:
                if env_path.exists():
                    load_dotenv(env_path, override=True)
                    print(f"📋 Loaded environment from: {env_path.absolute()}")
                    env_loaded = True
                    break
        
        if not env_loaded:
            print("⚠️  No .env file found. Using system environment variables only.")
            print("💡 Create a .env file from env.example for easier configuration.")
        
        # Set default for POWERTOOLS_IDEMPOTENCY_DISABLED if not already set
        if not os.environ.get("POWERTOOLS_IDEMPOTENCY_DISABLED"):
            os.environ["POWERTOOLS_IDEMPOTENCY_DISABLED"] = "1"
        
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
            batch_size=int(os.environ.get("BATCH_SIZE", "10")),
            include_comments=os.environ.get("INCLUDE_COMMENTS", "true").lower() == "true",
            include_history=os.environ.get("INCLUDE_HISTORY", "false").lower() == "true",
            
            # Filtering options
            projects=os.environ.get("PROJECTS", "").split(",") if os.environ.get("PROJECTS") else None,
            issue_types=os.environ.get("ISSUE_TYPES", "").split(",") if os.environ.get("ISSUE_TYPES") else None,
            jql_filter=os.environ.get("JQL_FILTER"),
            last_sync_date=os.environ.get("LAST_SYNC_DATE", "2010-01-01"),
            cache_table_name=os.environ.get("CACHE_TABLE_NAME", "jira-q-sync-cache")
        )
        
        # Validate required configuration
        cls._validate_config(config)
        
        return config
    
    @classmethod
    def from_ssm(cls, path_prefix="/jira-q-connector/"):
        """Create configuration from SSM Parameter Store"""

        ssm = boto3.client('ssm')
        params = {}
        next_token = None
        
        # Fetch all params from parameter store
        while True:
            # Prepare request parameters
            request_args = {
                'Path': path_prefix,
                'Recursive': True,
                'WithDecryption': True
            }
            
            # Add NextToken if we have one
            if next_token:
                request_args['NextToken'] = next_token
                
            # Make the API call
            response = ssm.get_parameters_by_path(**request_args)
            
            # Process parameters from this page
            for param in response['Parameters']:
                name = param['Name'].split('/')[-1]
                params[name] = param['Value']
            
            # Check if there are more parameters to fetch
            if 'NextToken' in response:
                next_token = response['NextToken']
            else:
                break

        print(f"🔑 {len(params)} parameters loaded from SSM")
        print(f"🔑 Parameters loaded: {', '.join(params.keys())}")

        # Set environment variables temporarily
        for key, value in params.items():
            os.environ[key] = value

        # Initialize Secrets Manager client
        client = boto3.client('secretsmanager')
        
        # Get secret value
        response = client.get_secret_value(SecretId='jira-q-connector')
        
        # Parse secret string to JSON
        secret_data = json.loads(response['SecretString'])
        
        # Set environment variables
        os.environ['JIRA_USERNAME'] = secret_data.get('JIRA_USERNAME')
        os.environ['JIRA_PASSWORD'] = secret_data.get('JIRA_PASSWORD')
        
        # Use existing from_env method
        return cls.from_env(env_loaded=True)
    
    @classmethod
    def _validate_config(cls, config):
        """Validate that required configuration is present"""
        errors = []
        
        # Validate Jira config
        if not config.jira.server_url:
            errors.append("JIRA_SERVER_URL is required")
        if not config.jira.username:
            errors.append("JIRA_USERNAME is required")
        if not config.jira.password:
            errors.append("JIRA_PASSWORD is required")
            
        # Validate Q Business config
        if not config.qbusiness.application_id:
            errors.append("Q_APPLICATION_ID is required")
        if not config.qbusiness.data_source_id:
            errors.append("Q_DATA_SOURCE_ID is required")
        if not config.qbusiness.index_id:
            errors.append("Q_INDEX_ID is required")

        if errors:
            print("❌ Configuration errors found:")
            for error in errors:
                print(f"   • {error}")
            print("\n💡 Please check your .env file or environment variables.")
            print("💡 Copy env.example to .env and fill in your values.")
            raise ValueError(f"Missing required configuration: {', '.join(errors)}")
    
    @classmethod  
    def reload_from_env(cls):
        """Reload configuration from .env file (useful for development)"""
        print("🔄 Reloading configuration from .env file...")
        return cls.from_env()


# Simplified loader function for backward compatibility
def load_config():
    """Load configuration from environment (simplified interface)"""
    try:
        return ConnectorConfig.from_env()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\n🔧 Quick Setup:")
        print("   1. Copy env.example to .env:")
        print("      cp env.example .env")
        print("   2. Edit .env with your Jira and Q Business settings")
        print("   3. Run the command again")
        raise