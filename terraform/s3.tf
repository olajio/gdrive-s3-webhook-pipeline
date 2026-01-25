# S3 bucket for synced files
resource "aws_s3_bucket" "gdrive_sync" {
  bucket = var.s3_bucket_name

  tags = merge(
    var.tags,
    {
      Name = var.s3_bucket_name
    }
  )
}

# Block public access
resource "aws_s3_bucket_public_access_block" "gdrive_sync" {
  bucket = aws_s3_bucket.gdrive_sync.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning
resource "aws_s3_bucket_versioning" "gdrive_sync" {
  bucket = aws_s3_bucket.gdrive_sync.id

  versioning_configuration {
    status = var.environment == "prod" ? "Enabled" : "Suspended"
  }
}

# Enable server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "gdrive_sync" {
  bucket = aws_s3_bucket.gdrive_sync.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Lifecycle policy to transition old files to Glacier
resource "aws_s3_bucket_lifecycle_configuration" "gdrive_sync" {
  bucket = aws_s3_bucket.gdrive_sync.id

  rule {
    id     = "archive-old-files"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = 2555  # 7 years
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "GLACIER_IR"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  rule {
    id     = "cleanup-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Enable logging
resource "aws_s3_bucket_logging" "gdrive_sync" {
  count = var.environment == "prod" ? 1 : 0

  bucket = aws_s3_bucket.gdrive_sync.id

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
