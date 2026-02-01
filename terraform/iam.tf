resource "google_service_account" "cloud_run_sa" {
  account_id   = "ecommerce-processor-sa"
  display_name = "Ecommerce Processor Cloud Run SA"
}

resource "google_service_account" "pubsub_push_sa" {
  account_id   = "ecommerce-pubsub-push-sa"
  display_name = "Pub/Sub Push Invoker SA"
}

resource "google_bigquery_dataset_iam_member" "cloud_run_bq_editor" {
  dataset_id = google_bigquery_dataset.ds.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "cloud_run_bq_user" {
  project = var.project_id
  role    = "roles/bigquery.user"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "cloud_run_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Allow Pub/Sub service agent to mint OIDC tokens for pubsub_push_sa.
resource "google_service_account_iam_member" "pubsub_token_creator" {
  service_account_id = google_service_account.pubsub_push_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
