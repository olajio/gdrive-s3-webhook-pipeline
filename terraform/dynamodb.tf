# DynamoDB table for webhook channel management
resource "aws_dynamodb_table" "gdrive_channels" {
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

  attribute {
    name = "status"
    type = "S"
  }

  # Global secondary index for querying by folder
  global_secondary_index {
    name            = "folder_id-index"
    hash_key        = "folder_id"
    projection_type = "ALL"
  }

  # Global secondary index for querying active channels
  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
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

  # Enable TTL for automatic cleanup of old channels
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

# DynamoDB table for sync audit log
resource "aws_dynamodb_table" "gdrive_s3_sync_log" {
  name         = "${var.project_name}-sync-log-${var.environment}"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "file_id"
  range_key    = "timestamp"

  attribute {
    name = "file_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  # Global secondary index for querying by status
  global_secondary_index {
    name            = "status-timestamp-index"
    hash_key        = "status"
    range_key       = "timestamp"
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

  # Enable TTL for automatic cleanup (90 days)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-sync-log-${var.environment}"
    }
  )
}
