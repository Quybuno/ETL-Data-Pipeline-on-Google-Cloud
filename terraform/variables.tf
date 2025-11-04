variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region (e.g. asia-southeast1)"
}

variable "location" {
  type        = string
  description = "Multi-regional or regional location for data services (e.g. US, EU, asia-southeast1)"
}

variable "raw_bucket_name" {
  type        = string
  description = "Bucket lưu dữ liệu raw"
  default     = "hanoi-bds-raw-data"
}

variable "clean_bucket_name" {
  type        = string
  description = "Bucket lưu dữ liệu clean"
  default     = "hanoi-bds-clean-data"
}

variable "bigquery_dataset_id" {
  type        = string
  description = "Dataset BigQuery"
  default     = "hanoi_real_estate"
}

variable "artifact_repo_id" {
  type        = string
  description = "Artifact Registry repository id"
  default     = "etl-repo"
}

variable "composer_env_name" {
  type        = string
  description = "Tên Cloud Composer environment"
  default     = "etl-orchestrator"
}

variable "composer_image_version" {
  type        = string
  description = "Phiên bản Composer/Airflow"
  default     = "composer-2-airflow-2"
}

variable "cloud_run_service_name" {
  type        = string
  description = "Tên dịch vụ Cloud Run cho crawler"
  default     = "crawler-service"
}

variable "crawler_image" {
  type        = string
  description = "Container image cho crawler (e.g. REGION-docker.pkg.dev/PROJECT/REPO/image:tag)"
}

variable "crawler_env" {
  type        = map(string)
  description = "Biến môi trường cho Cloud Run crawler"
  default     = {}
}

variable "run_service_account" {
  type        = string
  description = "Service account email cho Cloud Run"
  default     = null
}

variable "cf_name" {
  type        = string
  description = "Tên Cloud Function Gen2 xử lý file mới"
  default     = "gcs-file-handler"
}

variable "cf_runtime" {
  type        = string
  description = "Runtime Cloud Function (e.g. python311)"
  default     = "python311"
}

variable "cf_entry_point" {
  type        = string
  description = "Entry point function name"
  default     = "main"
}

variable "cf_source_bucket" {
  type        = string
  description = "Bucket chứa source Cloud Function (zip)"
}

variable "cf_source_object" {
  type        = string
  description = "Object (zip) trong bucket chứa source Cloud Function"
}

variable "cf_env" {
  type        = map(string)
  description = "Biến môi trường cho Cloud Function"
  default     = {}
}


