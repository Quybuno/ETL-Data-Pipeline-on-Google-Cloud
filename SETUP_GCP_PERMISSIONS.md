# Hướng dẫn Cấp Quyền trên GCP

## 1. Kiểm tra Quyền Hiện Tại

### Kiểm tra User Account của bạn:
```powershell
# Xem account đang đăng nhập
gcloud auth list

# Kiểm tra project hiện tại
gcloud config get-value project
```

### Kiểm tra quyền IAM của bạn:
```powershell
# Kiểm tra roles của user account
gcloud projects get-iam-policy etl-gcp-200501 --flatten="bindings[].members" --filter="bindings.members:user:$(gcloud config get-value account)"
```

## 2. Quyền Cần Thiết để Chạy Terraform

Để Terraform có thể tạo resources, user account của bạn cần các roles sau:

### Quyền Tối Thiểu (Recommended):
- **Editor** (`roles/editor`) - Có thể tạo và quản lý hầu hết resources
- Hoặc các roles cụ thể:
  - `roles/storage.admin` - Quản lý GCS buckets
  - `roles/bigquery.admin` - Quản lý BigQuery datasets và tables
  - `roles/run.admin` - Quản lý Cloud Run services
  - `roles/cloudfunctions.admin` - Quản lý Cloud Functions
  - `roles/composer.admin` - Quản lý Cloud Composer
  - `roles/artifactregistry.admin` - Quản lý Artifact Registry
  - `roles/iam.serviceAccountAdmin` - Tạo và quản lý service accounts
  - `roles/logging.logWriter` - Ghi logs
  - `roles/monitoring.metricWriter` - Ghi metrics

### Cấp Quyền Editor (Cách đơn giản nhất):

**Nếu bạn là Owner của project:**
- Bạn đã có đủ quyền, không cần làm gì thêm

**Nếu bạn không phải Owner, cần người Owner cấp quyền:**

1. **Người Owner vào IAM & Admin:**
   - Truy cập: https://console.cloud.google.com/iam-admin/iam?project=etl-gcp-200501

2. **Click "Grant Access" hoặc "ADD"**

3. **Thêm email của bạn:**
   - New principals: `your-email@gmail.com` (hoặc email bạn dùng để login GCP)

4. **Chọn role:**
   - Role: `Editor` (roles/editor)
   - Hoặc chọn `Owner` nếu bạn là admin project

5. **Click "Save"**

**Hoặc dùng gcloud CLI (nếu có quyền Owner/Admin):**
```powershell
# Cấp quyền Editor cho user
gcloud projects add-iam-policy-binding etl-gcp-200501 \
    --member="user:your-email@gmail.com" \
    --role="roles/editor"
```

## 3. Enable Required APIs

Đảm bảo các APIs sau đã được enable:

**PowerShell (viết trên một dòng):**
```powershell
gcloud services enable artifactregistry.googleapis.com run.googleapis.com cloudfunctions.googleapis.com eventarc.googleapis.com storage.googleapis.com bigquery.googleapis.com composer.googleapis.com logging.googleapis.com monitoring.googleapis.com pubsub.googleapis.com compute.googleapis.com iam.googleapis.com --project=etl-gcp-200501
```

**Hoặc enable từng API một (dễ đọc hơn, khuyến nghị):**
```powershell
gcloud services enable artifactregistry.googleapis.com --project=etl-gcp-200501
gcloud services enable run.googleapis.com --project=etl-gcp-200501
gcloud services enable cloudfunctions.googleapis.com --project=etl-gcp-200501
gcloud services enable eventarc.googleapis.com --project=etl-gcp-200501
gcloud services enable storage.googleapis.com --project=etl-gcp-200501
gcloud services enable bigquery.googleapis.com --project=etl-gcp-200501
gcloud services enable composer.googleapis.com --project=etl-gcp-200501
gcloud services enable logging.googleapis.com --project=etl-gcp-200501
gcloud services enable monitoring.googleapis.com --project=etl-gcp-200501
gcloud services enable pubsub.googleapis.com --project=etl-gcp-200501
gcloud services enable compute.googleapis.com --project=etl-gcp-200501
gcloud services enable iam.googleapis.com --project=etl-gcp-200501
```

**Hoặc enable qua GCP Console (không cần quyền admin CLI, khuyến nghị):**
1. Truy cập: https://console.cloud.google.com/apis/library?project=etl-gcp-200501
2. Search và enable từng API sau:
   - **Artifact Registry API**
   - **Cloud Run API**
   - **Cloud Functions API**
   - **Eventarc API**
   - **Cloud Storage API**
   - **BigQuery API**
   - **Cloud Composer API**
   - **Cloud Logging API**
   - **Cloud Monitoring API**
   - **Cloud Pub/Sub API**
   - **Compute Engine API**
   - **Identity and Access Management (IAM) API**

## 4. Kiểm tra Quyền đã Đủ Chưa

Sau khi được cấp quyền, test bằng cách:
```powershell
# Thử tạo bucket test (sẽ xóa ngay)
gsutil mb -p etl-gcp-200501 -l asia-southeast1 gs://test-permission-check-$(Get-Random)
gsutil rm -r gs://test-permission-check-*

# Nếu thành công → có đủ quyền
# Nếu lỗi permission denied → cần cấp thêm quyền
```

## 5. Service Account Permissions

Terraform sẽ tự động tạo service accounts và cấp quyền cho chúng. Bạn chỉ cần có quyền:
- `roles/iam.serviceAccountAdmin` - Để tạo service accounts
- `roles/iam.serviceAccountUser` - Để sử dụng service accounts

Các service accounts sẽ tự động được cấp quyền phù hợp (xem trong `terraform/main.tf`).

## Troubleshooting

### Lỗi "Permission denied" khi chạy Terraform:
1. Kiểm tra user account đang dùng: `gcloud auth list`
2. Kiểm tra project đúng chưa: `gcloud config get-value project`
3. Kiểm tra IAM roles: Truy cập https://console.cloud.google.com/iam-admin/iam?project=etl-gcp-200501
4. Đảm bảo APIs đã được enable (xem bước 3)

### Lỗi "API not enabled":
Chạy lệnh enable APIs ở bước 3, hoặc enable trong Console:
- Truy cập: https://console.cloud.google.com/apis/library?project=etl-gcp-200501
- Search và enable từng API nếu cần

