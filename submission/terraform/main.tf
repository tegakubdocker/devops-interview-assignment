# main.tf — EKS Cluster and Node Groups
#
# TASK: Complete this file to create a production-grade EKS cluster.
# Requirements:
#   - EKS cluster with proper IAM roles
#   - At least two node groups: one for general workloads, one for GPU inference
#   - Proper subnet placement (private subnets for nodes)
#   - Reference security groups from networking.tf

# --- EKS Cluster IAM Role ---
# TODO: Create an IAM role for the EKS cluster with the AmazonEKSClusterPolicy

# --- EKS Cluster ---
# TODO: Create the EKS cluster resource
#   - Place in private subnets
#   - Enable cluster logging (api, audit, authenticator)
#   - Reference the cluster IAM role

# --- Node Group IAM Role ---
# TODO: Create an IAM role for EKS node groups with:
#   - AmazonEKSWorkerNodePolicy
#   - AmazonEKS_CNI_Policy
#   - AmazonEC2ContainerRegistryReadOnly

# --- General Node Group ---
# TODO: Create a managed node group for general workloads
#   - Instance type(s) appropriate for general workloads
#   - Scaling configuration (min, max, desired)
#   - Place in private subnets

# --- GPU Node Group ---
# TODO: Create a managed node group for GPU inference
#   - GPU instance type (e.g., g4dn.xlarge)
#   - Appropriate scaling
#   - Taints for GPU workload isolation
#   - Place in private subnets
