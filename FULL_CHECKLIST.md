# 📋 Checklist Đầy Đủ - Từ Đầu Đến Cuối

## ✅ PHẦN 1: Setup Ban Đầu (Làm Một Lần)

### 1.1. Enable APIs trên GCP Console
- Truy cập: https://console.cloud.google.com/apis/library?project=etl-gcp-200501
- Enable các APIs sau:
  - ✅ Artifact Registry API
  - ✅ Cloud Run API
  - ✅ Cloud Functions API
  - ✅ Eventarc API
  - ✅ Cloud Storage API
  - ✅ BigQuery API
  - ✅ Cloud Composer API
  - ✅ Cloud Logging API
  - ✅ Cloud Monitoring API
  - ✅ Cloud Pub/Sub API
  - ✅ Compute Engine API
  - ✅ Identity and Access Management (IAM) API

### 1.2. Cấp Quyền IAM (Nếu chưa có)
- Truy cập: https://console.cloud.google.com/iam-admin/iam?project=etl-gcp-200501
- Đảm bảo user có quyền **Editor** hoặc **Owner**
- Nếu chưa có, yêu cầu Owner/Admin cấp quyền

### 1.3. Cài Đặt & Khởi Động Docker Desktop
- ✅ Đảm bảo Docker Desktop đã cài và đang chạy
- Kiểm tra: `docker ps` (không được lỗi)

---

## ✅ PHẦN 2: Tạo BigQuery Table

### 2.1. Tạo Dataset và Table
```powershell
cd D:\Nhadat\bigquery
pip install google-cloud-bigquery
python create_table.py
```
✅ **Kết quả:** Dataset `hanoi_real_estate` và table `properties` đã được tạo

---

## ✅ PHẦN 3: Build & Push Docker Image

### 3.1. Build Docker Image cho Cloud Run
```powershell
cd D:\Nhadat\cloud-run

# Build image
docker build -t "asia-southeast1-docker.pkg.dev/etl-gcp-200501/etl-repo/crawler:latest" .
```

### 3.2. Push Image lên Artifact Registry
```powershell
# Cấu hình Docker auth (chỉ cần làm 1 lần)
gcloud auth configure-docker asia-southeast1-docker.pkg.dev --quiet

# Push image
docker push "asia-southeast1-docker.pkg.dev/etl-gcp-200501/etl-repo/crawler:latest"
```
✅ **Kết quả:** Image đã được push lên Artifact Registry

---

## ✅ PHẦN 4: Upload Cloud Function Source

### 4.1. Package và Upload Cloud Function Source
```powershell
cd D:\Nhadat\cloud-function

# Cài đặt dependencies (nếu chưa có)
pip install google-cloud-storage

# Chạy script Python (tự động tạo zip và upload)
python upload_source.py
```
✅ **Kết quả:** File `cf-src.zip` đã được upload lên `gs://etl-gcp-200501-cf-src/`

---

## ✅ PHẦN 5: Cấu Hình Terraform Variables

### 5.1. Kiểm Tra terraform.tfvars
Mở file `D:\Nhadat\terraform\terraform.tfvars` và đảm bảo có:

```hcl
project_id           = "etl-gcp-200501"
region               = "asia-southeast1"
location             = "asia-southeast1"

# Cloud Run image (phải match với image đã push)
crawler_image        = "asia-southeast1-docker.pkg.dev/etl-gcp-200501/etl-repo/crawler:latest"

# Cloud Function source
cf_source_bucket     = "etl-gcp-200501-cf-src"
cf_source_object     = "cf-src.zip"

# Cloud Function environment variables (QUAN TRỌNG!)
cf_env = {
  RAW_BUCKET    = "hanoi-bds-raw-data"
  CLEAN_BUCKET  = "hanoi-bds-clean-data"
  DATASET_ID    = "hanoi_real_estate"
  TABLE_ID      = "properties"
}
```

---

## ✅ PHẦN 6: Import Resources Đã Tồn Tại (Nếu Có)

### 6.1. Import BigQuery Dataset
```powershell
cd D:\Nhadat\terraform
terraform import google_bigquery_dataset.dataset projects/etl-gcp-200501/datasets/hanoi_real_estate
```

### 6.2. Import Storage Buckets (Nếu đã tồn tại)
```powershell
# Nếu bucket đã tồn tại và muốn dùng
terraform import google_storage_bucket.raw_bucket hanoi-bds-raw-data
terraform import google_storage_bucket.clean_bucket hanoi-bds-clean-data

# HOẶC: Đổi tên bucket trong terraform.tfvars để tạo mới
```

---

## ✅ PHẦN 7: Deploy Infrastructure với Terraform

### 7.1. Initialize Terraform (chỉ cần làm 1 lần)
```powershell
cd D:\Nhadat\terraform
terraform init
```

### 7.2. Review Plan
```powershell
terraform plan
```
Xem trước các resources sẽ được tạo

### 7.3. Apply Infrastructure
```powershell
terraform apply
```
Gõ `yes` khi được hỏi xác nhận

