#!/bin/bash
# Script để import các resources đã tồn tại vào Terraform state
# Chạy nếu bucket/dataset đã tồn tại từ trước

# Import BigQuery dataset (nếu đã tạo trước)
terraform import google_bigquery_dataset.dataset projects/etl-gcp-200501/datasets/hanoi_real_estate

# Import Storage buckets (nếu đã tạo trước)
# terraform import google_storage_bucket.raw_bucket hanoi-bds-raw-data
# terraform import google_storage_bucket.clean_bucket hanoi-bds-clean-data

