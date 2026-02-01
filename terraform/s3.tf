# ==================================================
# Customer Care Call Processing System - S3 Storage
# ==================================================

# Primary S3 bucket for call recordings, transcripts, and summaries
resource "aws_s3_bucket" "call_storage" {
  bucket = var.s3_bucket_name

  tags = merge(
    var.tags,
    {
      Name = var.s3_bucket_name
    }
  )
}

# Block public access
resource "aws_s3_bucket_public_access_block" "call_storage" {
  bucket = aws_s3_bucket.call_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning for production
resource "aws_s3_bucket_versioning" "call_storage" {
  bucket = aws_s3_bucket.call_storage.id

  versioning_configuration {
    status = var.environment == "prod" ? "Enabled" : "Suspended"
  }
}

# Enable server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "call_storage" {
  bucket = aws_s3_bucket.call_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# CORS configuration for frontend access
resource "aws_s3_bucket_cors_configuration" "call_storage" {
  bucket = aws_s3_bucket.call_storage.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = var.environment == "prod" ? ["https://your-production-domain.com"] : ["http://localhost:3000", "http://localhost:5173"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

# Lifecycle policy for storage optimization
resource "aws_s3_bucket_lifecycle_configuration" "call_storage" {
  bucket = aws_s3_bucket.call_storage.id

  # Raw audio files - archive after 90 days
  rule {
    id     = "archive-raw-audio"
    status = "Enabled"

    filter {
      prefix = "raw-audio/"
    }

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = 2555 # 7 years (compliance)
    }
  }

  # Transcripts - keep longer in standard storage
  rule {
    id     = "archive-transcripts"
    status = "Enabled"

    filter {
      prefix = "transcripts/"
    }

    transition {
      days          = 180
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = 2555 # 7 years
    }
  }

  # Cleanup incomplete uploads
  rule {
    id     = "cleanup-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Enable access logging for production
resource "aws_s3_bucket_logging" "call_storage" {
  count = var.environment == "prod" ? 1 : 0

  bucket = aws_s3_bucket.call_storage.id

  target_bucket = aws_s3_bucket.logs[0].id
  target_prefix = "s3-access-logs/"
}

# S3 bucket for logs (only in production)
resource "aws_s3_bucket" "logs" {
  count  = var.environment == "prod" ? 1 : 0
  bucket = "${var.s3_bucket_name}-logs"

  tags = merge(
    var.tags,
    {
      Name = "${var.s3_bucket_name}-logs"
    }
  )
}

resource "aws_s3_bucket_public_access_block" "logs" {
  count  = var.environment == "prod" ? 1 : 0
  bucket = aws_s3_bucket.logs[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  count  = var.environment == "prod" ? 1 : 0
  bucket = aws_s3_bucket.logs[0].id

  rule {
    id     = "expire-old-logs"
    status = "Enabled"

    expiration {
      days = 90
    }
  }
}
