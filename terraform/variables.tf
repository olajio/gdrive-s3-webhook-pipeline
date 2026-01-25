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
  default     = "gdrive-webhook"
}

variable "s3_bucket_name" {
  description = "S3 bucket name for storing synced files"
  type        = string
}

variable "gdrive_folder_id" {
  description = "Google Drive folder ID to watch"
  type        = string
}

variable "allowed_extensions" {
  description = "Comma-separated list of allowed file extensions (e.g., .csv,.json,.parquet)"
  type        = string
  default     = ""
}

variable "max_file_size_mb" {
  description = "Maximum file size in MB to sync"
  type        = number
  default     = 100
}

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

variable "channel_renewal_memory" {
  description = "Memory allocation for channel renewal Lambda (MB)"
  type        = number
  default     = 256
}

variable "channel_renewal_timeout" {
  description = "Timeout for channel renewal Lambda (seconds)"
  type        = number
  default     = 30
}

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

variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode (PROVISIONED or PAY_PER_REQUEST)"
  type        = string
  default     = "PAY_PER_REQUEST"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
