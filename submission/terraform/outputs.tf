output "vpc_id" {
  description = "ID of the VPC"
  value       = "" # TODO: Reference the VPC resource
}

output "eks_cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = "" # TODO: Reference the EKS cluster resource
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = var.cluster_name
}

# TODO: Add outputs for:
# - Private subnet IDs
# - Public subnet IDs
# - NAT Gateway IPs
# - S3 bucket names
# - Any other values downstream consumers need
