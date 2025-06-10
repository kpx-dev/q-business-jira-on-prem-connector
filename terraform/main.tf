# Jira Q Business Connector - ECS Fargate Deployment
# This Terraform template deploys the connector as a scheduled ECS Fargate task

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "jira-q-connector"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Data sources for existing resources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# VPC and Networking
resource "aws_vpc" "main" {
  count = var.create_vpc ? 1 : 0

  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  count = var.create_vpc ? 1 : 0

  vpc_id = aws_vpc.main[0].id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

resource "aws_subnet" "private" {
  count = var.create_vpc ? 2 : 0

  vpc_id            = aws_vpc.main[0].id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-private-subnet-${count.index + 1}"
    Type = "private"
  }
}

resource "aws_subnet" "public" {
  count = var.create_vpc ? 2 : 0

  vpc_id                  = aws_vpc.main[0].id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index + 101)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet-${count.index + 1}"
    Type = "public"
  }
}

# NAT Gateway for private subnets
resource "aws_eip" "nat" {
  count = var.create_vpc ? 1 : 0

  domain = "vpc"

  tags = {
    Name = "${var.project_name}-nat-eip"
  }

  depends_on = [aws_internet_gateway.main]
}

resource "aws_nat_gateway" "main" {
  count = var.create_vpc ? 1 : 0

  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name = "${var.project_name}-nat"
  }

  depends_on = [aws_internet_gateway.main]
}

# Route Tables
resource "aws_route_table" "public" {
  count = var.create_vpc ? 1 : 0

  vpc_id = aws_vpc.main[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main[0].id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table" "private" {
  count = var.create_vpc ? 1 : 0

  vpc_id = aws_vpc.main[0].id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[0].id
  }

  tags = {
    Name = "${var.project_name}-private-rt"
  }
}

resource "aws_route_table_association" "public" {
  count = var.create_vpc ? 2 : 0

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

resource "aws_route_table_association" "private" {
  count = var.create_vpc ? 2 : 0

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[0].id
}

# Security Group
resource "aws_security_group" "ecs_task" {
  name_prefix = "${var.project_name}-ecs-task-"
  description = "Security group for Jira Q Connector ECS task"
  vpc_id      = var.create_vpc ? aws_vpc.main[0].id : var.existing_vpc_id

  # Outbound internet access for API calls
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "${var.project_name}-ecs-task-sg"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "connector" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-logs"
  }
}

# DynamoDB Table for Caching
resource "aws_dynamodb_table" "cache" {
  count = var.enable_cache ? 1 : 0

  name         = var.cache_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "document_id"

  attribute {
    name = "document_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-cache"
  }
}

# Secrets Manager for sensitive configuration
resource "aws_secretsmanager_secret" "jira_credentials" {
  name        = "${var.project_name}/jira-credentials"
  description = "Jira credentials for Q Business Connector"

  tags = {
    Name = "${var.project_name}-jira-creds"
  }
}

resource "aws_secretsmanager_secret_version" "jira_credentials" {
  secret_id = aws_secretsmanager_secret.jira_credentials.id
  secret_string = jsonencode({
    JIRA_USERNAME = var.jira_username
    JIRA_PASSWORD = var.jira_password
  })
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_execution" {
  name_prefix = "${var.project_name}-ecs-execution-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecs-execution-role"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_basic" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name_prefix = "${var.project_name}-secrets-"
  role        = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.jira_credentials.arn
        ]
      }
    ]
  })
}

# IAM Role for ECS Task
resource "aws_iam_role" "ecs_task" {
  name_prefix = "${var.project_name}-ecs-task-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecs-task-role"
  }
}

