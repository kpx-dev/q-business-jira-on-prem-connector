# Jira On-Premises Custom Connector for Amazon Q Business

A comprehensive Python-based custom connector that synchronizes Jira on-premises server (version 9.12.17) with Amazon Q Business using the BatchPutDocument API.

**How It Works:**

**🔄 Sync Process (jira-q-connector sync):**
1. **Start Job** - Initialize Q Business data source sync with execution ID
2. **Extract Data** - Pull Jira issues via REST API v2 using JQL queries
3. **Transform** - Convert issues to Q Business BatchPutDocument format
4. **Upload** - Send documents in batches of 10 (AWS API limit)
5. **Complete** - Stop sync job and finalize the data source update

**📄 Document Content:** Each Jira issue becomes a searchable Q Business document with:
- Issue summary, description, and key
- Comments (optional) and change history (optional)  
- Metadata: status, priority, assignee, reporter, labels
- Direct links back to original Jira issues

**☁️ Q Business Flow:** Documents are indexed in your Q Business Application → Index → Custom Data Source → Available for search by end users

## 🚀 Features

- **✅ Jira Server 9.12.17 Compatibility**: Uses Jira REST API v2 for maximum compatibility
- **🔄 Full & Incremental Sync**: Support for both full and incremental synchronization modes
- **📝 Rich Content Extraction**: Extracts issues, comments, change history, and metadata
- **🔒 Access Control Support**: Synchronizes Jira permissions to Q Business User Store
- **🏷️ Advanced Filtering**: Filter by projects, issue types, or custom JQL queries
- **📊 Batch Processing**: Efficient batch upload to Amazon Q Business
- **🔧 Simple Configuration**: Environment variables via .env file
- **📈 Comprehensive Logging**: Detailed logging with configurable levels
- **✨ CLI Interface**: Easy-to-use command-line interface

## 📋 Prerequisites

- Python 3.8 or higher
- Jira Server 9.12.17 (on-premises)
- Amazon Q Business application with custom data source
- AWS credentials with Q Business permissions

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
JIRA_VERIFY_SSL=true
JIRA_TIMEOUT=30

# Amazon Q Business Configuration
AWS_REGION=us-east-1
Q_APPLICATION_ID=your-q-application-id
Q_DATA_SOURCE_ID=your-q-data-source-id
Q_INDEX_ID=your-q-index-id

# Sync Configuration
SYNC_MODE=full  # Options: full, incremental
BATCH_SIZE=10   # Max 10 for Q Business BatchPutDocument
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
- `SYNC_MODE`: full or incremental (default: full)
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

# Preview sync (dry run - shows what would be synced)
jira-q-connector sync --dry-run

# Perform full sync
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
sync_result = connector.sync_issues_with_execution_id(execution_id, dry_run=False)
print(f"Sync completed: {sync_result['success']}")

# Stop sync job
connector.stop_qbusiness_sync(execution_id)

# Cleanup resources
connector.cleanup()
```

## 🔒 Access Control (ACL) Support

The connector supports synchronizing Jira permissions to Amazon Q Business User Store, enabling proper access control for your Jira documents.

### How It Works

1. **Permission Extraction**: The connector extracts permissions from Jira's complex permission model
2. **User Store Mapping**: Maps Jira users, groups, and project roles to Q Business User Store
3. **Document ACL**: Applies appropriate ACL to each document based on Jira permissions
4. **Hierarchical Structure**: Preserves Jira's permission hierarchy in Q Business

### Setup

1. **Q Business Permissions**: Ensure your IAM policy includes:
   ```json
   {
       "Effect": "Allow",
       "Action": [
           "qbusiness:BatchPutUserGroupStore",
           "qbusiness:BatchDeleteUserGroupStore"
       ],
       "Resource": "arn:aws:qbusiness:*:*:application/*/index/*/user-group-store"
   }
   ```

### Permission Mapping

The connector maps Jira permissions to Q Business as follows:

- **Users**: Direct mapping of Jira users to Q Business users
- **Groups**: Jira groups become Q Business groups
- **Project Roles**: Each project role becomes a Q Business group
- **Project Access**: Users with browse permission for a project get access to its documents
- **Security Levels**: Issue security levels are mapped to Q Business groups

## 🔧 Amazon Q Business Setup

### 1. Create Custom Data Source

Using AWS CLI:
```bash
aws qbusiness create-data-source \
    --application-id <your-app-id> \
    --index-id <your-index-id> \
    --display-name "Jira On-Premises" \
    --type "CUSTOM" \
    --configuration '{"type": "CUSTOM", "version": "1.0.0"}'
