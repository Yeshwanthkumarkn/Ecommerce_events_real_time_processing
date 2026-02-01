variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "ecommerce-processor"
}

variable "dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
  default     = "ecommerce_streaming"
}

variable "raw_table_id" {
  description = "BigQuery RAW table ID"
  type        = string
  default     = "ecommerce_raw_events"
}

variable "processed_table_id" {
  description = "BigQuery PROCESSED table ID"
  type        = string
  default     = "ecommerce_processed_events"
}

variable "error_table_id" {
  description = "BigQuery ERROR table ID"
  type        = string
  default     = "ecommerce_error_events"
}

variable "topic_name" {
  description = "Pub/Sub topic name"
  type        = string
  default     = "ecommerce_events"
}

variable "subscription_name" {
  description = "Pub/Sub push subscription name"
  type        = string
  default     = "ecommerce_events_push_sub"
}

variable "artifact_repo_id" {
  description = "Artifact Registry repository ID"
  type        = string
  default     = "ecommerce-pipeline"
}

variable "image" {
  description = "Container image URI for Cloud Run"
  type        = string
  default     = "us-central1-docker.pkg.dev/PROJECT_ID/ecommerce-pipeline/ecommerce-processor:latest"
}

variable "min_instances" {
  description = "Cloud Run min instances (0 = scale to zero)"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Cloud Run max instances"
  type        = number
  default     = 10
}
