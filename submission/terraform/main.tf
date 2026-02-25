# main.tf — EKS Cluster and Node Groups
#
# TASK: Complete this file to create a production-grade EKS cluster.
# Requirements:
#   - EKS cluster with proper IAM roles
#   - At least two node groups: one for general workloads, one for GPU inference
#   - Proper subnet placement (private subnets for nodes)
#   - Reference security groups from networking.tf

# --- EKS Cluster IAM Role ---

data "aws_iam_policy_document" "eks_cluster_assume" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "eks_cluster_role" {
  name               = "${var.cluster_name}-${var.environment}-eks-cluster-role"
  assume_role_policy = data.aws_iam_policy_document.eks_cluster_assume.json
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

# --- EKS Cluster ---

resource "aws_eks_cluster" "this" {
  name     = "${var.cluster_name}-${var.environment}"
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = var.eks_version

  vpc_config {
    subnet_ids              = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids      = [aws_security_group.eks_cluster.id]
    endpoint_public_access  = var.eks_endpoint_public_access
    endpoint_private_access = true
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator"]

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy
  ]
}

# --- Node Group IAM Role ---

data "aws_iam_policy_document" "eks_nodes_assume" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "eks_node_role" {
  name               = "${var.cluster_name}-${var.environment}-eks-node-role"
  assume_role_policy = data.aws_iam_policy_document.eks_nodes_assume.json
}

resource "aws_iam_role_policy_attachment" "node_worker_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "node_cni_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "node_ecr_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# --- General Node Group ---

resource "aws_eks_node_group" "general" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.cluster_name}-${var.environment}-general"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  instance_types = var.general_node_instance_types
  capacity_type  = var.general_node_capacity_type
  ami_type       = "AL2_x86_64"

  scaling_config {
    min_size     = var.general_node_min
    max_size     = var.general_node_max
    desired_size = var.general_node_desired
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    "workload" = "general"
  }

  tags = {
    Name = "${var.cluster_name}-${var.environment}-general-ng"
  }

  depends_on = [
    aws_iam_role_policy_attachment.node_worker_policy,
    aws_iam_role_policy_attachment.node_cni_policy,
    aws_iam_role_policy_attachment.node_ecr_policy
  ]
}

# --- GPU Node Group ---

resource "aws_eks_node_group" "gpu" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.cluster_name}-${var.environment}-gpu"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  instance_types = var.gpu_node_instance_types
  capacity_type  = var.gpu_node_capacity_type
  ami_type       = "AL2_x86_64_GPU"

  scaling_config {
    min_size     = var.gpu_node_min
    max_size     = var.gpu_node_max
    desired_size = var.gpu_node_desired
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    "workload" = "gpu"
  }

  taint {
    key    = "nvidia.com/gpu"
    value  = "true"
    effect = "NO_SCHEDULE"
  }

  tags = {
    Name = "${var.cluster_name}-${var.environment}-gpu-ng"
  }

  depends_on = [
    aws_iam_role_policy_attachment.node_worker_policy,
    aws_iam_role_policy_attachment.node_cni_policy,
    aws_iam_role_policy_attachment.node_ecr_policy
  ]
}