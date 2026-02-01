resource "google_pubsub_topic" "events" {
  name = var.topic_name
}

resource "google_pubsub_topic" "events_dlq" {
  name = "${var.topic_name}_dlq"
}

resource "google_pubsub_subscription" "dlq_pull" {
  name  = "${var.topic_name}_dlq_sub"
  topic = google_pubsub_topic.events_dlq.name

  ack_deadline_seconds = 60
}

resource "google_pubsub_subscription" "push" {
  name  = var.subscription_name
  topic = google_pubsub_topic.events.name

  ack_deadline_seconds = 60

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.events_dlq.id
    max_delivery_attempts = 5
  }

  push_config {
    push_endpoint = "${google_cloud_run_service.svc.status[0].url}/pubsub/push"

    oidc_token {
      service_account_email = google_service_account.pubsub_push_sa.email
      audience              = google_cloud_run_service.svc.status[0].url
    }
  }
}
