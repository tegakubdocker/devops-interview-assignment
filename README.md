# Edge-to-Cloud Infrastructure Challenge

## DevOps / Infrastructure Engineer Assessment

You are joining a company that deploys AI-powered video analytics to customer sites. Edge devices at each site capture and process video feeds from IP cameras, then upload results to the AWS cloud for further analysis, storage, and customer-facing dashboards.

Your job is to build, fix, and configure the infrastructure that makes this work — from Terraform and Kubernetes to edge device provisioning, networking, and CI/CD.

## Time Limit

**4 hours** — You do not need to complete every module. Focus on demonstrating depth and quality over breadth.

## Structure

The assessment consists of **5 modules** (100 points total):

| # | Module | Points | Directory |
|---|--------|--------|-----------|
| 1 | Infrastructure-as-Code (Terraform) | 25 | `submission/terraform/` |
| 2 | Kubernetes & Troubleshooting | 25 | `submission/k8s/` |
| 3 | Edge Device & Networking | 20 | `submission/network/` + `submission/edge/` |
| 4 | CI/CD & Automation | 15 | `submission/cicd/` |
| 5 | Debugging & Ops Insights | 15 | `submission/debug/` |

## Getting Started

1. **Clone this repo** and create a private copy (see Submission below)
2. Read `docs/GETTING_STARTED.md` for setup instructions
3. Read `docs/ARCHITECTURE.md` to understand the company's infrastructure
4. Work through modules in `submission/` — each file has instructions and TODOs
5. Reference data in `data/` as needed (read-only, do not modify)

## Evaluation

Your submission is graded automatically:

```bash
pip install -r requirements.txt
python -m evaluation.evaluate --submission ./submission
```

See `EVALUATION.md` for the full scoring rubric, weights, and thresholds.

## What We're Looking For

- **Practical, production-ready solutions** — not textbook answers
- **Security-first thinking** — least privilege, network segmentation, no open defaults
- **Operational awareness** — monitoring, alerting, rollback plans
- **Clear communication** — your markdown responses should be concise and actionable
- **Trade-off reasoning** — explain why you chose an approach, not just what you did

## Submission

1. Create a **private repository** on your GitHub account
2. Push your completed work to the private repo
3. Add the following GitHub users as collaborators: *(provided in email)*
4. Reply to the assessment email with your repo URL

**Do not fork this repo publicly.**

## Rules

- You may use any reference material, documentation, or AI tools
- Do not modify anything in `evaluation/` or `data/`
- All work should be in the `submission/` directory
- Commit frequently — we review git history

## Questions?

If anything is unclear, email the hiring team. We'd rather clarify than have you guess.
