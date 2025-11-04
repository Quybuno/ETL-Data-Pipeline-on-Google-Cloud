# Quick Fix cho Terraform Apply Errors

## Các lỗi gặp phải:

1. ✅ **Bucket đã tồn tại** - `hanoi-bds-raw-data` đã có sẵn
2. ✅ **Dataset đã tồn tại** - `hanoi_real_estate` đã có sẵn  
3. ✅ **Composer cần service account** - Đã sửa trong `main.tf`
4. ❌ **Image chưa push** - Cần push Docker image trước

## Giải pháp:

### Bước 1: Import resources đã tồn tại vào Terraform state

```powershell
cd D:\Nhadat\terraform

# Import BigQuery dataset (nếu đã tạo trước)
terraform import google_bigquery_dataset.dataset projects/etl-gcp-200501/datasets/hanoi_real_estate

# Import buckets (nếu cần - nếu bucket name bị conflict, có thể đổi tên trong terraform.tfvars)
# terraform import google_storage_bucket.raw_bucket hanoi-bds-raw-data
```

### Bước 2: Push Docker image TRƯỚC khi apply Cloud Run

Repository `etl-repo` đã được tạo thành công! Bây giờ push image:

```powershell
cd D:\Nhadat\cloud-run

# Build và push image
docker build -t "asia-southeast1-docker.pkg.dev/etl-gcp-200501/etl-repo/crawler:latest" .
docker push "asia-southeast1-docker.pkg.dev/etl-gcp-200501/etl-repo/crawler:latest"
```

### Bước 3: Nếu bucket name bị conflict, đổi tên trong terraform.tfvars

Mở `terraform.tfvars` và đổi tên bucket:

```hcl
raw_bucket_name   = "hanoi-bds-raw-data-unique-123"  # Thêm suffix unique
clean_bucket_name = "hanoi-bds-clean-data-unique-123"
```

### Bước 4: Sau khi push image xong, chạy lại terraform apply

```powershell
cd D:\Nhadat\terraform
terraform apply
```

### Bước 5: Tạm thời comment Cloud Run nếu chưa có image

Nếu muốn apply các resources khác trước (bỏ Cloud Run tạm thời), comment trong `main.tf`:

```hcl
# Tạm thời comment Cloud Run cho đến khi có image
# resource "google_cloud_run_v2_service" "crawler" {
#   ...
# }
```

Sau khi push image xong, uncomment và apply lại.