⚠️ **Lưu ý:**
- Cloud Composer sẽ mất 20-30 phút để tạo và tốn chi phí
- Đảm bảo Docker image đã được push TRƯỚC khi apply (nếu không Cloud Run sẽ lỗi)

✅ **Kết quả:** Tất cả resources đã được tạo:
- ✅ Storage Buckets (raw, clean)
- ✅ BigQuery Dataset
- ✅ Artifact Registry Repository
- ✅ Cloud Run Service
- ✅ Cloud Function Gen2
- ✅ Cloud Composer Environment
- ✅ Service Accounts và IAM permissions

---

## ✅ PHẦN 8: Test Pipeline

### 8.1. Lấy Cloud Run URL
```powershell
cd D:\Nhadat\terraform
terraform output cloud_run_url
```

### 8.2. Test Cloud Run Crawler
```powershell
# Trigger crawler qua HTTP POST
curl -X POST "<CLOUD_RUN_URL>?raw_bucket=hanoi-bds-raw-data"
```

### 8.3. Test Cloud Function (Event-driven)
```powershell
# Tạo file test
echo '{"url":"https://mogi.vn/test","price":"2 tỷ","address":"Hà Nội"}' | Out-File -Encoding utf8 test.jsonl

# Upload vào raw bucket (sẽ trigger Cloud Function tự động)
gsutil cp test.jsonl gs://hanoi-bds-raw-data/source=mogi/dt=2025-01-01/test.jsonl
```

### 8.4. Kiểm Tra Logs
- Cloud Run logs: https://console.cloud.google.com/run?project=etl-gcp-200501
- Cloud Function logs: https://console.cloud.google.com/functions?project=etl-gcp-200501
- BigQuery: Kiểm tra table `properties` đã có data chưa

---

## ✅ PHẦN 9: Deploy Airflow DAG (Optional)

### 9.1. Đợi Composer Environment Ready (~20-30 phút)

### 9.2. Lấy DAGs Folder Path
```powershell
gcloud composer environments describe etl-orchestrator --location asia-southeast1
```

### 9.3. Upload DAG File
```powershell
# Copy DAG lên Composer bucket
gsutil cp D:\Nhadat\airflow\dags\etl_pipeline.py gs://<COMPOSER_BUCKET>/dags/etl_pipeline.py
```

### 9.4. Kiểm Tra Airflow UI
- Truy cập Airflow UI từ Composer environment
- Xem DAG `hanoi_real_estate_etl` đã xuất hiện

---

## ✅ PHẦN 10: Demo Theo Các "Cốt Lõi"

### 10.1. Cốt Lõi 1: IaC (Infrastructure as Code)
- ✅ Show file `terraform/main.tf`
- ✅ Chạy `terraform plan` để xem planned changes
- ✅ Giải thích: Toàn bộ infrastructure định nghĩa bằng code

### 10.2. Cốt Lõi 2: Elastic Compute & Serverless
- ✅ Cloud Run: Show logs/metrics, giải thích auto-scaling
- ✅ Cloud Function: Upload file test → xem logs → giải thích event-driven

### 10.3. Cốt Lõi 3: Managed Services (PaaS)
- ✅ BigQuery: Chạy query mẫu, giải thích serverless data warehouse
- ✅ Cloud Composer: Mở Airflow UI, show DAG graph

### 10.4. Cốt Lõi 4: Accessibility & Observability (SaaS)
- ✅ Looker Studio: Tạo dashboard kết nối BigQuery
- ✅ Cloud Monitoring: Show metrics, tạo alert mẫu

---

## 🎯 TÓM TẮT THEO THỨ TỰ:

1. ✅ **Setup:** Enable APIs, cấp quyền IAM
2. ✅ **BigQuery:** Tạo dataset và table
3. ✅ **Docker:** Build và push image
4. ✅ **Cloud Function:** Upload source code
5. ✅ **Terraform:** Import resources đã có (nếu cần)
6. ✅ **Terraform:** Apply infrastructure
7. ✅ **Test:** Test Cloud Run và Cloud Function
8. ✅ **Airflow:** Deploy DAG (optional)
9. ✅ **Demo:** Demo theo 4 cốt lõi

---

## ⚠️ LƯU Ý QUAN TRỌNG:

1. **Docker image phải push TRƯỚC khi terraform apply** (nếu không Cloud Run sẽ lỗi)
2. **Cloud Composer tốn chi phí và mất 20-30 phút** để tạo
3. **Nếu bucket/dataset đã tồn tại** → phải import hoặc đổi tên
4. **Đảm bảo `terraform.tfvars` có đầy đủ config**, đặc biệt là `cf_env`

---

## 📞 Troubleshooting:

- Xem `DEPLOYMENT.md` cho hướng dẫn chi tiết
- Xem `QUICK_FIX.md` cho các lỗi thường gặp
- Xem `SETUP_GCP_PERMISSIONS.md` cho vấn đề quyền

