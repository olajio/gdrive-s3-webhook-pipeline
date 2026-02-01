# ==================================================
# Customer Care Call Processing System - DynamoDB Tables
# ==================================================

# -------------------------
# Call Summaries Table
# Primary table for storing call metadata, transcripts, and AI summaries
# -------------------------

resource "aws_dynamodb_table" "call_summaries" {
  name         = "${var.project_name}-summaries-${var.environment}"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "call_id"

  attribute {
    name = "call_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "assigned_user_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  # GSI for querying by status (for dashboard filters)
  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # GSI for querying by assigned user (for caseworker views)
  global_secondary_index {
    name            = "user-index"
    hash_key        = "assigned_user_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # Enable point-in-time recovery for production
  point_in_time_recovery {
    enabled = var.environment == "prod" ? true : false
  }

  # Enable server-side encryption
  server_side_encryption {
    enabled = true
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-summaries-${var.environment}"
    }
  )
}

# -------------------------
# WebSocket Connections Table
# Stores active WebSocket connections for real-time notifications
# -------------------------

resource "aws_dynamodb_table" "websocket_connections" {
  name         = "${var.project_name}-connections-${var.environment}"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "connection_id"

  attribute {
    name = "connection_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  # GSI for querying connections by user
  global_secondary_index {
    name            = "user-index"
    hash_key        = "user_id"
    projection_type = "ALL"
  }

  # Enable server-side encryption
  server_side_encryption {
    enabled = true
  }

  # Enable TTL for automatic cleanup of stale connections
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-connections-${var.environment}"
    }
  )
}

# -------------------------
# Webhook Channels Table
# Tracks Google Drive webhook channel registrations
# -------------------------

resource "aws_dynamodb_table" "webhook_channels" {
  name         = "${var.project_name}-channels-${var.environment}"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "channel_id"

  attribute {
    name = "channel_id"
    type = "S"
  }

  attribute {
    name = "folder_id"
    type = "S"
  }

  # GSI for querying by folder
  global_secondary_index {
    name            = "folder-index"
    hash_key        = "folder_id"
    projection_type = "ALL"
  }

  # Enable server-side encryption
  server_side_encryption {
    enabled = true
  }

  # Enable TTL for automatic cleanup of expired channels
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-channels-${var.environment}"
    }
  )
}
