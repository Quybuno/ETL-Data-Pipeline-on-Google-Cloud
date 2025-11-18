# 📋 Hướng Dẫn Triển Khai ETL Pipeline trên GCP Console (UI)

Hướng dẫn triển khai toàn bộ hạ tầng ETL pipeline cho dữ liệu bất động sản Hà Nội **trực tiếp trên GCP Console (UI)**, không cần Terraform.

## 🎯 Tổng Quan

Project này triển khai ETL pipeline với các thành phần **thuần Cloud Computing Core**:

- **Cloud Run**: Crawler serverless chạy container
- **Cloud Functions Gen2**: Xử lý file event-driven từ GCS
- **BigQuery**: Data warehouse serverless
- **Cloud Storage**: Lưu trữ raw và clean data
- **Artifact Registry**: Kho chứa Docker images
- **Cloud Composer** (tùy chọn): Orchestration với Airflow

> 📖 **Xem chi tiết**: [CLOUD_COMPUTING_CORE.md](CLOUD_COMPUTING_CORE.md) - Xác nhận project thuần Cloud Computing Core

---

## 📋 Prerequisites
   
1. **GCP Project**: `etl-gcp-200412` (hoặc project của bạn)
2. **Region**: `asia-southeast1`
3. **Quyền IAM**: Editor hoặc Owner
4. **Docker Desktop**: Đã cài và đang chạy (để build/push image)

---

## 🚀 Bước 1: Enable APIs

1. Truy cập: https://console.cloud.google.com/apis/library?project=etl-gcp-200412
2. Enable các APIs sau:
   - ✅ **Artifact Registry API**
   - ✅ **Cloud Run API**
   - ✅ **Cloud Functions API**
   - ✅ **Eventarc API**
   - ✅ **Cloud Storage API**
   - ✅ **BigQuery API**
   - ✅ **Cloud Composer API** (nếu dùng Composer)
   - ✅ **Cloud Logging API**
   - ✅ **Cloud Monitoring API**
   - ✅ **Cloud Pub/Sub API**
   - ✅ **Compute Engine API**
   - ✅ **Identity and Access Management (IAM) API**

---

## 🪣 Bước 2: Tạo Cloud Storage Buckets

### 2.1. Raw Bucket

1. Truy cập: https://console.cloud.google.com/storage/create-bucket?project=etl-gcp-200412
2. Cấu hình:
   - **Name**: `hanoi-bds-raw-data-final` (hoặc tên unique nếu bị conflict)
   - **Location type**: Region
   - **Location**: `asia-southeast1`
   - **Storage class**: Standard
   - **Access control**: Uniform (recommended)
3. Click **Create**

### 2.2. Clean Bucket

1. Tạo bucket thứ 2:
   - **Name**: `hanoi-bds-clean-data-final` (hoặc tên unique)
   - **Location**: `asia-southeast1`
   - Các cấu hình khác giống raw bucket
2. Click **Create**

### 2.3. Source Code Bucket (cho Cloud Function)

1. Tạo bucket thứ 3:
   - **Name**: `etl-gcp-200412-cf-src` (hoặc tên unique)
   - **Location**: `asia-southeast1`
2. Click **Create**

---

## 📊 Bước 3: Tạo BigQuery Dataset và Table

### 3.1. Tạo Dataset

1. Truy cập: https://console.cloud.google.com/bigquery?project=etl-gcp-200412
2. Click **"..."** bên cạnh project → **"Create dataset"**
3. Cấu hình:
   - **Dataset ID**: `hanoi_real_estate`
   - **Location type**: Region
   - **Location**: `asia-southeast1` ⚠️ **QUAN TRỌNG: Không chọn US!**
4. Click **Create dataset**

### 3.2. Tạo Table

1. Click vào dataset `hanoi_real_estate` vừa tạo
2. Click **"Compose new query"**
3. Copy toàn bộ nội dung từ file `D:\Nhadat\bigquery\schema.sql`
4. Paste vào query editor
5. **Sửa project ID** trong SQL từ `etl-gcp-200501` → `etl-gcp-200412` (nếu cần)
6. Click **Run**

---

## 🐳 Bước 4: Tạo Artifact Registry Repository

