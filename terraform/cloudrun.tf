resource "google_cloud_run_service" "svc" {
  name     = var.service_name
  location = var.region

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = tostring(var.min_instances)
        "autoscaling.knative.dev/maxScale" = tostring(var.max_instances)
      }
    }

    spec {
      service_account_name = google_service_account.cloud_run_sa.email

      containers {
        image = var.image

        env {
          name  = "BQ_DATASET"
          value = var.dataset_id
        }

        env {
          name  = "BQ_RAW_TABLE"
          value = var.raw_table_id
        }

        env {
          name  = "BQ_PROCESSED_TABLE"
          value = var.processed_table_id
        }

        env {
          name  = "BQ_ERROR_TABLE"
          value = var.error_table_id
        }

        env {
          name  = "EVENT_SOURCE"
          value = "pubsub"
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Only allow authenticated invocation (Pub/Sub push uses OIDC).
resource "google_cloud_run_service_iam_member" "pubsub_invoker" {
  service  = google_cloud_run_service.svc.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_push_sa.email}"
}
