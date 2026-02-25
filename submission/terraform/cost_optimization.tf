

resource "aws_s3_bucket" "video_chunks" {
  bucket = "${var.cluster_name}-${var.environment}-video-chunks-${var.site_id}"
}

resource "aws_s3_bucket_versioning" "video_chunks" {
  bucket = aws_s3_bucket.video_chunks.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "video_chunks" {
  bucket = aws_s3_bucket.video_chunks.id

  rule {
    id     = "tier-video-objects"
    status = "Enabled"

    filter {}

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = 365
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}