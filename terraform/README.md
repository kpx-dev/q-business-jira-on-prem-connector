# Jira Q Business Connector - AWS ECS Deployment

This Terraform template deploys the Jira Q Business Connector as a scheduled ECS Fargate task with all necessary AWS infrastructure.

## 🏗️ Architecture Overview

The deployment creates:

- **ECS Fargate Cluster**: Runs the connector as scheduled tasks
- **EventBridge Rule**: Schedules sync jobs (hourly by default)
- **VPC & Networking**: Private subnets with NAT gateway for internet access
- **IAM Roles**: Task execution and application roles with minimal required permissions
- **DynamoDB Table**: Caching for improved performance (optional)
- **Secrets Manager**: Secure storage for Jira credentials
- **CloudWatch Logs**: Centralized logging and monitoring

## 📋 Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **Terraform** >= 1.0 installed
3. **Docker** for building container images
4. **Amazon Q Business** application, index, and custom data source already created
5. **Jira Server** accessible from AWS (on-premises or cloud)

## 🚀 Quick Start

### Step 1: Build and Push Container Image

First, build and push the connector image to ECR:

```bash
# Create ECR repository
aws ecr create-repository --repository-name jira-q-connector

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag image
docker build -t jira-q-connector .
docker tag jira-q-connector:latest <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/jira-q-connector:latest

# Push image
docker push <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/jira-q-connector:latest
```

### Step 2: Configure Terraform Variables

#### Option A: Environment Variables (Recommended - More Secure)

```bash
# Copy environment template
cp env.terraform.example .env.terraform

# Edit with your credentials (never commit this file!)
nano .env.terraform

# Source environment variables
source .env.terraform
```

#### Option B: Terraform Variables File

```bash
# Copy example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required Variables:**
```hcl
# Container Configuration
container_image = "<your-account-id>.dkr.ecr.us-east-1.amazonaws.com/jira-q-connector:latest"

# Jira Configuration
jira_server_url = "https://your-jira-server.company.com"
jira_username   = "your-jira-username"
jira_password   = "your-jira-password-or-api-token"

# Amazon Q Business Configuration
q_application_id = "your-q-application-id"
q_data_source_id = "your-q-data-source-id"  # Must be CUSTOM type
q_index_id       = "your-q-index-id"
```

### Step 3: Deploy Infrastructure

#### Option A: Using Deploy Script (With Environment Variables)

```bash
# Using the provided deployment script
./deploy.sh plan
./deploy.sh apply

# Or with auto-approval
./deploy.sh apply --auto-approve
```

#### Option B: Direct Terraform Commands

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply changes
terraform apply
```

### Step 4: Verify Deployment

```bash
# Check ECS cluster
aws ecs describe-clusters --clusters jira-q-connector

# View recent logs
aws logs tail /ecs/jira-q-connector --follow

# Run task manually (optional)
terraform output -raw useful_commands | jq -r '."Run task manually"' | bash
```

## 📊 Monitoring and Management

### CloudWatch Logs
All connector logs are sent to CloudWatch Logs group `/ecs/jira-q-connector`.

```bash
# View logs in real-time
aws logs tail /ecs/jira-q-connector --follow

# View logs from specific time
aws logs tail /ecs/jira-q-connector --since 1h
```

### DynamoDB Cache Monitoring
If caching is enabled, monitor cache performance:

```bash
# Check cache statistics
aws dynamodb scan --table-name jira-q-connector-cache --select COUNT

# View cache items
aws dynamodb scan --table-name jira-q-connector-cache --max-items 10
```

### Manual Task Execution
Run sync manually outside the schedule:

```bash
# Get the run command from Terraform output
terraform output -raw useful_commands | jq -r '."Run task manually"'

# Or use the AWS Console ECS > Clusters > jira-q-connector > Tasks > Run new task
```

## 🔧 Configuration Options

### Scheduling

Update the sync schedule by modifying `sync_schedule` variable:

```hcl
# Every 6 hours
sync_schedule = "rate(6 hours)"

# Daily at 2 AM UTC
sync_schedule = "cron(0 2 * * ? *)"

# Weekdays at 9 AM UTC
sync_schedule = "cron(0 9 ? * MON-FRI *)"
```

### Resource Sizing

Adjust compute resources based on your Jira instance size:

```hcl
# Small instance (< 1000 issues)
task_cpu    = 256   # 0.25 vCPU
task_memory = 512   # 512 MB

# Medium instance (1000-10000 issues)
task_cpu    = 512   # 0.5 vCPU
task_memory = 1024  # 1 GB

# Large instance (> 10000 issues)
task_cpu    = 1024  # 1 vCPU
task_memory = 2048  # 2 GB
```

### Filtering

Filter which Jira issues to sync:

