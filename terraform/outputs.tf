output "api_gateway_url" {
  description = "API Gateway webhook endpoint URL"
  value       = aws_apigatewayv2_stage.webhook.invoke_url
}

output "s3_bucket_name" {
  description = "S3 bucket name for synced files"
  value       = aws_s3_bucket.gdrive_sync.id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.gdrive_sync.arn
}

output "webhook_handler_function_name" {
  description = "Webhook handler Lambda function name"
  value       = aws_lambda_function.webhook_handler.function_name
}

output "webhook_handler_function_arn" {
  description = "Webhook handler Lambda function ARN"
  value       = aws_lambda_function.webhook_handler.arn
}

output "channel_renewal_function_name" {
  description = "Channel renewal Lambda function name"
  value       = aws_lambda_function.channel_renewal.function_name
}

output "channel_renewal_function_arn" {
  description = "Channel renewal Lambda function ARN"
  value       = aws_lambda_function.channel_renewal.arn
}

output "channels_table_name" {
  description = "DynamoDB table for channel management"
  value       = aws_dynamodb_table.gdrive_channels.name
}

output "sync_log_table_name" {
  description = "DynamoDB table for sync audit log"
  value       = aws_dynamodb_table.gdrive_s3_sync_log.name
}

output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}

output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.webhook_metrics.dashboard_name}"
}

output "deployment_instructions" {
  description = "Next steps after Terraform deployment"
  value = <<-EOT
    Deployment complete! Next steps:
    
    1. Store Google service account credentials in Secrets Manager:
       aws secretsmanager create-secret \\
         --name gdrive-webhook-credentials \\
         --secret-string file://path/to/service-account-key.json
    
    2. Generate and store webhook token:
       WEBHOOK_TOKEN=$(openssl rand -hex 32)
       aws secretsmanager create-secret \\
         --name gdrive-webhook-config \\
         --secret-string "{\"webhook_token\":\"$WEBHOOK_TOKEN\"}"
    
    3. Deploy Lambda code:
       cd ../src/lambda
       zip -r lambda.zip *.py
       aws lambda update-function-code \\
         --function-name ${aws_lambda_function.webhook_handler.function_name} \\
         --zip-file fileb://lambda.zip
       aws lambda update-function-code \\
         --function-name ${aws_lambda_function.channel_renewal.function_name} \\
         --zip-file fileb://lambda.zip
    
    4. Subscribe to SNS alerts (if alert_email was provided):
       Check your email and confirm the subscription
    
    5. Trigger initial channel creation:
       aws lambda invoke \\
         --function-name ${aws_lambda_function.channel_renewal.function_name} \\
         --payload '{}' \\
         response.json
    
    6. Webhook endpoint URL: ${aws_apigatewayv2_stage.webhook.invoke_url}
    
    7. Monitor dashboard: ${aws_cloudwatch_dashboard.webhook_metrics.dashboard_name}
  EOT
}
