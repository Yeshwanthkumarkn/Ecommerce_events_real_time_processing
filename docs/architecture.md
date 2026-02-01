# Real-time Ecommerce Streaming Pipeline (GCP)

## Architecture (Mermaid)

```mermaid
flowchart LR
  A[Publisher\n`publisher/` (Python + Faker)] -->|JSON events| B[Pub/Sub Topic\n`ecommerce_events`]
  B --> C[Push Subscription\nOIDC auth + retry + DLQ]
  C -->|POST /pubsub/push| D[Cloud Run\nFastAPI Processor]

  D --> E[(BigQuery RAW\n`ecommerce_raw_events`)]
  D --> F[(BigQuery PROCESSED\n`ecommerce_processed_events`)]
  D --> G[(BigQuery ERROR\n`ecommerce_error_events`)]

  C -. after max attempts .-> H[DLQ Topic\n`ecommerce_events_dlq`]
  H --> I[DLQ Subscription\n`ecommerce_events_dlq_sub`]
```

## Data flow (high level)

```mermaid
sequenceDiagram
  autonumber
  participant P as Faker Publisher
  participant T as Pub/Sub Topic
  participant S as Push Subscription
  participant R as Cloud Run (FastAPI)
  participant BQ as BigQuery

  P->>T: Publish JSON (includes event_id)
  T->>S: Deliver message
  S->>R: HTTP POST /pubsub/push (OIDC)
  R->>BQ: Insert RAW (always)
  alt schema valid
    R->>BQ: Insert PROCESSED
    R-->>S: 2xx
  else schema invalid
    R->>BQ: Insert ERROR (stage=validation)
    R-->>S: 2xx (ack, no retry)
  else transient failure
    R-->>S: 5xx (retry)
  end
  Note over S: After max delivery attempts → DLQ
```

## Tables

- RAW: stores original JSON + Pub/Sub metadata + validation outcome
- PROCESSED: clean typed schema for analytics
- ERROR: operational table for validation failures and processed insert failures
