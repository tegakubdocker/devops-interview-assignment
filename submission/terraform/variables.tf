variable "management_cidr" {
  description = "CIDR allowed to SSH to bastion (management network)"
  type        = string
  default     = "10.50.1.0/24"
}

variable "eks_version" {
  description = "EKS Kubernetes version"
  type        = string
  default     = "1.29"
}

variable "eks_endpoint_public_access" {
  description = "Whether the EKS API endpoint is publicly accessible"
  type        = bool
  default     = false
}
variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "management_cidr" {
  description = "CIDR block for management access (SSH to bastion)"
  type        = string
}
variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "site_id" {
  description = "Site identifier"
  type        = string
}
# General node group sizing
variable "general_node_instance_types" {
  description = "Instance types for general node group"
  type        = list(string)
  default     = ["m6i.large"]
}

variable "general_node_capacity_type" {
  description = "ON_DEMAND or SPOT for general node group"
  type        = string
  default     = "ON_DEMAND"
}

variable "general_node_min" {
  type        = number
  default     = 2
  description = "Minimum size for general node group"
}

variable "general_node_max" {
  type        = number
  default     = 6
  description = "Maximum size for general node group"
}

variable "general_node_desired" {
  type        = number
  default     = 3
  description = "Desired size for general node group"
}

# GPU node group sizing
variable "gpu_node_instance_types" {
  description = "Instance types for GPU node group"
  type        = list(string)
  default     = ["g4dn.xlarge"]
}

variable "gpu_node_capacity_type" {
  description = "ON_DEMAND or SPOT for GPU node group"
  type        = string
  default     = "ON_DEMAND"
}

variable "gpu_node_min" {
  type        = number
  default     = 0
  description = "Minimum size for GPU node group"
}

variable "gpu_node_max" {
  type        = number
  default     = 4
  description = "Maximum size for GPU node group"
}

variable "gpu_node_desired" {
  type        = number
  default     = 0
  description = "Desired size for GPU node group"
}