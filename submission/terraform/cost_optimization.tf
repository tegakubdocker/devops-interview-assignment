# cost_optimization.tf — Cost Optimization Resources
#
# --- Your cost analysis ---
# NOTE: data/aws_cost_report.json not provided here, so below is a template.
# Current monthly cost: <fill from report>
# Top cost drivers: typically S3 storage/requests + EKS/EC2 compute + MSK brokers
#
# Proposed changes:
# 1) S3 lifecycle for video objects:
#    - Keep hot data in STANDARD for 0-30 days (95% access in first 30 days)
#    - Transition to STANDARD_IA after 30 days
#    - Transition to GLACIER_IR after 90 days
#    - Expire after 365 days (adjust per retention needs)
#    Estimated savings: significant reduction in storage cost for older video.
#    Trade-off: retrieval costs and higher access latency for cold tiers.
#
# 2) Spot for non-critical general workloads (optional via variables):
#    - Use capacity_type=SPOT for general node group where safe.
#    Trade-off: interruptions; ensure workloads are stateless and have PDB/HPA.
#
# 3) Keep GPU nodes scale-to-zero by default:
#    - gpu_node_min=0, desired=0 (already in variables defaults)
#    Trade-off: cold-start delay when scaling up.

# --- S3 Lifecycle Policies ---
# Implement lifecycle rules for the video chunks bucket.
# Assumption: bucket is managed elsewhere OR you will add it later.
# If your repo expects bucket resources here, create them and attach lifecycle.

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