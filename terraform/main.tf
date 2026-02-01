# ==================================================
# Customer Care Call Processing System
# Main Terraform Configuration
# ==================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Configure remote state storage
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "customer-care-call-processor/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "CustomerCareCallProcessor"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Local values for common configurations
locals {
  project_name = "customer-care-call-processor"

  lambda_runtime     = "python3.11"
  lambda_timeout     = 30
  lambda_memory_size = 256

  # Processing Lambda configs (may need more resources)
  processing_lambda_timeout     = 300
  processing_lambda_memory_size = 512

  # Bedrock summarization Lambda (needs even more time for AI)
  bedrock_lambda_timeout     = 600
  bedrock_lambda_memory_size = 1024

  common_tags = {
    Project     = "CustomerCareCallProcessor"
    Environment = var.environment
    Owner       = "DevOps"
  }
}

