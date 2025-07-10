# Jira On-Premises Custom Connector for Amazon Q Business

A Python-based custom connector that synchronizes Jira on-premises server with Amazon Q Business using the BatchPutDocument API.

## How It Works:

**🔄 Sync Process (jira-q-connector sync):**
1. **Start Job** - Initialize Q Business data source sync with execution ID
2. **Setup ACL** - Sync Jira users, groups, and permissions to Q Business User Store using comprehensive 4-step permission extraction
3. **Extract Data** - Pull Jira issues via REST API v2 using JQL queries with 60+ fields
4. **Transform & Upload** - Convert issues to Q Business BatchPutDocument format with rich content and comprehensive attributes
5. **Complete** - Stop sync job and finalize the data source update

**📄 Document Content:** Each Jira issue becomes a highly detailed searchable Q Business document with:
- Issue summary, description, and key with full metadata
- Comments (optional) and change history (optional)  
- Comprehensive metadata: status, priority, assignee, reporter, labels, components, versions, time tracking
- All custom fields including Agile fields (Epic Link, Story Points, Sprint)
- Attachment information, issue links, subtasks, and parent relationships
- Progress tracking, votes, watchers, and environment details
- Direct links back to original Jira issues

## 📋 Prerequisites

- Python 3.8 or higher
- Jira Server 9+ (on-premises) or compatible version
- Amazon Q Business application with custom data source
- AWS credentials with Q Business permissions

## 🏗️ Setting Up Jira On-Premises on AWS EC2 (Optional)

If you need to set up your own Jira instance for testing, follow these comprehensive instructions:

### Step 1: Launch EC2 Instance

**Instance Requirements:**
- **Instance Type**: t3.medium or larger (minimum 4GB RAM)
- **Operating System**: Amazon Linux 2 or Ubuntu 20.04+ 
- **Storage**: 20GB+ EBS volume
- **Security Group**: Configure ports as described below

### Step 2: Configure Security Group

**Required Ports:**
- **SSH (22)**: For server access
- **HTTP (8080)**: Default Jira port
- **HTTPS (8443)**: For SSL access (optional)

### Step 3: Connect to Instance and Prepare System

```bash
# Connect to your EC2 instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Update system packages
sudo yum update -y  # For Amazon Linux
# OR
sudo apt update && sudo apt upgrade -y  # For Ubuntu
```

### Step 4: Download and Install Jira

**Download Jira 9+:**

