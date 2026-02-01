param(
  [Parameter(Mandatory=$true)][string]$ProjectId,
  [string]$Region = "us-central1",
  [string]$ArtifactRepoId = "ecommerce-pipeline",
  [string]$ServiceName = "ecommerce-processor",
  [string]$DatasetId = "ecommerce_streaming",
  [string]$RawTableId = "ecommerce_raw_events",
  [string]$ProcessedTableId = "ecommerce_processed_events",
  [string]$ErrorTableId = "ecommerce_error_events",
  [string]$TopicName = "ecommerce_events",
  [string]$SubscriptionName = "ecommerce_events_push_sub",
  [string]$StateBucket = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($StateBucket)) {
  $StateBucket = "$ProjectId-tfstate-ecommerce"
}

Write-Host "Initializing Terraform backend (bucket=$StateBucket)" -ForegroundColor Cyan
terraform -chdir=terraform init -backend-config="bucket=$StateBucket" -backend-config="prefix=ecommerce-processor"

# NOTE: Import IDs follow the google provider import formats.
# If any import fails (because the resource truly doesn't exist), skip it.

$CloudRunSaEmail = "ecommerce-processor-sa@$ProjectId.iam.gserviceaccount.com"
$PubSubPushSaEmail = "ecommerce-pubsub-push-sa@$ProjectId.iam.gserviceaccount.com"

$imports = @(
  @{ Addr = "google_artifact_registry_repository.repo"; Id = "projects/$ProjectId/locations/$Region/repositories/$ArtifactRepoId" },
  @{ Addr = "google_bigquery_dataset.ds"; Id = "projects/$ProjectId/datasets/$DatasetId" },
  @{ Addr = "google_bigquery_table.raw"; Id = "projects/$ProjectId/datasets/$DatasetId/tables/$RawTableId" },
  @{ Addr = "google_bigquery_table.processed"; Id = "projects/$ProjectId/datasets/$DatasetId/tables/$ProcessedTableId" },
  @{ Addr = "google_bigquery_table.errors"; Id = "projects/$ProjectId/datasets/$DatasetId/tables/$ErrorTableId" },
  @{ Addr = "google_service_account.cloud_run_sa"; Id = "projects/$ProjectId/serviceAccounts/$CloudRunSaEmail" },
  @{ Addr = "google_service_account.pubsub_push_sa"; Id = "projects/$ProjectId/serviceAccounts/$PubSubPushSaEmail" },
  @{ Addr = "google_pubsub_topic.events"; Id = "projects/$ProjectId/topics/$TopicName" },
  @{ Addr = "google_pubsub_topic.events_dlq"; Id = "projects/$ProjectId/topics/${TopicName}_dlq" },
  @{ Addr = "google_pubsub_subscription.push"; Id = "projects/$ProjectId/subscriptions/$SubscriptionName" },
  @{ Addr = "google_pubsub_subscription.dlq_pull"; Id = "projects/$ProjectId/subscriptions/${TopicName}_dlq_sub" },
  @{ Addr = "google_cloud_run_service.svc"; Id = "locations/$Region/namespaces/$ProjectId/services/$ServiceName" }
)

foreach ($imp in $imports) {
  Write-Host "Importing $($imp.Addr)" -ForegroundColor Yellow
  try {
    terraform -chdir=terraform import $imp.Addr $imp.Id
  } catch {
    Write-Host "  Skipped (import failed): $($_.Exception.Message)" -ForegroundColor DarkYellow
  }
}

Write-Host "Done. Now run: terraform -chdir=terraform plan/apply" -ForegroundColor Green
