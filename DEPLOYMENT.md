# Hướng dẫn Deployment sau khi Terraform Apply

Sau khi chạy `terraform apply` thành công, thực hiện các bước sau:

## 1. Build và Push Docker Image cho Cloud Run

**⚠️ Quan trọng: Cần Docker Desktop đang chạy trước khi build!**

Nếu chưa cài Docker Desktop:
1. Tải Docker Desktop cho Windows: https://www.docker.com/products/docker-desktop
2. Cài đặt và khởi động Docker Desktop
3. Đợi Docker engine khởi động xong (icon Docker ở system tray)

```powershell
# Navigate to cloud-run directory (từ root project D:\Nhadat)
cd D:\Nhadat\cloud-run
# Hoặc nếu đang ở terraform: cd ..\cloud-run

# Kiểm tra Docker đang chạy
docker ps
# Nếu lỗi "cannot connect to Docker daemon", cần khởi động Docker Desktop

# Cấu hình Docker authentication với Artifact Registry
$REGION = "asia-southeast1"
$PROJECT = "etl-gcp-200501"
$REPO = "etl-repo"
$IMAGE = "crawler"

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# Build image
docker build -t "${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${IMAGE}:latest" .

# Push image
docker push "${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${IMAGE}:latest"
```

**Lưu ý:** Cập nhật `terraform.tfvars` với image URL đúng:
```hcl
crawler_image = "asia-southeast1-docker.pkg.dev/etl-gcp-200501/etl-repo/crawler:latest"
```

## 2. Tạo BigQuery Table

**Khuyến nghị: Dùng Python script** (tự động tạo dataset nếu chưa có)

```powershell
cd D:\Nhadat\bigquery
pip install google-cloud-bigquery
python create_table.py
```

**Hoặc dùng BigQuery Console (web UI)** - Cần tạo dataset trước:

1. Mở BigQuery Console: https://console.cloud.google.com/bigquery?project=etl-gcp-200501
2. **Tạo dataset trước (quan trọng!):**
   - Click vào project `etl-gcp-200501` ở sidebar
   - Click "..." → "Create dataset"
   - Dataset ID: `hanoi_real_estate`
   - **Location type: Region** → Chọn **asia-southeast1** (phải match với Terraform!)
   - Click "Create dataset"
3. Sau đó tạo table:
   - Click vào dataset `hanoi_real_estate`
   - Click "Compose new query"
   - Copy toàn bộ nội dung từ file `D:\Nhadat\bigquery\schema.sql`
   - Paste vào editor và click "Run"

**Lưu ý:** Dataset location phải là **asia-southeast1** (match với `location` trong `terraform.tfvars`), không phải US!

**Hoặc dùng bq CLI (cần quyền admin nếu SDK cài trong Program Files):**

```powershell
# Option 1: Chạy PowerShell as Administrator
# Sau đó chạy:
cd D:\Nhadat\bigquery
Get-Content schema.sql | bq query --use_legacy_sql=false

# Option 2: Dùng full path và escape quotes nếu cần
cd D:\Nhadat\bigquery
bq query --use_legacy_sql=false --format=prettyjson "$(Get-Content schema.sql -Raw)"
```

**Hoặc dùng Python script (không cần quyền admin):**

```powershell
cd D:\Nhadat\bigquery

# Cài đặt BigQuery client nếu chưa có
pip install google-cloud-bigquery

# Chạy script Python
python create_table.py
```

## 3. Package và Upload Cloud Function Source

**Khuyến nghị: Dùng Python script** (không cần quyền admin)

```powershell
cd D:\Nhadat\cloud-function

# Cài đặt GCS client nếu chưa có
pip install google-cloud-storage

# Chạy script Python (tự động tạo zip và upload)
python upload_source.py
```

**Hoặc dùng gsutil CLI (cần quyền admin nếu SDK cài trong Program Files):**

