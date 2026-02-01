output "cloud_run_url" {
  value = google_cloud_run_service.svc.status[0].url
}

output "pubsub_topic" {
  value = google_pubsub_topic.events.name
}

output "pubsub_subscription" {
  value = google_pubsub_subscription.push.name
}

output "bigquery_dataset" {
  value = google_bigquery_dataset.ds.dataset_id
}

output "bigquery_error_table" {
  value = google_bigquery_table.errors.table_id
}
