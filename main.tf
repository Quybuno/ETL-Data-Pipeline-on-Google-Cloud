# =============================================================================
# CLOUD INFRASTRUCTURE AS CODE - REAL ESTATE ETL PIPELINE
# =============================================================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
  
  # Uncomment for production - Remote state storage
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "real-estate-pipeline"
  # }
}

# =============================================================================
# PROVIDER CONFIGURATION
# =============================================================================
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# =============================================================================
# VARIABLES
# =============================================================================
variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "your-project-id"  # Thay đổi theo project của bạn
}

variable "region" {
  description = "GCP Region - Recommended: asia-southeast1 (Singapore) for Vietnam"
  type        = string
  default     = "asia-southeast1"
}

variable "zone" {
  description = "GCP Zone - Recommended: asia-southeast1-a for Vietnam"
  type        = string
  default     = "asia-southeast1-a"
}

variable "environment" {
  description = "Environment (dev/staging/prod)"
  type        = string
  default     = "dev"
}

# =============================================================================
# ENABLE REQUIRED APIs
# =============================================================================
resource "google_project_service" "required_apis" {
  for_each = toset([
    "storage.googleapis.com",
    "bigquery.googleapis.com",
    "cloudfunctions.googleapis.com",
    "composer.googleapis.com",
    "run.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com"
  ])
  
  project = var.project_id
  service = each.value
  
  disable_on_destroy = false
}

# =============================================================================
# CLOUD STORAGE BUCKETS (DATA LAKE)
# =============================================================================
resource "google_storage_bucket" "raw_data" {
  name          = "${var.project_id}-hanoi-bds-raw-data-${var.environment}"
  location      = var.region
  force_destroy = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_storage_bucket" "clean_data" {
  name          = "${var.project_id}-hanoi-bds-clean-data-${var.environment}"
  location      = var.region
  force_destroy = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
  
  depends_on = [google_project_service.required_apis]
}

# =============================================================================
# BIGQUERY DATASET (DATA WAREHOUSE)
# =============================================================================
resource "google_bigquery_dataset" "real_estate" {
  dataset_id  = "hanoi_real_estate_${var.environment}"
  location    = var.region
  description = "Hanoi Real Estate Data Warehouse"
  
  access {
    role = "OWNER"
    type = "user"
    user_by_email = "your-email@gmail.com"  # Thay đổi email của bạn
  }
  
  depends_on = [google_project_service.required_apis]
}

# =============================================================================
# BIGQUERY TABLE
# =============================================================================
resource "google_bigquery_table" "properties" {
  dataset_id = google_bigquery_dataset.real_estate.dataset_id
  table_id   = "properties"
  
  description = "Hanoi real estate properties data"
  
  schema = jsonencode([
    {
      name = "ma_bds"
      type = "STRING"
      mode = "REQUIRED"
      description = "Property ID"
    },
    {
      name = "dien_tich_su_dung_m2"
      type = "FLOAT"
      mode = "REQUIRED"
      description = "Usable area in square meters"
    },
    {
      name = "gia_ty"
      type = "FLOAT"
      mode = "REQUIRED"
      description = "Price in billion VND"
    },
    {
      name = "gia_per_m2"
      type = "FLOAT"
      mode = "REQUIRED"
      description = "Price per square meter in million VND"
    },
    {
      name = "price_segment"
      type = "STRING"
      mode = "REQUIRED"
      description = "Price segment (Budget/Mid-range/Premium/Luxury)"
    },
    {
      name = "phap_ly"
      type = "STRING"
      mode = "REQUIRED"
      description = "Legal status"
    },
    {
      name = "ngay_dang"
      type = "DATE"
      mode = "REQUIRED"
      description = "Posting date"
    },
    {
      name = "phuong_xa"
      type = "STRING"
      mode = "REQUIRED"
      description = "Ward/Commune"
    },
    {
      name = "quan_huyen"
      type = "STRING"
      mode = "REQUIRED"
      description = "District"
    },
    {
      name = "thanh_pho"
      type = "STRING"
      mode = "REQUIRED"
      description = "City"
    },
    {
      name = "nha_tam"
      type = "INTEGER"
      mode = "NULLABLE"
      description = "Number of bathrooms"
    },
    {
      name = "phong_ngu"
      type = "INTEGER"
      mode = "REQUIRED"
      description = "Number of bedrooms"
    },
    {
      name = "dien_tich_dat_m2"
      type = "FLOAT"
      mode = "NULLABLE"
      description = "Land area in square meters"
    },
    {
      name = "property_type"
      type = "STRING"
      mode = "REQUIRED"
      description = "Property type (Studio/1-2BR/3BR/4BR+)"
    },
    {
      name = "created_at"
      type = "TIMESTAMP"
      mode = "REQUIRED"
      description = "Record creation timestamp"
    },
    {
      name = "batch_id"
      type = "STRING"
      mode = "REQUIRED"
      description = "Batch processing ID"
    },
    {
      name = "data_source"
      type = "STRING"
      mode = "REQUIRED"
      description = "Data source"
    },
    {
      name = "processing_version"
      type = "STRING"
      mode = "REQUIRED"
      description = "Processing version"
    }
  ])
  
  time_partitioning {
    type = "DAY"
    field = "ngay_dang"
  }
  
  clustering = ["quan_huyen", "price_segment"]
  
  depends_on = [google_bigquery_dataset.real_estate]
}

# =============================================================================
# CLOUD FUNCTION (ETL PROCESSING)
# =============================================================================
resource "google_storage_bucket" "functions" {
  name          = "${var.project_id}-functions-${var.environment}"
  location      = var.region
  force_destroy = true
  
  depends_on = [google_project_service.required_apis]
}

# Upload Cloud Function source code
resource "google_storage_bucket_object" "function_source" {
  name   = "etl_function.zip"
  bucket = google_storage_bucket.functions.name
  source = "cloud_function/etl_function.zip"
}

resource "google_cloudfunctions_function" "etl_function" {
  name        = "hanoi-bds-etl-${var.environment}"
  description = "ETL function for Hanoi real estate data"
  runtime     = "python39"
  
  available_memory_mb   = 512
  source_archive_bucket = google_storage_bucket.functions.name
  source_archive_object = google_storage_bucket_object.function_source.name
  entry_point           = "process_real_estate_data"
  
  event_trigger {
    event_type = "google.storage.object.finalize"
    resource   = google_storage_bucket.raw_data.name
  }
  
  environment_variables = {
    CLEAN_BUCKET = google_storage_bucket.clean_data.name
    BQ_DATASET   = google_bigquery_dataset.real_estate.dataset_id
    BQ_TABLE     = google_bigquery_table.properties.table_id
  }
  
  depends_on = [
    google_project_service.required_apis,
    google_storage_bucket_object.function_source
  ]
}

# =============================================================================
# OUTPUTS
# =============================================================================
output "raw_data_bucket" {
  description = "Raw data bucket name"
  value       = google_storage_bucket.raw_data.name
}

output "clean_data_bucket" {
  description = "Clean data bucket name"
  value       = google_storage_bucket.clean_data.name
}

output "bigquery_dataset" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.real_estate.dataset_id
}

output "bigquery_table" {
  description = "BigQuery table ID"
  value       = google_bigquery_table.properties.table_id
}

output "cloud_function" {
  description = "Cloud Function name"
  value       = google_cloudfunctions_function.etl_function.name
}