```powershell
# Option 1: Chạy PowerShell as Administrator
# Sau đó chạy:
cd D:\Nhadat\cloud-function

# Tạo zip file chứa source code
Compress-Archive -Path *.py,requirements.txt -DestinationPath ..\cf-src.zip

# Tạo bucket cho source code (nếu chưa có)
gsutil mb -p etl-gcp-200501 -l asia-southeast1 gs://etl-gcp-200501-cf-src

# Upload zip
gsutil cp ..\cf-src.zip gs://etl-gcp-200501-cf-src/cf-src.zip
```

**Lưu ý:** Cập nhật `terraform.tfvars`:
```hcl
cf_source_bucket = "etl-gcp-200501-cf-src"
cf_source_object = "cf-src.zip"
```

Sau đó chạy lại `terraform apply` để tạo Cloud Function với source code.

## 4. Cấu hình Environment Variables cho Cloud Function

Trong `terraform.tfvars`, thêm:
```hcl
cf_env = {
  RAW_BUCKET    = "hanoi-bds-raw-data"
  CLEAN_BUCKET  = "hanoi-bds-clean-data"
  DATASET_ID    = "hanoi_real_estate"
  TABLE_ID      = "properties"
}
```

## 5. Deploy Airflow DAG vào Cloud Composer

Sau khi Composer environment sẵn sàng (mất ~20-30 phút), lấy DAGs folder path:
```powershell
# Lấy thông tin Composer environment
gcloud composer environments describe etl-orchestrator --location asia-southeast1

# Copy DAG file lên GCS bucket của Composer (từ root project)
gsutil cp D:\Nhadat\airflow\dags\etl_pipeline.py gs://<COMPOSER_BUCKET>/dags/etl_pipeline.py
```

## 6. Test Pipeline

### Test Cloud Run Crawler
```powershell
# Từ thư mục terraform
cd D:\Nhadat\terraform
# Lấy URL từ Terraform output
terraform output cloud_run_url

# Trigger crawler
curl -X POST "<CLOUD_RUN_URL>?raw_bucket=hanoi-bds-raw-data"
```

### Test Cloud Function
Upload một file test vào raw bucket:
```powershell
# Tạo file test
echo '{"url":"https://mogi.vn/test","price":"2 tỷ","address":"Hà Nội"}' | Out-File -Encoding utf8 test.jsonl

# Upload
gsutil cp test.jsonl gs://hanoi-bds-raw-data/source=mogi/dt=2024-01-15/test.jsonl
```

Cloud Function sẽ tự động trigger và xử lý file này.

## 7. Demo theo các "Cốt lõi"

### Cốt lõi 1: IaC (Infrastructure as Code)
- Show file `terraform/main.tf` - toàn bộ infrastructure định nghĩa bằng code
- Chạy `terraform plan` để xem planned changes
- Chạy `terraform destroy` rồi `terraform apply` để demonstrate reproducibility

### Cốt lõi 2: Elastic Compute & Serverless
- **Cloud Run**: Show logs, metrics trong Cloud Console - tự động scale based on traffic
- **Cloud Function**: Upload file test → xem logs → thấy function tự động trigger và scale

### Cốt lõi 3: Managed Services (PaaS)
- **BigQuery**: Chạy query mẫu trên dataset để show serverless data warehouse
- **Cloud Composer**: Mở Airflow UI, show DAG graph → giải thích orchestration

### Cốt lõi 4: Accessibility & Observability (SaaS)
- **Looker Studio**: Tạo dashboard kết nối BigQuery → share link cho end-user
- **Cloud Monitoring**: Show metrics, tạo alert mẫu cho error rate hoặc latency

## Troubleshooting

### Lỗi Cloud Run không deploy được
- Kiểm tra image đã push chưa: `gcloud artifacts docker images list asia-southeast1-docker.pkg.dev/etl-gcp-200501/etl-repo/crawler`
- Kiểm tra IAM permissions cho service account

### Lỗi Cloud Function không trigger
- Kiểm tra Eventarc trigger đã tạo: `gcloud eventarc triggers list`
- Kiểm tra service account có quyền đọc GCS và write BigQuery

### Lỗi BigQuery insert
- Kiểm tra schema match với data
- Kiểm tra service account có quyền `roles/bigquery.dataEditor`

