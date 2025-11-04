terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "5.30.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "5.30.0"
    }
  }
}

provider "google" {
  project = "etl-gcp-200501"
  region  = "asia-southeast1"
}

provider "google-beta" {
  project = "etl-gcp-200501"
  region  = "asia-southeast1"
}

# Giai đoạn 1: Tạo Bucket [cite: 10]
resource "google_storage_bucket" "raw_bucket" {
  name          = var.raw_bucket_name
  location      = var.location
  force_destroy = true
}

resource "google_storage_bucket" "clean_bucket" {
  name          = var.clean_bucket_name
  location      = var.location
  force_destroy = true
}

# Giai đoạn 1: Tạo BigQuery Dataset [cite: 11]
resource "google_bigquery_dataset" "dataset" {
  dataset_id = var.bigquery_dataset_id
  location   = var.location
}

# Giai đoạn 1: Tạo kho chứa container cho Cloud Run
resource "google_artifact_registry_repository" "repo" {
  provider      = google
  location      = var.region
  repository_id = var.artifact_repo_id
  format        = "DOCKER"
}

# Giai đoạn 1: Tạo Cloud Composer Environment [cite: 13]
# LƯU Ý: Việc này sẽ tốn chi phí và mất 20-30 phút để tạo.
# LƯU Ý 2: Composer 2 yêu cầu node_config và service account
resource "google_service_account" "composer_sa" {
  account_id   = "composer-worker-sa"
  display_name = "Composer Worker Service Account"
}

resource "google_project_iam_member" "composer_worker" {
  project = "etl-gcp-200501"
  role    = "roles/composer.worker"
  member  = "serviceAccount:${google_service_account.composer_sa.email}"
}

resource "google_composer_environment" "composer_env" {
  name   = var.composer_env_name
  region = var.region

  config {
    software_config {
      image_version = var.composer_image_version
    }
    # Composer 2 yêu cầu node_config với service account
    node_config {
      service_account = google_service_account.composer_sa.email
      zone            = "${var.region}-a"
      machine_type    = "n1-standard-1"
    }
  }
  depends_on = [google_project_iam_member.composer_worker]
}

# Giai đoạn 2: Cloud Run service để chạy crawler (serverless container)
resource "google_cloud_run_v2_service" "crawler" {
  name     = var.cloud_run_service_name
  location = var.region

  template {
    containers {
      image = var.crawler_image
      dynamic "env" {
        for_each = var.crawler_env
        content {
          name  = env.key
          value = env.value
        }
      }
    }
    service_account = var.run_service_account != null ? var.run_service_account : null
  }
}

resource "google_cloud_run_service_iam_member" "crawler_invoker_all" {
  location = google_cloud_run_v2_service.crawler.location
  project  = "etl-gcp-200501"
  service  = google_cloud_run_v2_service.crawler.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Giai đoạn 3: Cloud Function Gen2 xử lý khi có file mới trong bucket (Event-driven)
resource "google_service_account" "cf_sa" {
  account_id   = "cf-handler-sa"
  display_name = "Cloud Functions Handler Service Account"
}

resource "google_cloudfunctions2_function" "gcs_handler" {
  name     = var.cf_name
  location = var.region
  build_config {
    runtime     = var.cf_runtime
    entry_point = var.cf_entry_point
    source {
      storage_source {
        bucket = var.cf_source_bucket
        object = var.cf_source_object
      }
    }
  }
  service_config {
    max_instance_count    = 3
    available_memory      = "512M"
    service_account_email = google_service_account.cf_sa.email
    environment_variables = var.cf_env
  }
  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.storage.object.v1.finalized"
    event_filters {
      attribute = "bucket"
      value     = google_storage_bucket.raw_bucket.name
    }
    retry_policy = "RETRY_POLICY_RETRY"
  }
}

resource "google_project_iam_member" "cf_logs_writer" {
  project = "etl-gcp-200501"
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cf_sa.email}"
}

resource "google_project_iam_member" "cf_storage_access" {
  project = "etl-gcp-200501"
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.cf_sa.email}"
}

resource "google_project_iam_member" "cf_bigquery_user" {
  project = "etl-gcp-200501"
  role    = "roles/bigquery.user"
  member  = "serviceAccount:${google_service_account.cf_sa.email}"
}

output "raw_bucket_name" {
  value = google_storage_bucket.raw_bucket.name
}

output "clean_bucket_name" {
  value = google_storage_bucket.clean_bucket.name
}

output "bigquery_dataset_id" {
  value = google_bigquery_dataset.dataset.dataset_id
}

output "cloud_run_url" {
  value = google_cloud_run_v2_service.crawler.uri
}