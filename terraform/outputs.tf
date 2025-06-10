# Terraform Outputs for Jira Q Business Connector

# Resource Identifiers
output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.connector.arn
}

output "task_definition_family" {
  description = "Family name of the ECS task definition"
  value       = aws_ecs_task_definition.connector.family
}

output "task_definition_revision" {
  description = "Revision of the ECS task definition"
  value       = aws_ecs_task_definition.connector.revision
}

# IAM Roles
output "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  value       = aws_iam_role.ecs_task.arn
}

output "ecs_execution_role_arn" {
  description = "ARN of the ECS task execution role"
  value       = aws_iam_role.ecs_task_execution.arn
}

# Networking
output "vpc_id" {
  description = "ID of the VPC used for deployment"
  value       = var.create_vpc ? aws_vpc.main[0].id : var.existing_vpc_id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = var.create_vpc ? aws_subnet.private[*].id : var.existing_subnet_ids
}

output "security_group_id" {
  description = "ID of the ECS task security group"
  value       = aws_security_group.ecs_task.id
}

# DynamoDB Cache
output "cache_table_name" {
  description = "Name of the DynamoDB cache table"
  value       = var.enable_cache ? aws_dynamodb_table.cache[0].name : null
}

output "cache_table_arn" {
  description = "ARN of the DynamoDB cache table"
  value       = var.enable_cache ? aws_dynamodb_table.cache[0].arn : null
}

# Secrets Manager
output "secrets_manager_secret_name" {
  description = "Name of the Secrets Manager secret containing Jira credentials"
  value       = aws_secretsmanager_secret.jira_credentials.name
}

output "secrets_manager_secret_arn" {
  description = "ARN of the Secrets Manager secret containing Jira credentials"
  value       = aws_secretsmanager_secret.jira_credentials.arn
}

# CloudWatch Logs
output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.connector.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.connector.arn
}

# EventBridge Scheduling
output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule for scheduling"
  value       = aws_cloudwatch_event_rule.sync_schedule.name
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge rule for scheduling"
  value       = aws_cloudwatch_event_rule.sync_schedule.arn
}

output "sync_schedule" {
  description = "Schedule expression for the sync job"
  value       = var.sync_schedule
}

# Useful Commands
output "useful_commands" {
  description = "Useful AWS CLI commands for managing the deployment"
  value = {
    "Run task manually" = "aws ecs run-task --cluster ${aws_ecs_cluster.main.name} --task-definition ${aws_ecs_task_definition.connector.family} --launch-type FARGATE --network-configuration 'awsvpcConfiguration={subnets=[${join(",", var.create_vpc ? aws_subnet.private[*].id : var.existing_subnet_ids)}],securityGroups=[${aws_security_group.ecs_task.id}],assignPublicIp=${var.assign_public_ip ? "ENABLED" : "DISABLED"}}'"

    "View logs" = "aws logs tail ${aws_cloudwatch_log_group.connector.name} --follow"

    "List running tasks" = "aws ecs list-tasks --cluster ${aws_ecs_cluster.main.name}"

    "Update secret" = "aws secretsmanager update-secret --secret-id ${aws_secretsmanager_secret.jira_credentials.name} --secret-string '{\"JIRA_USERNAME\":\"your-username\",\"JIRA_PASSWORD\":\"your-password\"}'"

    "Check cache stats" = var.enable_cache ? "aws dynamodb scan --table-name ${aws_dynamodb_table.cache[0].name} --select COUNT" : "Cache not enabled"

    "Force new deployment" = "aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${aws_ecs_task_definition.connector.family} --force-new-deployment || echo 'No service created - this is a scheduled task'"
  }
}

# Monitoring URLs (when using AWS Console)
output "monitoring_urls" {
  description = "URLs for monitoring the deployment (replace REGION and ACCOUNT_ID)"
  value = {
    "ECS Cluster" = "https://${var.aws_region}.console.aws.amazon.com/ecs/home?region=${var.aws_region}#/clusters/${aws_ecs_cluster.main.name}"

    "CloudWatch Logs" = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#logsV2:log-groups/log-group/${replace(aws_cloudwatch_log_group.connector.name, "/", "$252F")}"

    "DynamoDB Table" = var.enable_cache ? "https://${var.aws_region}.console.aws.amazon.com/dynamodb/home?region=${var.aws_region}#tables:selected=${aws_dynamodb_table.cache[0].name}" : "Cache not enabled"

    "EventBridge Rules" = "https://${var.aws_region}.console.aws.amazon.com/events/home?region=${var.aws_region}#/rules"

    "Secrets Manager" = "https://${var.aws_region}.console.aws.amazon.com/secretsmanager/home?region=${var.aws_region}#!/secret?name=${aws_secretsmanager_secret.jira_credentials.name}"
  }
} 