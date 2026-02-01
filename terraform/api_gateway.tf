# ==================================================
# Customer Care Call Processing System - API Gateway
# ==================================================

# -------------------------
# REST API (HTTP API)
# -------------------------

resource "aws_apigatewayv2_api" "rest_api" {
  name          = "${var.project_name}-api-${var.environment}"
  protocol_type = "HTTP"
  description   = "Customer Care Call Processing REST API"

  cors_configuration {
    allow_origins = var.environment == "prod" ? ["https://your-production-domain.com"] : ["http://localhost:3000", "http://localhost:5173"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key"]
    max_age       = 300
  }
}

# Cognito Authorizer
resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.rest_api.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito-authorizer"

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.frontend.id]
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.main.id}"
  }
}

# -------------------------
# Webhook Route (No Auth - Google Drive calls this)
# -------------------------

resource "aws_apigatewayv2_integration" "webhook_handler" {
  api_id                 = aws_apigatewayv2_api.rest_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.webhook_handler.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "webhook" {
  api_id    = aws_apigatewayv2_api.rest_api.id
  route_key = "POST /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.webhook_handler.id}"
}

# -------------------------
# Summaries Routes (Authenticated)
# -------------------------

# List Summaries
resource "aws_apigatewayv2_integration" "list_summaries" {
  api_id                 = aws_apigatewayv2_api.rest_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.list_summaries.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "list_summaries" {
  api_id             = aws_apigatewayv2_api.rest_api.id
  route_key          = "GET /summaries"
  target             = "integrations/${aws_apigatewayv2_integration.list_summaries.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Get Summary Detail
resource "aws_apigatewayv2_integration" "get_summary" {
  api_id                 = aws_apigatewayv2_api.rest_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_summary.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_summary" {
  api_id             = aws_apigatewayv2_api.rest_api.id
  route_key          = "GET /summaries/{call_id}"
  target             = "integrations/${aws_apigatewayv2_integration.get_summary.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# -------------------------
# API Stage
# -------------------------

resource "aws_apigatewayv2_stage" "rest_api" {
  api_id      = aws_apigatewayv2_api.rest_api.id
  name        = var.environment
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      errorMessage   = "$context.error.message"
      userId         = "$context.authorizer.claims.sub"
    })
  }

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }

  tags = var.tags
}

# -------------------------
# WebSocket API
# -------------------------

resource "aws_apigatewayv2_api" "websocket" {
  name                       = "${var.project_name}-websocket-${var.environment}"
  protocol_type              = "WEBSOCKET"
  route_selection_expression = "$request.body.action"
  description                = "Real-time notifications for call processing"
}

# WebSocket Connect Route
resource "aws_apigatewayv2_integration" "ws_connect" {
  api_id                    = aws_apigatewayv2_api.websocket.id
  integration_type          = "AWS_PROXY"
  integration_uri           = aws_lambda_function.websocket_connect.invoke_arn
  integration_method        = "POST"
  content_handling_strategy = "CONVERT_TO_TEXT"
}

resource "aws_apigatewayv2_route" "ws_connect" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$connect"
  target    = "integrations/${aws_apigatewayv2_integration.ws_connect.id}"
}

# WebSocket Disconnect Route
resource "aws_apigatewayv2_integration" "ws_disconnect" {
  api_id                    = aws_apigatewayv2_api.websocket.id
  integration_type          = "AWS_PROXY"
  integration_uri           = aws_lambda_function.websocket_disconnect.invoke_arn
  integration_method        = "POST"
  content_handling_strategy = "CONVERT_TO_TEXT"
}

resource "aws_apigatewayv2_route" "ws_disconnect" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$disconnect"
  target    = "integrations/${aws_apigatewayv2_integration.ws_disconnect.id}"
}

# WebSocket Stage
resource "aws_apigatewayv2_stage" "websocket" {
  api_id      = aws_apigatewayv2_api.websocket.id
  name        = var.environment
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 500
    throttling_rate_limit  = 100
  }

  tags = var.tags
}

# Lambda permissions for WebSocket
resource "aws_lambda_permission" "ws_connect" {
  statement_id  = "AllowWebSocketConnect"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.websocket_connect.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket.execution_arn}/*/*"
}

resource "aws_lambda_permission" "ws_disconnect" {
  statement_id  = "AllowWebSocketDisconnect"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.websocket_disconnect.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket.execution_arn}/*/*"
}

# -------------------------
# CloudWatch Log Group
# -------------------------

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.project_name}-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}
