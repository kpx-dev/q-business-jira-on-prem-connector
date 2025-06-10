# Terraform Variables for Jira Q Business Connector

# Project Configuration
variable "project_name" {
  description = "Name of the project, used for resource naming"
  type        = string
  default     = "jira-q-connector"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

# Networking Configuration
variable "create_vpc" {
  description = "Whether to create a new VPC or use existing one"
  type        = bool
  default     = true
}

variable "vpc_cidr" {
  description = "CIDR block for VPC (only used if create_vpc is true)"
  type        = string
  default     = "10.0.0.0/16"
}

variable "existing_vpc_id" {
  description = "ID of existing VPC (only used if create_vpc is false)"
  type        = string
  default     = null
}

variable "existing_subnet_ids" {
  description = "List of existing subnet IDs (only used if create_vpc is false)"
  type        = list(string)
  default     = []
}

variable "assign_public_ip" {
  description = "Whether to assign public IP to ECS tasks (needed for internet access from private subnets without NAT)"
  type        = bool
  default     = true
}

# Container Configuration
variable "container_image" {
  description = "Docker image for the Jira Q Connector"
  type        = string
  # You'll need to build and push your image to ECR or Docker Hub
}

variable "task_cpu" {
  description = "CPU units for ECS task (1 vCPU = 1024 units)"
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Memory in MB for ECS task"
  type        = number
  default     = 1024
}

# Jira Configuration
variable "jira_server_url" {
  description = "Jira server URL"
  type        = string
}

variable "jira_username" {
  description = "Jira username (will be stored in Secrets Manager)"
  type        = string
  sensitive   = true
  default     = null
}

variable "jira_password" {
  description = "Jira password or API token (will be stored in Secrets Manager)"
  type        = string
  sensitive   = true
  default     = null
}

variable "jira_verify_ssl" {
  description = "Whether to verify SSL certificates for Jira"
  type        = bool
  default     = true
}

variable "jira_timeout" {
  description = "Timeout in seconds for Jira API requests"
  type        = number
  default     = 30
}

# Amazon Q Business Configuration
variable "q_application_id" {
  description = "Amazon Q Business application ID"
  type        = string
  sensitive   = true
  default     = null
}

variable "q_data_source_id" {
  description = "Amazon Q Business data source ID (must be CUSTOM type)"
  type        = string
  sensitive   = true
  default     = null
}

variable "q_index_id" {
  description = "Amazon Q Business index ID"
  type        = string
  sensitive   = true
  default     = null
}

# Sync Configuration
variable "sync_mode" {
  description = "Sync mode: full or incremental"
  type        = string
  default     = "full"

  validation {
    condition     = contains(["full", "incremental"], var.sync_mode)
    error_message = "Sync mode must be either 'full' or 'incremental'."
  }
}

variable "batch_size" {
  description = "Batch size for document processing (max 10 for Q Business)"
  type        = number
  default     = 10

  validation {
    condition     = var.batch_size > 0 && var.batch_size <= 10
    error_message = "Batch size must be between 1 and 10."
  }
}

variable "include_comments" {
  description = "Whether to include issue comments in sync"
  type        = bool
  default     = true
}

variable "include_history" {
  description = "Whether to include issue change history in sync"
  type        = bool
  default     = false
}

# Filtering Configuration
variable "projects" {
  description = "List of Jira project keys to sync (null means all projects)"
  type        = list(string)
  default     = null
}

variable "issue_types" {
  description = "List of issue types to sync (null means all types)"
  type        = list(string)
  default     = null
}

variable "jql_filter" {
  description = "Custom JQL filter for issue selection"
  type        = string
  default     = null
}

# Caching Configuration
variable "enable_cache" {
  description = "Whether to enable DynamoDB caching"
  type        = bool
  default     = true
}

variable "cache_table_name" {
  description = "Name of DynamoDB table for caching"
  type        = string
  default     = "jira-q-connector-cache"
}

# Scheduling Configuration
variable "sync_schedule" {
  description = "Schedule expression for sync job (EventBridge schedule)"
  type        = string
  default     = "rate(1 hour)"

  # Examples:
  # "rate(1 hour)"           - Every hour
  # "rate(6 hours)"          - Every 6 hours
  # "rate(1 day)"            - Daily
  # "cron(0 9 * * ? *)"      - Daily at 9 AM UTC
  # "cron(0 9 ? * MON-FRI *)" - Weekdays at 9 AM UTC
}

# Monitoring Configuration
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30

  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653
    ], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
} 