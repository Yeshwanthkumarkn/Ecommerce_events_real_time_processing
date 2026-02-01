# Real-Time E-commerce Event Processing Pipeline (GCP)

Faker App → Pub/Sub Topic → Push Subscription → Cloud Run (FastAPI) → BigQuery (RAW + PROCESSED)

## What’s in this repo

- `app/`: FastAPI service for Pub/Sub push → BigQuery writes
- `terraform/`: GCP infrastructure (Pub/Sub, Cloud Run, BigQuery, IAM, Artifact Registry)
- `.github/workflows/`: CI/CD pipeline (build & push image + Terraform plan/apply)

## Deploy on GCP

Infrastructure is defined in [terraform/README.md](terraform/README.md).

## CI/CD (GitHub Actions)

Workflow: [.github/workflows/gcp-ci-cd.yml](.github/workflows/gcp-ci-cd.yml)

Required GitHub Secrets:

- `GCP_PROJECT_ID`
- `REGION` (example: `us-central1`)
- `GCP_SA_KEY` (service account JSON key with permissions for Artifact Registry + Cloud Run + Pub/Sub + BigQuery + IAM)

## Local run (smoke test)

1) Install deps:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r app/requirements.txt
```

2) Set env vars (example):

- `BQ_DATASET` (default: `ecommerce_streaming`)
- `BQ_RAW_TABLE` (default: `ecommerce_raw_events`)
- `BQ_PROCESSED_TABLE` (default: `ecommerce_processed_events`)

3) Run API:

```bash
uvicorn app.main:app --reload --port 8080
```

4) Send a sample Pub/Sub push message (you can use any base64 payload):

The processor expects an `event_id` field (UUID string).

```bash
curl -X POST http://127.0.0.1:8080/pubsub/push \
	-H "Content-Type: application/json" \
	-d '{
		"message": {
			"messageId": "test-1",
			"publishTime": "2026-01-31T10:15:00Z",
			"data": "eyJ1c2VyX2lkIjoiVTEyMyIsImV2ZW50X3R5cGUiOiJwdXJjaGFzZSIsInByb2R1Y3RfaWQiOiJQNDU2IiwiY2F0ZWdvcnkiOiJlbGVjdHJvbmljcyIsInByaWNlIjoxOTk5Ljk5LCJkZXZpY2UiOiJtb2JpbGUiLCJjaXR5IjoiSHlkZXJhYmFkIiwiZXZlbnRfdGltZSI6IjIwMjYtMDEtMzFUMTA6MTU6MDBaIn0="
		}
	}'
```

Note: BigQuery writes require GCP credentials (ADC) and existing dataset/tables (Terraform creates them).

## Data quality behavior

- Events are always written to RAW (with Pub/Sub attributes).
- If schema validation fails, the event is marked `is_valid=false` and `validation_errors` is populated; the service still returns 2xx to Pub/Sub to avoid infinite retries on bad data.
- Only valid events are written to PROCESSED.

## Faker publisher

This repo includes a simple publisher that generates realistic-ish ecommerce events.

```bash
pip install -r publisher/requirements.txt
python publisher/main.py --project YOUR_PROJECT_ID --topic ecommerce_events --rate 5 --count 100
```

Architecture diagrams: [docs/architecture.md](docs/architecture.md)
