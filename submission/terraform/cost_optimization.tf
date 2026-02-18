# cost_optimization.tf — Cost Optimization Resources
#
# TASK: Review data/aws_cost_report.json and implement cost-saving measures.
#
# Requirements:
#   1. Analyze the cost report and identify the top savings opportunities
#   2. Implement Terraform resources that address the findings, such as:
#      - S3 lifecycle policies for tiered storage
#      - Spot/mixed instance configurations for node groups
#      - Right-sizing recommendations implemented as resource changes
#   3. Add a comment block at the top explaining your cost analysis:
#      - Current monthly cost and top cost drivers
#      - Proposed changes and estimated savings
#      - Any trade-offs or risks

# --- Your cost analysis ---
# TODO: Write your analysis here as comments

# --- S3 Lifecycle Policies ---
# TODO: Implement lifecycle rules for the video chunks bucket
#   Hint: 95% of access is within the first 30 days

# --- Spot/Mixed Instance Configuration ---
# TODO: Configure mixed instance policies for appropriate node groups
#   Hint: Not all workloads are suitable for spot instances

# --- Other Cost Optimizations ---
# TODO: Implement any other cost-saving measures you identified
