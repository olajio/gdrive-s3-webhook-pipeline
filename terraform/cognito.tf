# ==================================================
# Customer Care Call Processing System - Amazon Cognito
# ==================================================

# Cognito User Pool
resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-users-${var.environment}"

  # Username configuration
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # Password policy
  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  # MFA configuration
  mfa_configuration = var.environment == "prod" ? "ON" : "OPTIONAL"

  software_token_mfa_configuration {
    enabled = true
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Email configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # User attribute schema
  schema {
    name                     = "email"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 5
      max_length = 256
    }
  }

  schema {
    name                     = "name"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  schema {
    name                     = "department"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 0
      max_length = 256
    }
  }

  # Verification message template
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "Your verification code"
    email_message        = "Your verification code is {####}"
  }

  # Admin create user config
  admin_create_user_config {
    allow_admin_create_user_only = false

    invite_message_template {
      email_subject = "Welcome to Customer Care Call Processor"
      email_message = "Your username is {username} and temporary password is {####}. Please log in and change your password."
      sms_message   = "Your username is {username} and temporary password is {####}"
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-users-${var.environment}"
    }
  )
}

# Cognito User Pool Domain
resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.cognito_domain_prefix}-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main.id
}

# Cognito User Pool Client for React Frontend
resource "aws_cognito_user_pool_client" "frontend" {
  name         = "${var.project_name}-frontend-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = false # SPA apps should not have secrets

  # OAuth settings
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["email", "openid", "profile"]

  callback_urls = var.environment == "prod" ? [
    "https://your-production-domain.com/callback"
    ] : [
    "http://localhost:3000/callback",
    "http://localhost:5173/callback"
  ]

  logout_urls = var.environment == "prod" ? [
    "https://your-production-domain.com"
    ] : [
    "http://localhost:3000",
    "http://localhost:5173"
  ]

  supported_identity_providers = ["COGNITO"]

  # Token validity
  access_token_validity  = 1  # hours
  id_token_validity      = 1  # hours
  refresh_token_validity = 30 # days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # Enable SRP authentication
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  prevent_user_existence_errors = "ENABLED"
}

# User Groups

# Caseworkers group
resource "aws_cognito_user_group" "caseworkers" {
  name         = "caseworkers"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Caseworkers who handle customer calls"
  precedence   = 3
}

# Supervisors group
resource "aws_cognito_user_group" "supervisors" {
  name         = "supervisors"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Supervisors who oversee caseworkers"
  precedence   = 2
}

# Administrators group
resource "aws_cognito_user_group" "admins" {
  name         = "admin"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "System administrators with full access"
  precedence   = 1
}

# Outputs for Cognito
output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_arn" {
  description = "Cognito User Pool ARN"
  value       = aws_cognito_user_pool.main.arn
}

output "cognito_client_id" {
  description = "Cognito User Pool Client ID for frontend"
  value       = aws_cognito_user_pool_client.frontend.id
}

output "cognito_domain" {
  description = "Cognito hosted UI domain"
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com"
}
