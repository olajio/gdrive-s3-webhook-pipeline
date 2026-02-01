# ==================================================
# Customer Care Call Processing System - Variables
# ==================================================

# -------------------------
# General Configuration
# -------------------------

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "customer-care-call-processor"
}

# -------------------------
# S3 Configuration
# -------------------------

variable "s3_bucket_name" {
  description = "S3 bucket name for storing call recordings, transcripts, and summaries"
  type        = string
}

# -------------------------
# Google Drive Configuration
# -------------------------

variable "gdrive_folder_id" {
  description = "Google Drive folder ID to watch for new call recordings"
  type        = string
}

variable "google_credentials_secret_name" {
  description = "AWS Secrets Manager secret name containing Google service account credentials"
  type        = string
  default     = "google-drive-credentials"
}

# -------------------------
# Amazon Cognito Configuration
# -------------------------

variable "cognito_user_pool_name" {
  description = "Name of the Cognito User Pool"
  type        = string
  default     = "call-processor-users"
}

variable "cognito_domain_prefix" {
  description = "Domain prefix for Cognito hosted UI"
  type        = string
  default     = "call-processor"
}

# -------------------------
# Amazon Bedrock Configuration
# -------------------------

variable "bedrock_model_id" {
  description = "Bedrock model ID for AI summarization"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

variable "bedrock_max_tokens" {
  description = "Maximum tokens for Bedrock response"
  type        = number
  default     = 4096
}

# -------------------------
# Lambda Configuration
# -------------------------

variable "webhook_handler_memory" {
  description = "Memory allocation for webhook handler Lambda (MB)"
  type        = number
  default     = 512
}

variable "webhook_handler_timeout" {
  description = "Timeout for webhook handler Lambda (seconds)"
  type        = number
  default     = 60
}

variable "processing_lambda_memory" {
  description = "Memory allocation for processing Lambdas (MB)"
  type        = number
  default     = 512
}

variable "processing_lambda_timeout" {
  description = "Timeout for processing Lambdas (seconds)"
  type        = number
  default     = 300
}

variable "bedrock_lambda_memory" {
  description = "Memory allocation for Bedrock summarization Lambda (MB)"
  type        = number
  default     = 1024
}

variable "bedrock_lambda_timeout" {
  description = "Timeout for Bedrock summarization Lambda (seconds)"
  type        = number
  default     = 600
}

# -------------------------
# DynamoDB Configuration
# -------------------------

variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode (PROVISIONED or PAY_PER_REQUEST)"
  type        = string
  default     = "PAY_PER_REQUEST"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name for call summaries"
  type        = string
  default     = "call-summaries"
}

variable "connections_table_name" {
  description = "DynamoDB table name for WebSocket connections"
  type        = string
  default     = "websocket-connections"
}

# -------------------------
# Monitoring & Alerts
# -------------------------

variable "alert_email" {
  description = "Email address for SNS alerts"
  type        = string
  default     = ""
}

variable "enable_api_gateway_logging" {
  description = "Enable CloudWatch logging for API Gateway"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# -------------------------
# Tags
# -------------------------

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