1. Truy cập: https://console.cloud.google.com/artifacts?project=etl-gcp-200412
2. Click **"Create Repository"**
3. Cấu hình:
   - **Name**: `etl-repo`
   - **Format**: Docker
   - **Location**: `asia-southeast1`
4. Click **Create**

---

## 🚢 Bước 5: Build và Push Docker Image

### 5.1. Build Image Locally

```powershell
cd D:\Nhadat\cloud-run

# Cấu hình Docker auth
gcloud auth configure-docker asia-southeast1-docker.pkg.dev --quiet

# Build image
docker build -t "asia-southeast1-docker.pkg.dev/etl-gcp-200412/etl-repo/crawler:latest" .

# Push image
docker push "asia-southeast1-docker.pkg.dev/etl-gcp-200412/etl-repo/crawler:latest"
```

### 5.2. Verify Image trên Console

1. Truy cập: https://console.cloud.google.com/artifacts/docker/etl-gcp-200412/asia-southeast1/etl-repo?project=etl-gcp-200412
2. Kiểm tra image `crawler:latest` đã xuất hiện

---

## ☁️ Bước 6: Tạo Cloud Run Service

1. Truy cập: https://console.cloud.google.com/run?project=etl-gcp-200412
2. Click **"Create Service"**
3. **Tab 1: Deploy container image**
   - **Container image URL**: `asia-southeast1-docker.pkg.dev/etl-gcp-200412/etl-repo/crawler:latest`
   - Click **"Select"**
4. **Tab 2: Service name and region**
   - **Service name**: `crawler-service`
   - **Region**: `asia-southeast1`
5. **Tab 3: Configure service**
   - **Container port**: `8080`
   - **Environment variables** (click "Add variable"):
     - `RAW_BUCKET` = `hanoi-bds-raw-data-final`
     - `SOURCE` = `mogi`
     - `MAX_PAGES` = `40` (số trang mỗi ngày, tùy chọn - mặc định 40)
   - **Min instances**: `0`
   - **Max instances**: `3`
6. **Tab 4: Security**
   - **Allow unauthenticated invocations**: ✅ **Enable** (để demo)
7. Click **"Create"**

### 6.1. Lấy Cloud Run URL

Sau khi service tạo xong, copy **URL** từ trang service details (ví dụ: `https://crawler-service-xxxxx-as.a.run.app`)

---

## 📦 Bước 7: Upload Cloud Function Source Code

### 7.1. Package Source Code

```powershell
cd D:\Nhadat\cloud-function

# Tạo zip file
Compress-Archive -Path *.py,requirements.txt -DestinationPath ..\cf-src.zip -Force
```

### 7.2. Upload lên GCS

**Cách 1: Dùng Python Script (Khuyến nghị)**
```powershell
cd D:\Nhadat\cloud-function
pip install google-cloud-storage
python upload_source.py
```

**Cách 2: Dùng Console**
1. Truy cập: https://console.cloud.google.com/storage/browser/etl-gcp-200412-cf-src?project=etl-gcp-200412
2. Click **"Upload files"**
3. Chọn file `D:\Nhadat\cf-src.zip`
4. Click **"Upload"**

---

## ⚡ Bước 8: Tạo Cloud Run Function (Cloud Functions Gen2)

> Cloud Functions Gen2 giờ hiển thị trong Console dưới mục **Cloud Run → Functions**. Bạn có thể triển khai qua giao diện mới hoặc dùng CLI.

### 8.1. Tạo function qua Console

1. Mở trang Functions: `https://console.cloud.google.com/run/functions/list?project=etl-gcp-200412`
   - Hoặc trong thanh tìm kiếm gõ **“Cloud Run functions”** và pin vào sidebar.
2. Chọn region ở góc phải: **asia-southeast1** → bấm **Create function**.
3. **Basic information**
   - Function name: `etl-cleaner`
   - Environment: `2nd gen`
   - Region: `asia-southeast1`
4. **Runtime & entry point**
   - Runtime: `Python 3.11`
   - Entry point: `main` (đúng với hàm trong `cloud-function/main.py`)
