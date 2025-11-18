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

## ✅ PHẦN 5: Tạo Infrastructure qua GCP Console

Thực hiện theo hướng dẫn trong **README.md** để tạo các resources sau:

### 5.1. Tạo Cloud Storage Buckets
- `hanoi-bds-raw-data-final` (raw data)
- `hanoi-bds-clean-data-final` (clean data)
- `etl-gcp-200412-cf-src` (Cloud Run Function source code)

Xem chi tiết: **README.md** - Bước 2

### 5.2. Tạo Artifact Registry Repository
- Repository name: `etl-repo`
- Format: Docker
- Location: `asia-southeast1`

Xem chi tiết: **README.md** - Bước 4

### 5.3. Tạo Cloud Run Service
- Service name: `crawler-service`
- Image: `asia-southeast1-docker.pkg.dev/etl-gcp-200412/etl-repo/crawler:latest`
- Environment variables:
  - `RAW_BUCKET` = `hanoi-bds-raw-data-final`
  - `SOURCE` = `mogi`
  - `MAX_PAGES` = `40`

Xem chi tiết: **README.md** - Bước 6

### 5.4. Tạo Cloud Run Function (Cloud Functions Gen2)
- Mở mục **Cloud Run → Functions** (search “Cloud Run functions”), chọn region `asia-southeast1`
- Function name: `etl-cleaner`
- Runtime: `Python 3.11`, Entry point: `main`
- Source: `gs://etl-gcp-200412-cf-src/cf-src.zip`
- Trigger: Cloud Storage → Object finalized từ bucket `hanoi-bds-raw-data-final`
- Environment variables: `RAW_BUCKET`, `CLEAN_BUCKET`, `DATASET_ID`, `TABLE_ID`
- Service account cần quyền: `Storage Object Admin`, `BigQuery Data Editor`, `Logs Writer`
- **Composer Airflow Variable:** Trong Airflow UI → Admin → Variables → thêm `cloud_run_crawler_url = https://crawler-service-xxxxx-as.a.run.app`

Xem chi tiết: **README.md** - Bước 8

### 5.5. (Tùy chọn) Tạo Cloud Composer
- Environment name: `etl-orchestrator`
- Location: `asia-southeast1`

⚠️ **Lưu ý:** Cloud Composer sẽ mất 20-30 phút để tạo và tốn chi phí

Xem chi tiết: **README.md** - Bước 9

---

## ✅ PHẦN 6: Test Pipeline

### 6.1. Lấy Cloud Run URL
Truy cập GCP Console: https://console.cloud.google.com/run?project=etl-gcp-200412
Copy URL từ service details (ví dụ: `https://crawler-service-xxxxx-as.a.run.app`)

### 6.2. Test Cloud Run Crawler
```powershell
# Trigger crawler qua HTTP POST
curl -X POST "<CLOUD_RUN_URL>?raw_bucket=hanoi-bds-raw-data-final"
```

### 6.3. Test Cloud Function (Event-driven)
```powershell
# Tạo file test
echo '{"url":"https://mogi.vn/test","price":"2 tỷ","address":"Hà Nội"}' | Out-File -Encoding utf8 test.jsonl

# Upload vào raw bucket (sẽ trigger Cloud Function tự động)
gsutil cp test.jsonl gs://hanoi-bds-raw-data-final/source=mogi/dt=2025-01-01/test.jsonl
```

### 6.4. Kiểm Tra Logs
- Cloud Run logs: https://console.cloud.google.com/run?project=etl-gcp-200412
- Cloud Function logs: https://console.cloud.google.com/run/functions/logs?project=etl-gcp-200412
- BigQuery: Kiểm tra table `properties` đã có data chưa

---

## ✅ PHẦN 7: Deploy Airflow DAG (Optional)

### 7.1. Đợi Composer Environment Ready (~20-30 phút)

### 7.2. Lấy DAGs Folder Path
```powershell
gcloud composer environments describe etl-orchestrator --location asia-southeast1
```

### 7.3. Upload DAG File
```powershell
# Copy DAG lên Composer bucket
gsutil cp D:\Nhadat\airflow\dags\etl_pipeline.py gs://<COMPOSER_BUCKET>/dags/etl_pipeline.py
```

### 7.4. Kiểm Tra Airflow UI
- Truy cập Airflow UI từ Composer environment
- Xem DAG `hanoi_real_estate_etl` đã xuất hiện

---

## ✅ PHẦN 8: Demo Theo Các "Cốt Lõi"

### 8.1. Cốt Lõi 1: Cloud Computing Core
- ✅ Serverless Architecture: Tất cả services tự động scale
- ✅ Managed Services: Không cần quản lý infrastructure
- ✅ Giải thích: Cloud-native approach với auto-scaling

### 8.2. Cốt Lõi 2: Elastic Compute & Serverless
- ✅ Cloud Run: Show logs/metrics, giải thích auto-scaling
- ✅ Cloud Function: Upload file test → xem logs → giải thích event-driven

### 8.3. Cốt Lõi 3: Managed Services (PaaS)
- ✅ BigQuery: Chạy query mẫu, giải thích serverless data warehouse
- ✅ Cloud Composer: Mở Airflow UI, show DAG graph

### 8.4. Cốt Lõi 4: Accessibility & Observability (SaaS)
- ✅ Looker Studio: Tạo dashboard kết nối BigQuery
- ✅ Cloud Monitoring: Show metrics, tạo alert mẫu

---

## 🎯 TÓM TẮT THEO THỨ TỰ:

1. ✅ **Setup:** Enable APIs, cấp quyền IAM
2. ✅ **BigQuery:** Tạo dataset và table
3. ✅ **Docker:** Build và push image
4. ✅ **Cloud Function:** Upload source code
5. ✅ **Infrastructure:** Tạo resources qua GCP Console (buckets, Cloud Run, Cloud Function)
6. ✅ **Test:** Test Cloud Run và Cloud Function
7. ✅ **Airflow:** Deploy DAG (optional)
8. ✅ **Demo:** Demo theo 4 cốt lõi

---

## ⚠️ LƯU Ý QUAN TRỌNG:

1. **Docker image phải push TRƯỚC khi tạo Cloud Run service** (nếu không sẽ lỗi)
2. **Cloud Composer tốn chi phí và mất 20-30 phút** để tạo
3. **Nếu bucket/dataset đã tồn tại** → có thể dùng lại hoặc tạo mới với tên khác
4. **Đảm bảo environment variables đúng** khi tạo Cloud Run và Cloud Function

---

## 📞 Troubleshooting:

- Xem `README.md` cho hướng dẫn chi tiết triển khai qua UI
- Xem `DEPLOYMENT.md` cho hướng dẫn manual deployment
- Xem `SETUP_GCP_PERMISSIONS.md` cho vấn đề quyền

