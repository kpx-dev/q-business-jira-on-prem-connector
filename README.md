# Jira On-Premises Custom Connector for Amazon Q Business

A comprehensive Python-based custom connector that synchronizes Jira on-premises server (version 9.12.17) with Amazon Q Business using the BatchPutDocument API.

## 🚀 Features

- **✅ Jira Server 9.12.17 Compatibility**: Uses Jira REST API v2 for maximum compatibility
- **🔄 Full & Incremental Sync**: Support for both full and incremental synchronization modes
- **📝 Rich Content Extraction**: Extracts issues, comments, change history, and metadata
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

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd q-business-jira-on-prem-connector
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
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

### Command Line Interface

```bash
# Test connections
python main.py doctor

# Preview sync (dry run)
python main.py sync --dry-run

# Perform full sync
python main.py sync

# Clean sync (delete duplicates first)
python main.py sync --clean

# Check sync job status
python main.py status
```

### Python API

```python
from config import ConnectorConfig
from jira_connector import JiraQBusinessConnector

# Load configuration
config = ConnectorConfig.from_env()

# Create connector
connector = JiraQBusinessConnector(config)

# Test connections
results = connector.test_connections()
print(f"Connections: {results['overall_success']}")

# Start sync job and sync issues
sync_job = connector.start_qbusiness_sync()
execution_id = sync_job['execution_id']

# Sync issues with execution ID
sync_result = connector.sync_issues_with_execution_id(execution_id, dry_run=False)
print(f"Sync completed: {sync_result['success']}")

# Stop sync job
connector.stop_qbusiness_sync(execution_id)

# Cleanup
connector.cleanup()
```

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
# Run unit tests
python test_connector.py

# Test with real connections (requires environment variables)
JIRA_SERVER_URL=https://your-jira.com \
JIRA_USERNAME=user \
JIRA_PASSWORD=pass \
Q_APPLICATION_ID=app-id \
Q_DATA_SOURCE_ID=ds-id \
Q_INDEX_ID=index-id \
python test_connector.py
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
python main.py sync --log-level DEBUG
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
0 2 * * * /path/to/python /path/to/main.py sync > /var/log/jira-sync.log 2>&1

# Weekly full sync on Sundays at 1 AM
0 1 * * 0 SYNC_MODE=full /path/to/python /path/to/main.py sync
```

### AWS Lambda
Deploy as a Lambda function for serverless execution:

```python
import json
from jira_connector import JiraQBusinessConnector
from config import ConnectorConfig

def lambda_handler(event, context):
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