5. **Source**
   - Source type: `Cloud Storage archive`
   - URL: `gs://etl-gcp-200412-cf-src/cf-src.zip`
   - Stage bucket: dùng `etl-gcp-200412-cf-src` (hoặc bucket staging khác nếu muốn)
6. **Trigger (Eventarc)**
   - Provider: `Google sources`
   - Event provider: `Cloud Storage`
   - Event type: `Object finalized (google.cloud.storage.object.v1.finalized)`
   - Bucket: `hanoi-bds-raw-data-final`
7. **Environment variables**
   - `RAW_BUCKET = hanoi-bds-raw-data-final`
   - `CLEAN_BUCKET = hanoi-bds-clean-data-final`
   - `DATASET_ID = hanoi_real_estate`
   - `TABLE_ID = properties`
8. **Service account & quyền**
   - Có thể dùng default compute service account (đã là Editor) hoặc chọn `cf-handler-sa` nếu đã tạo.
   - Tối thiểu service account chạy function cần: `Storage Object Admin`, `BigQuery Data Editor`, `Logs Writer`.
9. Triển khai: bấm **Deploy** và đợi trạng thái `Active`.

> **Lưu ý quyền Eventarc / Pub/Sub:** Nếu Console hiện cảnh báo, bấm **Grant** (hoặc cấp thủ công):
> - `service-<PROJECT_NUMBER>@gcp-sa-eventarc.iam.gserviceaccount.com` → `roles/eventarc.eventReceiver`
> - `service-<PROJECT_NUMBER>@gcp-sa-pubsub.iam.gserviceaccount.com` → `roles/iam.serviceAccountTokenCreator`

### 8.2. Triển khai bằng CLI (tuỳ chọn)

```powershell
cd D:\Nhadat\cloud-function
python upload_source.py

gcloud functions deploy etl-cleaner `
  --gen2 `
  --region=asia-southeast1 `
  --runtime=python311 `
  --source=gs://etl-gcp-200412-cf-src/cf-src.zip `
  --entry-point=main `
  --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" `
  --trigger-event-filters="bucket=hanoi-bds-raw-data-final" `
  --set-env-vars="RAW_BUCKET=hanoi-bds-raw-data-final,CLEAN_BUCKET=hanoi-bds-clean-data-final,DATASET_ID=hanoi_real_estate,TABLE_ID=properties"
```

Sau deploy:

```powershell
gcloud functions list --gen2 --regions=asia-southeast1
gcloud functions describe etl-cleaner --gen2 --region=asia-southeast1
gcloud functions logs read etl-cleaner --gen2 --region=asia-southeast1 --limit=50
```

Nếu gặp lỗi permission, kiểm tra lại các quyền ở bước trên rồi deploy lại.

---

## 🎭 Bước 9: (Tùy chọn) Tạo Cloud Composer

### 9.1. Tạo Composer Environment

1. Truy cập: https://console.cloud.google.com/composer/environments?project=etl-gcp-200412
2. Click **"Create"**
3. **Environment name**: `etl-orchestrator`
4. **Location**: `asia-southeast1`
5. **Composer version**: **Composer 3** (hoặc Composer 2 nếu cần)
6. **Environment size**: `Small` (hoặc Medium/Large tùy nhu cầu)
7. **Service account**: Tạo mới hoặc chọn existing
   - Nếu tạo mới: `composer-worker-sa`
   - Role: `Composer Worker`
8. Click **"Create"**
   - ⚠️ **Lưu ý**: Mất 15-30 phút và tốn chi phí

### 9.2. Upload DAG (Sau khi Environment Ready)

1. Sau khi environment ready, lấy DAGs bucket:
   - Vào environment details → **"DAGs folder"** → copy GCS path
2. Upload DAG file:
   - Truy cập Storage bucket của Composer
   - Navigate đến folder `dags/`
   - Upload file `D:\Nhadat\airflow\dags\etl_pipeline.py`

### 9.3. Cấu hình Airflow Variables (Cloud Run URL)

Pipeline cần biết URL Cloud Run crawler. Có hai cách:

- **Airflow UI:** Vào Composer Airflow UI → **Admin → Variables** → **+**
  - Key: `cloud_run_crawler_url`
  - Value: URL Cloud Run `crawler-service` (ví dụ: `https://crawler-service-xxxxx-as.a.run.app`)