resource "aws_iam_role_policy" "ecs_task_qbusiness" {
  name_prefix = "${var.project_name}-qbusiness-"
  role        = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "qbusiness:BatchPutDocument",
          "qbusiness:BatchDeleteDocument",
          "qbusiness:StartDataSourceSyncJob",
          "qbusiness:StopDataSourceSyncJob",
          "qbusiness:GetDataSourceSyncJob",
          "qbusiness:ListDataSourceSyncJobs",
          "qbusiness:GetApplication"
        ]
        Resource = [
          "arn:aws:qbusiness:${var.aws_region}:${data.aws_caller_identity.current.account_id}:application/${var.q_application_id}",
          "arn:aws:qbusiness:${var.aws_region}:${data.aws_caller_identity.current.account_id}:application/${var.q_application_id}/index/${var.q_index_id}",
          "arn:aws:qbusiness:${var.aws_region}:${data.aws_caller_identity.current.account_id}:application/${var.q_application_id}/index/${var.q_index_id}/data-source/${var.q_data_source_id}"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "ecs_task_dynamodb" {
  count = var.enable_cache ? 1 : 0

  name_prefix = "${var.project_name}-dynamodb-"
  role        = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:CreateTable",
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:Scan",
          "dynamodb:DescribeTable"
        ]
        Resource = [
          aws_dynamodb_table.cache[0].arn
        ]
      }
    ]
  })
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = var.project_name

  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"

      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.connector.name
      }
    }
  }

  tags = {
    Name = "${var.project_name}-cluster"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "connector" {
  family                   = var.project_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "jira-q-connector"
      image = var.container_image

      essential = true

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.connector.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      environment = concat(
        [
          {
            name  = "JIRA_SERVER_URL"
            value = var.jira_server_url
          },
          {
            name  = "JIRA_VERIFY_SSL"
            value = tostring(var.jira_verify_ssl)
          },
          {
            name  = "JIRA_TIMEOUT"
            value = tostring(var.jira_timeout)
          },
          {
            name  = "AWS_REGION"
            value = var.aws_region
          },
          {
            name  = "Q_APPLICATION_ID"
            value = var.q_application_id
          },
          {
            name  = "Q_DATA_SOURCE_ID"
            value = var.q_data_source_id
          },
          {
            name  = "Q_INDEX_ID"
            value = var.q_index_id
          },
          {
            name  = "SYNC_MODE"
            value = var.sync_mode
          },
          {
            name  = "BATCH_SIZE"
            value = tostring(var.batch_size)
          },
          {
            name  = "INCLUDE_COMMENTS"
            value = tostring(var.include_comments)
          },
          {
            name  = "INCLUDE_HISTORY"
            value = tostring(var.include_history)
          },
          {
            name  = "ENABLE_CACHE"
            value = tostring(var.enable_cache)
          }
        ],
        var.enable_cache ? [
          {
            name  = "CACHE_TABLE_NAME"
            value = var.cache_table_name
          }
        ] : [],
        var.projects != null ? [
          {
            name  = "PROJECTS"
            value = join(",", var.projects)
          }
        ] : [],
        var.issue_types != null ? [
          {
            name  = "ISSUE_TYPES"
            value = join(",", var.issue_types)
          }
        ] : [],
        var.jql_filter != null ? [
          {
            name  = "JQL_FILTER"
            value = var.jql_filter
          }
        ] : []
      )

      secrets = [
        {
          name      = "JIRA_USERNAME"
          valueFrom = "${aws_secretsmanager_secret.jira_credentials.arn}:JIRA_USERNAME::"
        },
        {
          name      = "JIRA_PASSWORD"
          valueFrom = "${aws_secretsmanager_secret.jira_credentials.arn}:JIRA_PASSWORD::"
        }
      ]

      command = ["sync", "--cache"]
    }
  ])

  tags = {
    Name = "${var.project_name}-task-definition"
  }
}

# EventBridge Rule for Scheduling
resource "aws_cloudwatch_event_rule" "sync_schedule" {
  name                = "${var.project_name}-sync-schedule"
  description         = "Trigger sync job on schedule"
  schedule_expression = var.sync_schedule

  tags = {
    Name = "${var.project_name}-sync-schedule"
  }
}

resource "aws_cloudwatch_event_target" "ecs_target" {
  rule      = aws_cloudwatch_event_rule.sync_schedule.name
  target_id = "ECSTarget"
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.connector.arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

          network_configuration {
        subnets          = var.create_vpc ? aws_subnet.private[*].id : var.existing_subnet_ids
        security_groups  = [aws_security_group.ecs_task.id]
        assign_public_ip = var.assign_public_ip
      }
  }
}

# IAM Role for EventBridge
resource "aws_iam_role" "eventbridge" {
  name_prefix = "${var.project_name}-eventbridge-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-eventbridge-role"
  }
}

resource "aws_iam_role_policy" "eventbridge_ecs" {
  name_prefix = "${var.project_name}-eventbridge-ecs-"
  role        = aws_iam_role.eventbridge.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask"
        ]
        Resource = [
          aws_ecs_task_definition.connector.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          aws_iam_role.ecs_task_execution.arn,
          aws_iam_role.ecs_task.arn
        ]
      }
    ]
  })
} 