resource "google_bigquery_dataset" "ds" {
  dataset_id = var.dataset_id
  location   = var.region
}

resource "google_bigquery_table" "raw" {
  dataset_id          = google_bigquery_dataset.ds.dataset_id
  table_id            = var.raw_table_id
  deletion_protection = false

  schema = jsonencode([
    { name = "message_id", type = "STRING", mode = "NULLABLE" },
    { name = "event_id", type = "STRING", mode = "NULLABLE" },
    { name = "publish_time", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "ingestion_time", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "raw_payload", type = "JSON", mode = "NULLABLE" },
    { name = "source", type = "STRING", mode = "NULLABLE" },
    { name = "attributes", type = "JSON", mode = "NULLABLE" },
    { name = "is_valid", type = "BOOLEAN", mode = "NULLABLE" },
    { name = "validation_errors", type = "JSON", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "processed" {
  dataset_id          = google_bigquery_dataset.ds.dataset_id
  table_id            = var.processed_table_id
  deletion_protection = false

  schema = jsonencode([
    { name = "event_id", type = "STRING", mode = "NULLABLE" },
    { name = "user_id", type = "STRING", mode = "NULLABLE" },
    { name = "event_type", type = "STRING", mode = "NULLABLE" },
    { name = "product_id", type = "STRING", mode = "NULLABLE" },
    { name = "category", type = "STRING", mode = "NULLABLE" },
    { name = "price", type = "FLOAT", mode = "NULLABLE" },
    { name = "device", type = "STRING", mode = "NULLABLE" },
    { name = "city", type = "STRING", mode = "NULLABLE" },
    { name = "event_time", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "ingestion_time", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "errors" {
  dataset_id          = google_bigquery_dataset.ds.dataset_id
  table_id            = var.error_table_id
  deletion_protection = false

  schema = jsonencode([
    { name = "message_id", type = "STRING", mode = "NULLABLE" },
    { name = "event_id", type = "STRING", mode = "NULLABLE" },
    { name = "publish_time", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "ingestion_time", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "stage", type = "STRING", mode = "NULLABLE" },
    { name = "error_message", type = "STRING", mode = "NULLABLE" },
    { name = "error_details", type = "JSON", mode = "NULLABLE" },
    { name = "raw_payload", type = "JSON", mode = "NULLABLE" },
    { name = "attributes", type = "JSON", mode = "NULLABLE" },
    { name = "source", type = "STRING", mode = "NULLABLE" },
  ])
}