- **CLI:**
  ```bash
  gcloud composer environments run etl-orchestrator --location asia-southeast1 variables -- \
    set cloud_run_crawler_url "https://crawler-service-xxxxx-as.a.run.app"
  ```

(Composer cũng đọc env `CLOUD_RUN_URL`. Nếu thích, có thể đặt trong phần Environment variables của Composer environment.)

---

## ✅ Bước 10: Test Pipeline

### 10.1. Test Cloud Run Crawler

1. Lấy Cloud Run URL từ service details
2. Test qua HTTP POST:
   ```powershell
   # PowerShell
   $url = "https://crawler-service-xxxxx-as.a.run.app"
   Invoke-WebRequest -Uri "$url?raw_bucket=hanoi-bds-raw-data-final" -Method POST
   ```
3. Kiểm tra logs:
   - Truy cập: image.png
4. Kiểm tra data trong raw bucket:
   - Truy cập: https://console.cloud.google.com/storage/browser/hanoi-bds-raw-data-final?project=etl-gcp-200412

### 10.2. Test Cloud Function

1. Tạo file test:
   ```powershell
   echo '{"url":"https://mogi.vn/test","price":"2 tỷ","address":"Hà Nội"}' | Out-File -Encoding utf8 test.jsonl
   ```
2. Upload vào raw bucket:
   - Truy cập: https://console.cloud.google.com/storage/browser/hanoi-bds-raw-data-final?project=etl-gcp-200412
   - Click **"Upload files"**
   - Upload vào path: `source=mogi/dt=2025-01-01/test.jsonl`
3. Kiểm tra logs:
   - Truy cập: https://console.cloud.google.com/functions/details/asia-southeast1/gcs-file-handler?project=etl-gcp-200412
   - Click tab **"Logs"**
4. Kiểm tra clean bucket hoặc BigQuery:
   - Clean bucket: https://console.cloud.google.com/storage/browser/hanoi-bds-clean-data-final?project=etl-gcp-200412
   - BigQuery: https://console.cloud.google.com/bigquery?project=etl-gcp-200412
     - Query: `SELECT * FROM hanoi_real_estate.properties LIMIT 10`

---

## 📊 Bước 11: Tạo Looker Studio Dashboard

1. Truy cập: https://datastudio.google.com/
2. Click **"Create"** → **"Data Source"**
3. Chọn **"BigQuery"**
4. Chọn:
   - **Project**: `etl-gcp-200412`
   - **Dataset**: `hanoi_real_estate`
   - **Table**: `properties`
5. Click **"Connect"**
6. Tạo dashboard theo hướng dẫn trong: `D:\Nhadat\analysis\LOOKER_STUDIO_STEP_BY_STEP.md`

---

## 🎯 Demo theo các "Cốt lõi"

### Cốt lõi 1: Cloud Computing Core
- **Serverless Architecture**: Tất cả services tự động scale, không cần quản lý infrastructure
- **Show**: Có thể dùng `gcloud` commands để tạo và quản lý resources
- **Giải thích**: Cloud-native approach với managed services

### Cốt lõi 2: Elastic Compute & Serverless
- **Cloud Run**: 
  - Show metrics: https://console.cloud.google.com/run/detail/asia-southeast1/crawler-service/metrics?project=etl-gcp-200412
  - Giải thích: Auto-scaling, scale to zero, chỉ tính phí khi chạy
- **Cloud Function**:
  - Show logs và metrics
  - Giải thích: Event-driven, tự động scale, serverless

### Cốt lõi 3: Managed Services (PaaS)
- **BigQuery**:
  - Chạy query mẫu: `SELECT COUNT(*) FROM hanoi_real_estate.properties`
  - Giải thích: Serverless data warehouse, không cần quản lý cluster
- **Cloud Composer** (nếu có):
  - Mở Airflow UI từ environment details
  - Show DAG graph
  - Giải thích: Managed Airflow, tự động scale

### Cốt lõi 4: Accessibility & Observability (SaaS)
- **Looker Studio**: 
  - Share dashboard link cho end-user
  - Giải thích: SaaS, truy cập qua web, không cần cài đặt
