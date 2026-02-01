# ==================================================
# Customer Care Call Processing System - Outputs
# ==================================================

# -------------------------
# API Endpoints
# -------------------------

output "api_gateway_url" {
  description = "REST API base URL"
  value       = aws_apigatewayv2_stage.rest_api.invoke_url
}

output "webhook_endpoint" {
  description = "Webhook endpoint for Google Drive notifications"
  value       = "${aws_apigatewayv2_stage.rest_api.invoke_url}/webhook"
}

output "websocket_endpoint" {
  description = "WebSocket endpoint for real-time notifications"
  value       = aws_apigatewayv2_stage.websocket.invoke_url
}

# -------------------------
# S3 Bucket
# -------------------------

output "s3_bucket_name" {
  description = "S3 bucket for call recordings, transcripts, and summaries"
  value       = aws_s3_bucket.call_storage.id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.call_storage.arn
}

# -------------------------
# DynamoDB Tables
# -------------------------

output "call_summaries_table" {
  description = "DynamoDB table for call summaries"
  value       = aws_dynamodb_table.call_summaries.name
}

output "websocket_connections_table" {
  description = "DynamoDB table for WebSocket connections"
  value       = aws_dynamodb_table.websocket_connections.name
}

output "webhook_channels_table" {
  description = "DynamoDB table for webhook channels"
  value       = aws_dynamodb_table.webhook_channels.name
}

# -------------------------
# Step Functions
# -------------------------

output "step_function_arn" {
  description = "Step Functions state machine ARN"
  value       = aws_sfn_state_machine.call_processing.arn
}

output "step_function_name" {
  description = "Step Functions state machine name"
  value       = aws_sfn_state_machine.call_processing.name
}

# -------------------------
# Lambda Functions
# -------------------------

output "lambda_functions" {
  description = "Map of Lambda function names"
  value = {
    webhook_handler    = aws_lambda_function.webhook_handler.function_name
    start_transcribe   = aws_lambda_function.start_transcribe.function_name
    process_transcript = aws_lambda_function.process_transcript.function_name
    generate_summary   = aws_lambda_function.generate_summary.function_name
    save_summary       = aws_lambda_function.save_summary.function_name
    list_summaries     = aws_lambda_function.list_summaries.function_name
    get_summary        = aws_lambda_function.get_summary.function_name
    ws_connect         = aws_lambda_function.websocket_connect.function_name
    ws_disconnect      = aws_lambda_function.websocket_disconnect.function_name
    ws_notify          = aws_lambda_function.websocket_notify.function_name
  }
}

# -------------------------
# SNS
# -------------------------

output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}

# -------------------------
# Deployment Instructions
# -------------------------

output "deployment_instructions" {
  description = "Next steps after Terraform deployment"
  value       = <<-EOT
    ╔══════════════════════════════════════════════════════════════════╗
    ║       Customer Care Call Processing System - Deployment          ║
    ╚══════════════════════════════════════════════════════════════════╝
    
    Deployment complete! Follow these steps to finish setup:
    
    ═══════════════════════════════════════════════════════════════════
    STEP 1: Store Google Service Account Credentials
    ═══════════════════════════════════════════════════════════════════
    
    aws secretsmanager create-secret \
      --name ${var.google_credentials_secret_name} \
      --secret-string file://path/to/service-account-key.json
    
    ═══════════════════════════════════════════════════════════════════
    STEP 2: Generate and Store Webhook Token
    ═══════════════════════════════════════════════════════════════════
    
    WEBHOOK_TOKEN=$(openssl rand -hex 32)
    aws secretsmanager create-secret \
      --name ${var.project_name}-webhook-config \
      --secret-string "{\"webhook_token\":\"$WEBHOOK_TOKEN\"}"
    
    ═══════════════════════════════════════════════════════════════════
    STEP 3: Create Initial Cognito Users
    ═══════════════════════════════════════════════════════════════════
    
    # Create admin user
    aws cognito-idp admin-create-user \
      --user-pool-id ${aws_cognito_user_pool.main.id} \
      --username admin@example.com \
      --user-attributes Name=email,Value=admin@example.com Name=name,Value="Admin User"
    
    # Add to admin group
    aws cognito-idp admin-add-user-to-group \
      --user-pool-id ${aws_cognito_user_pool.main.id} \
      --username admin@example.com \
      --group-name admin
    
    ═══════════════════════════════════════════════════════════════════
    STEP 4: Register Google Drive Webhook
    ═══════════════════════════════════════════════════════════════════
    
    Run the channel registration script:
    python scripts/register_webhook.py \
      --folder-id ${var.gdrive_folder_id} \
      --webhook-url ${aws_apigatewayv2_stage.rest_api.invoke_url}/webhook
    
    ═══════════════════════════════════════════════════════════════════
    STEP 5: Configure Frontend Environment
    ═══════════════════════════════════════════════════════════════════
    
    Create frontend/.env with:
    
    VITE_API_URL=${aws_apigatewayv2_stage.rest_api.invoke_url}
    VITE_WEBSOCKET_URL=${aws_apigatewayv2_stage.websocket.invoke_url}
    VITE_COGNITO_USER_POOL_ID=${aws_cognito_user_pool.main.id}
    VITE_COGNITO_CLIENT_ID=${aws_cognito_user_pool_client.frontend.id}
    VITE_COGNITO_REGION=${var.aws_region}
    
    ═══════════════════════════════════════════════════════════════════
    ENDPOINTS
    ═══════════════════════════════════════════════════════════════════
    
    REST API:      ${aws_apigatewayv2_stage.rest_api.invoke_url}
    WebSocket:     ${aws_apigatewayv2_stage.websocket.invoke_url}
    Cognito Login: https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com
    
    ═══════════════════════════════════════════════════════════════════
    MONITORING
    ═══════════════════════════════════════════════════════════════════
    
    CloudWatch Dashboard:
    https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${var.project_name}-${var.environment}
    
    Step Functions Console:
    https://console.aws.amazon.com/states/home?region=${var.aws_region}#/statemachines/view/${aws_sfn_state_machine.call_processing.arn}
  EOT
}