Based on [Atlassian's download archives](https://www.atlassian.com/software/jira/download-archives), download the Linux installer:

```bash
# Ex: Download Jira 9+ Linux installer
wget https://www.atlassian.com/software/jira/downloads/binary/atlassian-jira-software-9.17.5-x64.bin

# Make installer executable
chmod +x atlassian-jira-software-9.17.5-x64.bin

# Run the installer
sudo ./atlassian-jira-software-9.17.5-x64.bin
```

**Access Jira Web Interface:**

1. Open browser and navigate to: `http://your-ec2-public-ip:8080`

**Configure API Access:**
1. Go to Administration → System → General Configuration
2. Enable "Accept remote API calls"
3. Note the Base URL for your connector configuration

### Step 4: Update Connector Configuration

Update your `.env` file with the new Jira instance details:

```bash
# Jira Configuration
JIRA_SERVER_URL=http://your-ec2-public-ip:8080
JIRA_USERNAME=jira-connector
JIRA_PASSWORD=your-service-account-password
```

### Step 5: Test Connector

```bash
# Test connections
jira-q-connector doctor

# Perform sync
jira-q-connector sync
```

## 🛠️ Installation

### Option 1: Install from Source (Recommended for Development)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd q-business-jira-on-prem-connector
   ```

2. **Install in development mode:**
   ```bash
   pip install -e .
   ```

3. **Set up configuration:**
   ```bash
   # Copy example environment file
   cp env.example .env
   
   # Edit with your settings
   nano .env
   ```

## ⚙️ Configuration

### Environment Variables

```bash
# Jira Configuration
JIRA_SERVER_URL=https://your-jira-server.company.com
JIRA_USERNAME=your-username
JIRA_PASSWORD=your-password-or-api-token

# Amazon Q Business Configuration
AWS_REGION=us-east-1
Q_APPLICATION_ID=your-q-application-id
Q_DATA_SOURCE_ID=your-q-data-source-id
Q_INDEX_ID=your-q-index-id

# Sync Configuration
BATCH_SIZE=10  
INCLUDE_COMMENTS=true
INCLUDE_HISTORY=false

# Filtering (Optional)
PROJECTS=PROJECT1,PROJECT2
ISSUE_TYPES=Bug,Task,Story
JQL_FILTER=status != "Closed" AND updated >= -7d

# Access Control is enabled by default
```

### Configuration Details

**Required Environment Variables:**
- `JIRA_SERVER_URL`: Your Jira server URL
- `JIRA_USERNAME`: Jira username or email
- `JIRA_PASSWORD`: Jira password or API token
- `Q_APPLICATION_ID`: Q Business application ID
- `Q_DATA_SOURCE_ID`: Q Business data source ID (must be CUSTOM type)
- `Q_INDEX_ID`: Q Business index ID

**Optional Configuration:**
- `AWS_REGION`: AWS region (default: us-east-1)
- `JIRA_VERIFY_SSL`: Verify SSL certificates (default: true)
- `JIRA_TIMEOUT`: Request timeout in seconds (default: 30)
- `BATCH_SIZE`: Documents per batch, max 10 (default: 10)
- `INCLUDE_COMMENTS`: Include issue comments (default: true)
- `INCLUDE_HISTORY`: Include change history (default: false)
- `PROJECTS`: Comma-separated project keys to sync
- `ISSUE_TYPES`: Comma-separated issue types to sync
- `JQL_FILTER`: Custom JQL filter for issue selection


## 🎯 Usage

The connector provides a command-line interface (CLI) as the primary way to interact with the system. The CLI is installed as `jira-q-connector` and can also be run as a Python module.

### Command Line Interface

```bash
# Test connections and configuration
jira-q-connector doctor

# Perform sync
jira-q-connector sync

# Clean sync (delete duplicates first)
jira-q-connector sync --clean

# Check sync job status
jira-q-connector status

# Stop running sync jobs
jira-q-connector stop

# Alternative: Run as a module
python -m jira_q_connector doctor
python -m jira_q_connector sync
python -m jira_q_connector status
```

### Python API (Advanced Usage)

For advanced use cases or custom integrations, you can use the Python API directly:

```python
from jira_q_connector import ConnectorConfig, JiraQBusinessConnector

# Load configuration from environment
config = ConnectorConfig.from_env()

# Create connector instance
connector = JiraQBusinessConnector(config)

# Test connections
results = connector.test_connections()
print(f"Connections: {results['overall_success']}")

# Perform sync with custom execution ID
sync_job = connector.start_qbusiness_sync()
execution_id = sync_job['execution_id']

# Sync issues with execution ID
sync_result = connector.sync_issues_with_execution_id(execution_id)
print(f"Sync completed: {sync_result['success']}")

# Stop sync job
connector.stop_qbusiness_sync(execution_id)

# Cleanup resources
connector.cleanup()
```

## 🧪 Testing

Run the test suite:

```bash
# Install in development mode with test dependencies
pip install -e ".[dev]"

# Run tests (when test suite is available)
python -m pytest tests/

# Test real connections manually
jira-q-connector doctor
```

### AWS Lambda
Deploy as a Lambda function for serverless execution:

```python
import json
import subprocess
import os

def lambda_handler(event, context):
    """
    Lambda function to run Jira Q Business connector sync
    """
    try:
        # Set environment variables if needed
        # os.environ['JIRA_SERVER_URL'] = 'https://...'
        
        # Run the CLI command
        result = subprocess.run(
            ['jira-q-connector', 'sync'],
            capture_output=True,
            text=True,
            timeout=900  # 15 minutes max
        )
        
        # Check if command was successful
        if result.returncode == 0:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': 'Sync completed successfully',
                    'output': result.stdout
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'error': result.stderr,
                    'output': result.stdout
                })
            }
            
    except subprocess.TimeoutExpired:
        return {
            'statusCode': 408,
            'body': json.dumps({
                'success': False,
                'error': 'Sync operation timed out'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
```

**Alternative: Using Python API for advanced control:**

```python
import json
from jira_q_connector import ConnectorConfig, JiraQBusinessConnector

def lambda_handler(event, context):
    try:
        config = ConnectorConfig.from_env()
        connector = JiraQBusinessConnector(config)
        
        # Start sync job and sync issues
        sync_job = connector.start_qbusiness_sync()
        execution_id = sync_job['execution_id']
        
        # Sync issues with execution ID
        result = connector.sync_issues_with_execution_id(execution_id)
        
        # Stop sync job
        connector.stop_qbusiness_sync(execution_id)
        connector.cleanup()
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
```

## 📚 API Reference

### JiraClient
- `test_connection()`: Test Jira connectivity
- `search_issues(jql, start_at, max_results)`: Search issues

### QBusinessClient  
- `test_connection()`: Test Q Business connectivity
- `batch_put_documents_with_execution_id(documents, execution_id)`: Upload documents
- `batch_delete_documents(ids)`: Delete documents
- `start_data_source_sync()`: Start sync job

### JiraDocumentProcessor
- `process_issue(issue, execution_id)`: Convert issue to Q Business document
- `create_batch_documents(issues, execution_id)`: Process multiple issues

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## 🔗 References

- [Jira Server REST API Documentation](https://developer.atlassian.com/server/jira/platform/rest/v10006/intro/)
- [Amazon Q Business Custom Connectors](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/custom-connector.html)
- [Amazon Q Business BatchPutDocument API](https://docs.aws.amazon.com/amazonq/latest/api-reference/API_BatchPutDocument.html)
- [Amazon Q Business Required Attributes](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/custom-required-attributes.html)
- [Jira Permission Schemes](https://confluence.atlassian.com/adminjiraserver/managing-project-permissions-938847142.html)
- [Amazon Q Business User Store](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/user-group-store.html)

---