- **Cloud Monitoring**:
  - Truy cập: https://console.cloud.google.com/monitoring?project=etl-gcp-200412
  - Show metrics của Cloud Run và Cloud Function
  - Tạo alert mẫu cho error rate hoặc latency

---

## 🔧 Troubleshooting

### Lỗi Cloud Run không deploy được
- Kiểm tra image đã push: https://console.cloud.google.com/artifacts/docker/etl-gcp-200412/asia-southeast1/etl-repo?project=etl-gcp-200412
- Kiểm tra IAM permissions: https://console.cloud.google.com/iam-admin/iam?project=etl-gcp-200412

### Lỗi Cloud Function không trigger
- Kiểm tra Eventarc trigger: https://console.cloud.google.com/eventarc/triggers?project=etl-gcp-200412
- Kiểm tra service account có quyền: Storage Object Admin, BigQuery User
- Kiểm tra Eventarc Service Agent có quyền: Eventarc Service Agent role

### Lỗi BigQuery insert
- Kiểm tra schema match với data
- Kiểm tra service account có quyền `BigQuery Data Editor`

### Lỗi Composer
- Composer 2: KHÔNG được set zone/machine_type trong node_config
- Composer 3: Dùng environment_size và workloads_config thay vì node_config

---

## 📝 Checklist Hoàn Thành

- [ ] Enable tất cả APIs
- [ ] Tạo 3 buckets (raw, clean, cf-src)
- [ ] Tạo BigQuery dataset và table
- [ ] Tạo Artifact Registry repository
- [ ] Build và push Docker image
- [ ] Tạo Cloud Run service
- [ ] Upload Cloud Function source code
- [ ] Tạo Cloud Function Gen2
- [ ] Cấp quyền Eventarc Service Agent (nếu cần)
- [ ] (Tùy chọn) Tạo Cloud Composer
- [ ] Test Cloud Run crawler
- [ ] Test Cloud Function
- [ ] Tạo Looker Studio dashboard
- [ ] Demo theo 4 cốt lõi

---

## 🔗 Quick Links

- **Storage**: https://console.cloud.google.com/storage?project=etl-gcp-200412
- **BigQuery**: https://console.cloud.google.com/bigquery?project=etl-gcp-200412
- **Artifact Registry**: https://console.cloud.google.com/artifacts?project=etl-gcp-200412
- **Cloud Run**: https://console.cloud.google.com/run?project=etl-gcp-200412
- **Cloud Functions**: https://console.cloud.google.com/functions?project=etl-gcp-200412
- **Cloud Composer**: https://console.cloud.google.com/composer?project=etl-gcp-200412
- **IAM**: https://console.cloud.google.com/iam-admin?project=etl-gcp-200412
- **Monitoring**: https://console.cloud.google.com/monitoring?project=etl-gcp-200412
- **Logging**: https://console.cloud.google.com/logs?project=etl-gcp-200412

---

## 📚 Tài Liệu Tham Khảo

- **CLOUD_COMPUTING_CORE.md**: ✅ Xác nhận project thuần Cloud Computing Core
- **DEPLOYMENT.md**: Hướng dẫn triển khai manual từng bước
- **FULL_CHECKLIST.md**: Checklist đầy đủ từ đầu đến cuối
- **analysis/LOOKER_STUDIO_STEP_BY_STEP.md**: Hướng dẫn tạo Looker Studio dashboard
- **SETUP_GCP_PERMISSIONS.md**: Hướng dẫn cấp quyền IAM
- **architecture_diagram.md**: Sơ đồ kiến trúc 3 lớp (IaaS/PaaS/SaaS)

---

## ⚠️ Lưu Ý Quan Trọng

1. **Project ID phải thống nhất** trong tất cả resources (etl-gcp-200412)
2. **Region phải thống nhất** (asia-southeast1)
3. **Composer tốn chi phí** và mất 15-30 phút để tạo
4. **Docker image phải push TRƯỚC** khi tạo Cloud Run service
5. **Cloud Function source code phải upload TRƯỚC** khi deploy function
6. **Eventarc Service Agent** cần quyền để trigger Cloud Function từ GCS events

---

**Chúc bạn triển khai thành công! 🎉**

