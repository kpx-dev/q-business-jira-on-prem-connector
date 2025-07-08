# Jira On-Premises Custom Connector for Amazon Q Business

A comprehensive Python-based custom connector that synchronizes Jira on-premises server (version 9.12.17) with Amazon Q Business using the BatchPutDocument API.

**How It Works:**

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

**🔒 Advanced ACL Integration:** Follows Jira's exact permission model:
- **4-Step Permission Extraction** - Comprehensive permission scheme analysis
- **Individual User Mapping** - Groups are expanded to include individual users in document ACL
- **Project-Level Security** - Respects Jira project permissions and roles
- **memberRelation: "OR"** - Proper Q Business ACL format with combined principals array

**☁️ Q Business Flow:** Documents are indexed in your Q Business Application → Index → Custom Data Source → Available for search by end users with proper access control

## 🚀 Features

- **✅ Jira Server 9.12.17 Compatibility**: Uses Jira REST API v2 for maximum compatibility
- **📝 Comprehensive Content Extraction**: Extracts 60+ fields including all custom fields, time tracking, progress, links, and metadata
- **🔒 Advanced ACL Integration**: 4-step permission extraction with individual user mapping and proper Q Business ACL format
- **🏷️ Rich Attribute Support**: 60+ filterable attributes for advanced search and faceting
- **🎯 Custom Field Support**: Automatic extraction of Agile fields (Epic Link, Story Points, Sprint) and all custom fields
- **📊 Enhanced Filtering**: Filter by projects, issue types, custom JQL queries, or any field value
- **📦 Efficient Processing**: Batch upload to Amazon Q Business with raw content format
- **🔧 Simple Configuration**: Environment variables via .env file
- **📈 Comprehensive Logging**: Detailed logging with configurable levels and debug mode
- **✨ CLI Interface**: Easy-to-use command-line interface with debug support

## 📋 Prerequisites

- Python 3.8 or higher
- Jira Server 9.12.17 (on-premises) or compatible version
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

**Launch Instance:**
```bash
# Using AWS CLI (replace with your key pair and subnet)
aws ec2 run-instances \
    --image-id ami-0c55b159cbfafe1d0 \
    --count 1 \
    --instance-type t3.medium \
    --key-name your-key-pair \
    --subnet-id subnet-xxxxxxxxx \
    --security-group-ids sg-xxxxxxxxx \
    --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]'
```

### Step 2: Configure Security Group

**Required Ports:**
- **SSH (22)**: For server access
- **HTTP (8080)**: Default Jira port
- **HTTPS (8443)**: For SSL access (optional)

**AWS Console Configuration:**
1. Go to EC2 → Security Groups
2. Select your security group
3. Add inbound rules:

```bash
# SSH access (replace with your IP)
Type: SSH, Port: 22, Source: Your.IP.Address/32

# Jira HTTP access
Type: Custom TCP, Port: 8080, Source: 0.0.0.0/0

# Jira HTTPS access (optional)
Type: HTTPS, Port: 8443, Source: 0.0.0.0/0
```

**Using AWS CLI:**
```bash
# Get your public IP
MY_IP=$(curl -s ifconfig.me)

# Add SSH rule
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol tcp \
    --port 22 \
    --cidr ${MY_IP}/32

# Add Jira HTTP rule
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol tcp \
    --port 8080 \
    --cidr 0.0.0.0/0
```

### Step 3: Connect to Instance and Prepare System

```bash
# Connect to your EC2 instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Update system packages
sudo yum update -y  # For Amazon Linux
# OR
sudo apt update && sudo apt upgrade -y  # For Ubuntu

# Install Java 11 (required for Jira)
sudo yum install -y java-11-amazon-corretto  # Amazon Linux
# OR
sudo apt install -y openjdk-11-jdk  # Ubuntu

# Verify Java installation
java -version
```

### Step 4: Download and Install Jira

**Download Jira 9.12.7:**

