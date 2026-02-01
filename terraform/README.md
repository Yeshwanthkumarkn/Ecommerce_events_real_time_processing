Terraform provisions:

- Pub/Sub topic + push subscription (OIDC auth)
- Cloud Run service (FastAPI)
- BigQuery dataset + RAW/PROCESSED tables
- Artifact Registry repo
- IAM for Cloud Run runtime + Pub/Sub push invoker

Usage:

```bash
terraform -chdir=terraform init
terraform -chdir=terraform plan \
  -var="project_id=YOUR_PROJECT_ID" \
  -var="region=us-central1" \
  -var="image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/ecommerce-pipeline/ecommerce-processor:latest"
terraform -chdir=terraform apply
```