```

Using AWS Console:
1. Navigate to Amazon Q Business
2. Select your application
3. Go to Data Sources
4. Create new Custom data source
5. Note the generated data source ID

### 2. Required IAM Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "qbusiness:BatchPutDocument",
                "qbusiness:BatchDeleteDocument",
                "qbusiness:StartDataSourceSyncJob",
                "qbusiness:StopDataSourceSyncJob",
                "qbusiness:GetDataSourceSyncJob",
                "qbusiness:ListDataSourceSyncJobs",
                "qbusiness:BatchPutUserGroupStore",
                "qbusiness:BatchDeleteUserGroupStore",
                "qbusiness:GetApplication"
            ],
            "Resource": [
                "arn:aws:qbusiness:*:*:application/*",
                "arn:aws:qbusiness:*:*:application/*/index/*",
                "arn:aws:qbusiness:*:*:application/*/index/*/data-source/*"
            ]
        }
    ]
}
```

## 📊 Document Structure

Each Jira issue is converted to a Q Business document with:

### Content
- Issue key and summary
- Description (cleaned HTML/ADF)
- Status, priority, type metadata
- Project information
- Assignee and reporter details
- Comments (if enabled)
- Change history (if enabled)

### Attributes
- `_source_uri`: Direct link to Jira issue
- `jira_issue_key`: Issue key (e.g., "PROJ-123")
- `jira_project`: Project key
- `jira_status`: Current status
- `jira_priority`: Priority level
- `jira_assignee`: Assigned user
- `jira_created`: Creation date
- `jira_updated`: Last update date
- `jira_labels`: Issue labels (array)

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

## 🐛 Troubleshooting

### Common Issues

**Authentication Failed:**
```bash
# Verify Jira credentials
curl -u username:password https://your-jira.com/rest/api/2/myself
```

**Q Business Access Denied:**
```bash
# Check AWS credentials and permissions
aws sts get-caller-identity
aws qbusiness get-application --application-id <your-app-id>
```

**SSL Certificate Issues:**
```bash
# For self-signed certificates
export JIRA_VERIFY_SSL=false
```

### Debug Mode

Enable debug logging:
```bash
# Enable debug logging for sync
jira-q-connector sync --log-level DEBUG

# Or set environment variable
export LOG_LEVEL=DEBUG
jira-q-connector sync

# Test connections with debug output
jira-q-connector doctor --log-level DEBUG
```

## 📈 Performance Tuning

### Batch Size Optimization
- **All installations**: `BATCH_SIZE=10` (AWS Q Business limit)
- Note: AWS Q Business BatchPutDocument API has a maximum of 10 documents per batch

### Memory Usage
- Disable comments for memory-intensive syncs: `INCLUDE_COMMENTS=false`
- Use incremental sync for large datasets: `SYNC_MODE=incremental`

### Network Optimization
- Increase timeout for slow networks: `JIRA_TIMEOUT=60`
- Reduce batch size for unstable connections

## 🔄 Scheduling

### Cron Example
```bash
# Daily incremental sync at 2 AM
0 2 * * * /usr/local/bin/jira-q-connector sync > /var/log/jira-sync.log 2>&1

# Weekly full sync on Sundays at 1 AM
0 1 * * 0 SYNC_MODE=full /usr/local/bin/jira-q-connector sync --clean > /var/log/jira-full-sync.log 2>&1

# Alternative: Using specific path to Python module
# 0 2 * * * cd /path/to/project && python -m jira_q_connector sync
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
        result = connector.sync_issues_with_execution_id(execution_id, dry_run=False)
        
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

---

**📧 Support**: For issues and questions, please open a GitHub issue.