Based on [Atlassian's download archives](https://www.atlassian.com/software/jira/download-archives), download the Linux installer:

```bash
# Create installation directory
sudo mkdir -p /opt/atlassian
cd /opt/atlassian

# Download Jira 9.12.7 Linux installer
sudo wget https://product-downloads.atlassian.com/software/jira/downloads/atlassian-jira-software-9.12.7-x64.bin

# Make installer executable
sudo chmod +x atlassian-jira-software-9.12.7-x64.bin

# Run the installer
sudo ./atlassian-jira-software-9.12.7-x64.bin
```

**Installation Process:**

Following the [official installation guide](https://confluence.atlassian.com/adminjiraserver/installing-jira-applications-on-linux-938846841.html):

```bash
# The installer will prompt for:
# 1. Installation type: Choose "Install a new instance"
# 2. Installation directory: Accept default (/opt/atlassian/jira)
# 3. Home directory: Accept default (/var/atlassian/application-data/jira)
# 4. TCP ports: Accept defaults (8080 for HTTP, 8005 for control)
# 5. Install as service: Yes (recommended)

# Installation example prompts:
# Where should Jira Software be installed?
# [/opt/atlassian/jira]: <Press Enter>
#
# Default location for Jira Software data
# [/var/atlassian/application-data/jira]: <Press Enter>
#
# Configure which ports Jira Software will use.
# Jira requires two TCP ports that are not being used by any other applications.
# The HTTP port is where users will access Jira through their browsers.
# [8080]: <Press Enter>
#
# Control port:
# [8005]: <Press Enter>
#
# Jira can be run in the background.
# You may choose to run Jira in the foreground or install it as a service.
# Install Jira as Service? [y/N]: y
```

### Step 5: Configure Database (PostgreSQL)

**Install PostgreSQL:**
```bash
# Amazon Linux
sudo amazon-linux-extras install postgresql13 -y
sudo yum install postgresql-server postgresql-contrib -y

# Ubuntu
sudo apt install postgresql postgresql-contrib -y

# Initialize and start PostgreSQL
sudo postgresql-setup initdb  # Amazon Linux only
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Create Jira Database:**
```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user for Jira
CREATE DATABASE jiradb WITH ENCODING 'UNICODE' LC_COLLATE 'C' LC_CTYPE 'C' TEMPLATE template0;
CREATE USER jirauser WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE jiradb TO jirauser;
\q
```

**Configure PostgreSQL Authentication:**
```bash
# Edit pg_hba.conf to allow connections
sudo nano /var/lib/pgsql/data/pg_hba.conf

# Add this line before other rules:
local   jiradb          jirauser                                md5
host    jiradb          jirauser        127.0.0.1/32            md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Step 6: Start Jira and Complete Setup

**Start Jira Service:**
```bash
# Start Jira service
sudo systemctl start jira
sudo systemctl enable jira

# Check Jira status
sudo systemctl status jira

# View Jira logs
sudo tail -f /opt/atlassian/jira/logs/catalina.out
```

**Access Jira Web Interface:**

1. Open browser and navigate to: `http://your-ec2-public-ip:8080`
2. Complete the Jira setup wizard:
   - Choose "I'll set it up myself"
   - Database configuration:
     - Database Type: PostgreSQL
     - Hostname: localhost
     - Port: 5432
     - Database: jiradb
     - Username: jirauser
     - Password: your_secure_password
   - Generate Jira license or use evaluation license
   - Create administrator account
   - Set up sample project (optional)

### Step 7: Configure Jira for Connector

**Create Service Account:**
1. Log into Jira as administrator
2. Go to Administration → User Management
3. Create new user for the connector:
   - Username: `jira-connector`
   - Email: `jira-connector@your-domain.com`
   - Full Name: `Q Business Connector`
4. Add user to `jira-administrators` group

**Configure API Access:**
1. Go to Administration → System → General Configuration
2. Enable "Accept remote API calls"
3. Note the Base URL for your connector configuration

**Test API Access:**
```bash
# Test REST API connectivity
curl -u jira-connector:password \
  http://your-ec2-public-ip:8080/rest/api/2/myself
```

### Step 8: Update Connector Configuration

Update your `.env` file with the new Jira instance details:

```bash
# Jira Configuration
JIRA_SERVER_URL=http://your-ec2-public-ip:8080
JIRA_USERNAME=jira-connector
JIRA_PASSWORD=your-service-account-password
JIRA_VERIFY_SSL=false  # Since we're using HTTP
JIRA_TIMEOUT=30
```

### Step 9: Test Connector

```bash
# Test connections
jira-q-connector doctor

# Perform sync
jira-q-connector sync

# Clean sync (delete duplicates first)
jira-q-connector sync --clean
```

### Troubleshooting

**Common Issues:**

**Jira Won't Start:**
```bash
# Check Java version
java -version

# Check available memory
free -h

# Increase Jira memory (if needed)
sudo nano /opt/atlassian/jira/bin/setenv.sh
# Add: JVM_MINIMUM_MEMORY="1024m"
# Add: JVM_MAXIMUM_MEMORY="2048m"
```

**Database Connection Issues:**
```bash
# Test PostgreSQL connection
sudo -u postgres psql -d jiradb -U jirauser -h localhost

# Check PostgreSQL status
sudo systemctl status postgresql
```

**Network Access Issues:**
```bash
# Check if Jira is listening on port 8080
sudo netstat -tlnp | grep 8080

# Verify security group rules
aws ec2 describe-security-groups --group-ids sg-xxxxxxxxx
```

**Performance Optimization:**
```bash
# For production use, consider:
# - Using RDS PostgreSQL instead of local database
# - Setting up SSL/HTTPS with certificates
# - Using Application Load Balancer
# - Configuring automatic backups
# - Setting up CloudWatch monitoring
```

### Security Considerations

**For Production Use:**
- Use HTTPS with valid SSL certificates
- Restrict security group access to specific IP ranges
- Use RDS for database with encryption
- Enable CloudTrail and VPC Flow Logs
- Regular security updates and patches
- Backup automation with point-in-time recovery

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

## 🔒 Access Control (ACL) Support

The connector implements comprehensive ACL synchronization using Jira's exact permission model, ensuring that document access in Q Business matches Jira permissions precisely.

### 4-Step Permission Extraction Process

The connector follows this exact process for each document:

1. **Get Project Permission Scheme** (`/rest/api/2/project/{projectKey}/permissionscheme`)
   - Extract the permission scheme ID for the project

2. **Get Permission Scheme Grants** (`/rest/api/2/permissionscheme/{schemeId}/permission`)
   - Extract all BROWSE_PROJECTS permission grants from the scheme

3. **Get Role Actors** (`/rest/api/2/project/{projectKey}/role/{roleId}`)
   - For each project role grant, get all actors (users and groups)
   - Extract both `atlassian-user-role-actor` and `atlassian-group-role-actor` types

4. **Expand Groups to Users** (`/rest/api/2/group/member`)
   - For each group-role-actor, get all individual group members
   - Build comprehensive user list with individual email addresses

### Advanced ACL Format

Each document gets a properly formatted ACL with individual users AND groups:

```json
{
  "accessConfiguration": {
    "accessControls": [
      {
        "principals": [
          {"user": {"id": "user1@company.com", "access": "ALLOW", "membershipType": "DATASOURCE"}},
          {"user": {"id": "user2@company.com", "access": "ALLOW", "membershipType": "DATASOURCE"}},
          {"group": {"name": "jira-administrators", "access": "ALLOW", "membershipType": "DATASOURCE"}},
          {"group": {"name": "project-users", "access": "ALLOW", "membershipType": "DATASOURCE"}}
        ],
        "memberRelation": "OR"
      }
    ]
  }
}
```

### Permission Mapping

The connector maps Jira permissions to Q Business as follows:

- **Direct Users**: Users with direct BROWSE_PROJECTS permission → Individual user principals
- **Direct Groups**: Groups with direct BROWSE_PROJECTS permission → Group principals + individual users
- **Project Roles**: Users/groups in project roles with BROWSE_PROJECTS → Individual user principals + group principals
- **Group Expansion**: All group members are individually listed as user principals
- **Fallback Access**: Projects get default access groups (`jira-project-{key}`, `jira-administrators`)

### Setup Requirements

1. **Jira API Access**: The service account needs permission to:
   - Read project permission schemes
   - Read permission scheme grants  
   - Read project role actors
   - Read group membership

2. **Q Business Permissions**: Ensure your IAM policy includes:
   ```json
   {
       "Effect": "Allow",
       "Action": [
           "qbusiness:BatchPutDocument",
           "qbusiness:BatchPutUserGroupStore",
           "qbusiness:BatchDeleteUserGroupStore"
       ],
       "Resource": [
           "arn:aws:qbusiness:*:*:application/*/index/*",
           "arn:aws:qbusiness:*:*:application/*/index/*/user-group-store"
       ]
   }
   ```

### User Store Synchronization

The connector automatically synchronizes:
- **Users**: All users found in permission grants (with create/update logic)
- **Groups**: Group references are preserved in document ACL (but group creation is disabled to avoid Q Business version limits)
- **Membership**: Individual users are explicitly listed in document ACL for precise access control

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

Each Jira issue is converted to a comprehensive Q Business document with rich content and extensive metadata:

### Content (Searchable Text)

**Core Information:**
- Issue key, title, and description (with ADF/HTML cleaning)
- Status, priority, issue type (with descriptions)
- Project information (name, description, category)
- People details (assignee, reporter, creator with emails)
- Resolution status and descriptions

**Rich Metadata:**
- Labels, components (with descriptions), and versions
- Environment details and security levels
- Time tracking (original estimate, remaining, time spent)
- Progress tracking and work ratios
- Votes, watchers, and attachment information
- Parent/child relationships and subtask details
- Issue links (inward/outward with relationship types)

**Agile & Custom Fields:**
- Epic Link, Story Points, Sprint information
- Team assignments and business value
- Acceptance criteria and risk assessments
- All custom fields (automatically extracted)

**Optional Content:**
- Comments with authors and timestamps (if enabled)
- Change history with field transitions (if enabled)

### Attributes (Filterable/Faceted Search)

**60+ Comprehensive Attributes Including:**

**Core Attributes:**
- `_source_uri`: Direct link to Jira issue
- `jira_issue_key`: Issue key (e.g., "PROJ-123")
- `jira_issue_id`: Numeric issue ID
- `jira_project`: Project key
- `jira_project_name`: Full project name
- `jira_project_category`: Project category

**Status & Type:**
- `jira_status`: Current status
- `jira_status_category`: Status category (To Do, In Progress, Done)
- `jira_issue_type`: Issue type name
- `jira_is_subtask`: Boolean indicator
- `jira_priority`: Priority level
- `jira_resolution`: Resolution status

**People & Dates:**
- `jira_assignee`: Assigned user display name
- `jira_assignee_email`: Assignee email address
- `jira_assignee_username`: Assignee username
- `jira_reporter`: Reporter display name
- `jira_reporter_email`: Reporter email address
- `jira_creator`: Creator display name
- `jira_created`: Creation date
- `jira_updated`: Last update date
- `jira_due_date`: Due date
- `jira_resolution_date`: Resolution date

**Content & Structure:**
- `jira_labels`: Issue labels (array)
- `jira_components`: Components (array)
- `jira_fix_versions`: Fix versions (array)
- `jira_affects_versions`: Affects versions (array)
- `jira_environment`: Environment description
- `jira_security_level`: Security level

**Time Tracking:**
- `jira_original_estimate`: Original time estimate
- `jira_remaining_estimate`: Remaining time estimate
- `jira_time_spent`: Time spent
- `jira_original_estimate_seconds`: Numeric original estimate
- `jira_remaining_estimate_seconds`: Numeric remaining estimate
- `jira_time_spent_seconds`: Numeric time spent
- `jira_work_ratio`: Work completion ratio

**Progress & Engagement:**
- `jira_progress_percent`: Progress percentage
- `jira_progress_total`: Total progress units
- `jira_votes`: Vote count
- `jira_watchers`: Watcher count

**Attachments & Relationships:**
- `jira_attachment_count`: Number of attachments
- `jira_attachment_names`: Attachment filenames (array)
- `jira_subtask_count`: Number of subtasks
- `jira_subtask_keys`: Subtask keys (array)
- `jira_parent_key`: Parent issue key (for subtasks)
- `jira_inward_links`: Inward issue links (array)
- `jira_outward_links`: Outward issue links (array)
- `jira_link_types`: Link relationship types (array)

**Agile Fields:**
- `jira_epic_link`: Epic relationship
- `jira_story_points`: Story point estimate
- `jira_sprint`: Sprint names (array)
- `jira_team`: Team assignment
- `jira_business_value`: Business value score
- `jira_risk`: Risk assessment

**Custom Fields:**
- `jira_customfield_*`: All custom fields automatically extracted
- Supports string, number, array, and object custom field types
- Agile tools fields (Epic Name, Epic Status, Rank, etc.)

### Access Configuration

Each document includes comprehensive ACL with individual users and groups:
```json
{
  "accessConfiguration": {
    "accessControls": [
      {
        "principals": [
          {"user": {"id": "user@company.com", "access": "ALLOW", "membershipType": "DATASOURCE"}},
          {"group": {"name": "project-team", "access": "ALLOW", "membershipType": "DATASOURCE"}}
        ],
        "memberRelation": "OR"
      }
    ]
  }
}
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

Enable comprehensive debug logging to see exactly what content and metadata is being sent to Q Business:

```bash
# Enable debug mode (recommended for troubleshooting)
jira-q-connector sync --debug

# Alternative: Set log level explicitly
jira-q-connector sync --log-level DEBUG

# Debug mode for specific commands
jira-q-connector doctor --debug
jira-q-connector status --debug

# Or set environment variable
export LOG_LEVEL=DEBUG
jira-q-connector sync
```

**Debug Output Includes:**
- **Complete API Payloads**: Full JSON structure sent to Q Business BatchPutDocument API
- **Raw Content Display**: Actual searchable text content (not truncated)
- **Comprehensive Attributes**: All 60+ attributes extracted from each issue
- **ACL Structure**: Individual users and groups in access configuration
- **Permission Extraction**: 4-step ACL process details with API calls
- **Custom Field Values**: All custom field extraction results
- **API Response Details**: Q Business upload results and any errors

**Example Debug Output:**
```json
{
  "id": "jira-issue-PROJ-123",
  "title": "PROJ-123: Sample Issue Title",
  "content": {
    "blob": "Issue Key: PROJ-123\nTitle: Sample Issue Title\n\nDescription:\nDetailed issue description...\n\nStatus: In Progress\nPriority: High\nAssignee: John Doe\nReporter: Jane Smith\nComponents: Backend, API\nSprint: Sprint 25\nStory Points: 8\n..."
  },
  "attributes": [
    {"name": "_source_uri", "value": {"stringValue": "https://jira.company.com/browse/PROJ-123"}},
    {"name": "jira_issue_key", "value": {"stringValue": "PROJ-123"}},
    {"name": "jira_story_points", "value": {"longValue": 8}},
    {"name": "jira_sprint", "value": {"stringListValue": ["Sprint 25"]}},
    ...
  ],
  "contentType": "PLAIN_TEXT",
  "accessConfiguration": {
    "accessControls": [
      {
        "principals": [
          {"user": {"id": "john.doe@company.com", "access": "ALLOW", "membershipType": "DATASOURCE"}},
          {"user": {"id": "jane.smith@company.com", "access": "ALLOW", "membershipType": "DATASOURCE"}},
          {"group": {"name": "project-team", "access": "ALLOW", "membershipType": "DATASOURCE"}}
        ],
        "memberRelation": "OR"
      }
    ]
  }
}
```

## 🔍 Enhanced Search Capabilities

With comprehensive content extraction and 60+ attributes, users can perform sophisticated searches and filtering:

### Natural Language Search Examples

**Content-Based Queries:**
- "Show me all issues with acceptance criteria about user authentication"
- "Find bugs with high priority that have attachments"
- "Issues in Sprint 25 that are assigned to John Doe"
- "Stories with more than 5 story points that are behind schedule"

**Advanced Field Searches:**
- "Issues with original estimate greater than 40 hours"
- "Find all epics linked to project MOBILE"
- "Show me issues created last week with security level restrictions"
- "Tasks that have been in progress for more than 30 days"

### Faceted Filtering & Attributes

**Filter by Status & Progress:**
- Status category (To Do, In Progress, Done)
- Priority levels and resolution status
- Progress percentage and work ratios
- Time estimates vs. actual time spent

**Filter by People & Assignments:**
- Assignee, reporter, or creator email addresses
- Team assignments and role responsibilities
- Vote counts and watcher engagement

**Filter by Agile & Project Management:**
- Story points and business value scores
- Sprint assignments and team allocations
- Epic relationships and parent/child hierarchies
- Risk assessments and environment specifications

**Filter by Content & Relationships:**
- Components, versions, and labels
- Issue link types and relationships
- Attachment counts and file types
- Custom field values (any field automatically supported)

### Advanced Use Cases

**Project Managers:**
- "Show me all high-priority issues in current sprint with story points > 8"
- "Find issues that are overdue based on due date and still in progress"
- "Display all epics with linked stories that have acceptance criteria"

**Developers:**
- "Find all bugs assigned to me with attachments and time estimates"
- "Show me issues I reported that are still unresolved"
- "Display all tasks linked to epic MOBILE-123 with environment details"

**Business Users:**
- "Find all features with high business value that are completed this quarter"
- "Show me all issues with customer impact that have votes > 10"
- "Display all enhancement requests with risk assessment"

## 📈 Performance Tuning

### Batch Size Optimization
- **All installations**: `BATCH_SIZE=10` (AWS Q Business limit)
- Note: AWS Q Business BatchPutDocument API has a maximum of 10 documents per batch

### Memory Usage
- Disable comments for memory-intensive syncs: `INCLUDE_COMMENTS=false`
- Use batching to process large datasets efficiently

### Network Optimization
- Increase timeout for slow networks: `JIRA_TIMEOUT=60`
- Reduce batch size for unstable connections

## 🔄 Scheduling

### Cron Example
```bash
# Daily sync at 2 AM
0 2 * * * /usr/local/bin/jira-q-connector sync > /var/log/jira-sync.log 2>&1

# Weekly sync with clean on Sundays at 1 AM
0 1 * * 0 /usr/local/bin/jira-q-connector sync --clean > /var/log/jira-full-sync.log 2>&1

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

**🎯 Recent Enhancements**: This connector now includes comprehensive content extraction (60+ fields), advanced ACL integration with 4-step permission mapping, individual user resolution, and enhanced debug capabilities for optimal Q Business integration.

**📧 Support**: For issues and questions, please open a GitHub issue.