```hcl
# Sync specific projects
projects = ["PROJ1", "PROJ2", "PROJ3"]

# Sync specific issue types
issue_types = ["Bug", "Task", "Story"]

# Custom JQL filter
jql_filter = "status != \"Closed\" AND updated >= -30d"
```

## 🔐 Security Considerations

### IAM Permissions
The deployment creates minimal IAM roles with only required permissions:

- **ECS Task Role**: Q Business API access + DynamoDB (if caching enabled)
- **ECS Execution Role**: Pull images, write logs, read secrets
- **EventBridge Role**: Trigger ECS tasks

### Network Security
- Tasks run in private subnets with no direct internet access
- NAT Gateway provides outbound internet for API calls
- Security group allows outbound traffic only

### Secrets Management
- Jira credentials stored in AWS Secrets Manager
- No sensitive data in environment variables or logs
- Secrets automatically rotated when updated

### Environment Variable Security
When using environment variables for Terraform:
- `.env.terraform` files are excluded from git (see `.gitignore`)
- Never commit credential files to version control
- Use temporary environment variables when possible
- Consider using AWS CLI profiles for additional security

## 🛠️ Troubleshooting

### Common Issues

1. **Task fails to start:**
   ```bash
   # Check task definition
   aws ecs describe-task-definition --task-definition jira-q-connector
   
   # Check latest task events
   aws ecs list-tasks --cluster jira-q-connector
   aws ecs describe-tasks --cluster jira-q-connector --tasks <task-arn>
   ```

2. **Cannot pull container image:**
   ```bash
   # Verify ECR repository exists
   aws ecr describe-repositories --repository-names jira-q-connector
   
   # Check ECR permissions
   aws ecr get-authorization-token
   ```

3. **Jira connection issues:**
   ```bash
   # Check Jira credentials in Secrets Manager
   aws secretsmanager get-secret-value --secret-id jira-q-connector/jira-credentials
   
   # Test connectivity manually
   curl -u username:password https://your-jira-server.company.com/rest/api/2/myself
   ```

4. **Q Business API errors:**
   ```bash
   # Verify Q Business configuration
   aws qbusiness get-application --application-id <your-app-id>
   aws qbusiness get-index --application-id <your-app-id> --index-id <your-index-id>
   aws qbusiness get-data-source --application-id <your-app-id> --index-id <your-index-id> --data-source-id <your-ds-id>
   ```

### Debugging Steps

1. **Enable debug logging:**
   Update task definition environment variable:
   ```hcl
   LOG_LEVEL = "DEBUG"
   ```

2. **Run task manually:**
   ```bash
   # Use output command to run task
   terraform output useful_commands
   ```

3. **Check EventBridge rules:**
   ```bash
   # List EventBridge rules
   aws events list-rules --name-prefix jira-q-connector
   
   # Check rule targets
   aws events list-targets-by-rule --rule jira-q-connector-sync-schedule
   ```

## 💰 Cost Optimization

### Fargate Pricing
- **vCPU**: $0.04048 per vCPU per hour
- **Memory**: $0.004445 per GB per hour

Example costs (us-east-1):
- **0.25 vCPU, 512MB**: ~$0.012/hour (~$8.64/month for hourly runs)
- **0.5 vCPU, 1GB**: ~$0.024/hour (~$17.28/month for hourly runs)
- **1 vCPU, 2GB**: ~$0.049/hour (~$35.28/month for hourly runs)

### Cost Reduction Tips
1. **Optimize schedule**: Run less frequently if data doesn't change often
2. **Use caching**: Reduces runtime by skipping unchanged documents
3. **Right-size resources**: Monitor CloudWatch metrics and adjust CPU/memory
4. **Filter data**: Use JQL filters to sync only necessary issues

## 🔄 Updates and Maintenance

### Updating the Application
```bash
# Build and push new image
docker build -t jira-q-connector .
docker tag jira-q-connector:latest <account>.dkr.ecr.us-east-1.amazonaws.com/jira-q-connector:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/jira-q-connector:latest

# Update task definition
terraform apply
```

### Updating Configuration
```bash
# Modify terraform.tfvars
nano terraform.tfvars

# Apply changes
terraform apply
```

### Updating Jira Credentials
```bash
# Update secret directly
aws secretsmanager update-secret \
  --secret-id jira-q-connector/jira-credentials \
  --secret-string '{"JIRA_USERNAME":"new-username","JIRA_PASSWORD":"new-password"}'
```

## 📚 Additional Resources

- [Amazon Q Business Developer Guide](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/)
- [ECS Fargate User Guide](https://docs.aws.amazon.com/AmazonECS/latest/userguide/what-is-fargate.html)
- [EventBridge User Guide](https://docs.aws.amazon.com/eventbridge/latest/userguide/)
- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

## 🆘 Support

For issues related to:
- **Jira Q Connector**: Check the main project README and logs
- **AWS Infrastructure**: Review CloudWatch logs and AWS documentation
- **Terraform**: Validate configuration and check Terraform documentation 