project_id           = "etl-gcp-200501"
region               = "asia-southeast1"
location             = "asia-southeast1"

# Artifact Registry repo id is defined in variables with default "etl-repo"
# Buckets and dataset have defaults; override here if you want custom names
# raw_bucket_name     = "hanoi-bds-raw-data"
# clean_bucket_name   = "hanoi-bds-clean-data"
# bigquery_dataset_id = "hanoi_real_estate"

# Cloud Run crawler image (MUST set to an existing pushed image)
crawler_image        = "asia-southeast1-docker.pkg.dev/etl-gcp-200501/etl-repo/crawler:latest"

# Optional env for Cloud Run
crawler_env = {
}

# Optional service account for Cloud Run (email); leave empty to use default
run_service_account  = null

# Cloud Functions Gen2 source location (MUST upload a zip to this bucket/object)
cf_source_bucket     = "etl-gcp-200501-cf-src"
cf_source_object     = "cf-src.zip"

# Optional env for Cloud Function
cf_env = {
}

