output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "eks_cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = aws_eks_cluster.this.endpoint
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.this.name
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = [aws_subnet.public_a.id, aws_subnet.public_b.id]
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

output "nat_gateway_public_ip" {
  description = "NAT Gateway public IP"
  value       = aws_eip.nat.public_ip
}

output "bastion_security_group_id" {
  description = "Bastion security group ID"
  value       = aws_security_group.bastion.id
}

output "eks_nodes_security_group_id" {
  description = "EKS nodes security group ID"
  value       = aws_security_group.eks_nodes.id
}

output "eks_cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = aws_security_group.eks_cluster.id
}