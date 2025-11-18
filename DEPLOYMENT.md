# Hướng dẫn Deployment End-to-End (Manual Deployment)

Tài liệu này mô tả toàn bộ quy trình triển khai manual từ đầu đến cuối cho một project duy nhất (ví dụ: `etl-gcp-200412`). Tất cả các bước được thực hiện qua GCP Console hoặc gcloud CLI.

## 1. Build và Push Docker Image cho Cloud Run

**⚠️ Quan trọng: Cần Docker Desktop đang chạy trước khi build!**

Nếu chưa cài Docker Desktop:
1. Tải Docker Desktop cho Windows: https://www.docker.com/products/docker-desktop
2. Cài đặt và khởi động Docker Desktop
3. Đợi Docker engine khởi động xong (icon Docker ở system tray)

```powershell
# Navigate to cloud-run directory
cd D:\Nhadat\cloud-run

# Kiểm tra Docker đang chạy
docker ps
# Nếu lỗi "cannot connect to Docker daemon", cần khởi động Docker Desktop

# Cấu hình Docker authentication với Artifact Registry
$REGION = "asia-southeast1"
$PROJECT = "etl-gcp-200412"
$REPO = "etl-repo"
$IMAGE = "crawler"

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# Build image
docker build -t "${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${IMAGE}:latest" .

# Push image
docker push "${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${IMAGE}:latest"
```

**Lưu ý:** Image URL sẽ là: `asia-southeast1-docker.pkg.dev/etl-gcp-200412/etl-repo/crawler:latest`

## 2. Tạo BigQuery Table

**Khuyến nghị: Dùng Python script** (tự động tạo dataset nếu chưa có, đúng project/location)

```powershell
cd D:\Nhadat\bigquery
pip install google-cloud-bigquery
python create_table.py
```

**Hoặc dùng BigQuery Console (web UI)** - Cần tạo dataset trước:

1. Mở BigQuery Console: https://console.cloud.google.com/bigquery?project=etl-gcp-200412
2. **Tạo dataset trước (quan trọng!):**
   - Click vào project `etl-gcp-200412` ở sidebar
   - Click "..." → "Create dataset"
   - Dataset ID: `hanoi_real_estate`
   - **Location type: Region** → Chọn **asia-southeast1** ⚠️ **QUAN TRỌNG: Không chọn US!**
   - Click "Create dataset"
3. Sau đó tạo table:
   - Click vào dataset `hanoi_real_estate`
   - Click "Compose new query"
   - Copy toàn bộ nội dung từ file `D:\Nhadat\bigquery\schema.sql`
   - Paste vào editor và click "Run"

**Lưu ý:** Dataset location phải là **asia-southeast1**, không phải US!

**Hoặc dùng bq CLI:**

```powershell
# Option 1: Chạy PowerShell as Administrator
# Sau đó chạy:
cd D:\Nhadat\bigquery
Get-Content schema.sql | bq query --use_legacy_sql=false

# Option 2: Dùng full path và escape quotes nếu cần
cd D:\Nhadat\bigquery
bq query --use_legacy_sql=false --format=prettyjson "$(Get-Content schema.sql -Raw)"
```

## 3. Package và Upload Cloud Function Source

**Khuyến nghị: Dùng Python script** (không cần quyền admin, đúng project/region)

```powershell
cd D:\Nhadat\cloud-function

# Cài đặt GCS client nếu chưa có
pip install google-cloud-storage

# Chạy script Python (tự động tạo zip và upload)
python upload_source.py
```

**Hoặc dùng gsutil CLI:**

```powershell
# Option 1: Chạy PowerShell as Administrator
# Sau đó chạy:
cd D:\Nhadat\cloud-function

# Tạo zip file chứa source code
Compress-Archive -Path *.py,requirements.txt -DestinationPath ..\cf-src.zip

# Tạo bucket cho source code (nếu chưa có)
gsutil mb -p etl-gcp-200412 -l asia-southeast1 gs://etl-gcp-200412-cf-src

# Upload zip
gsutil cp ..\cf-src.zip gs://etl-gcp-200412-cf-src/cf-src.zip
```

**Lưu ý:** Source code location sẽ là: `gs://etl-gcp-200412-cf-src/cf-src.zip`

## 4. Tạo Cloud Run Service

Xem hướng dẫn chi tiết trong **README.md** - Bước 6.

Tóm tắt:
1. Truy cập: https://console.cloud.google.com/run?project=etl-gcp-200412
2. Click **"Create Service"**
3. Cấu hình:
   - Container image: `asia-southeast1-docker.pkg.dev/etl-gcp-200412/etl-repo/crawler:latest`
   - Service name: `crawler-service`
   - Region: `asia-southeast1`
   - Environment variables:
     - `RAW_BUCKET` = `hanoi-bds-raw-data-final`
     - `SOURCE` = `mogi`
     - `MAX_PAGES` = `40` (số trang mỗi ngày, tùy chọn - mặc định 40)

## 5. Tạo Cloud Run Function (Cloud Functions Gen2)

Chi tiết xem trong **README.md** – Bước 8. Tóm tắt nhanh:

1. Mở `https://console.cloud.google.com/run/functions/list?project=etl-gcp-200412` (hoặc search "Cloud Run functions").
2. Chọn region `asia-southeast1` → bấm **Create function**.
3. Cấu hình:
   - Function name: `etl-cleaner`
   - Environment: `2nd gen`
   - Runtime: `Python 3.11`
   - Entry point: `main`
   - Source: `Cloud Storage archive` → `gs://etl-gcp-200412-cf-src/cf-src.zip`
   - Trigger: Cloud Storage → `Object finalized` từ bucket `hanoi-bds-raw-data-final`
   - Environment variables: `RAW_BUCKET`, `CLEAN_BUCKET`, `DATASET_ID`, `TABLE_ID`
4. Service account cần ít nhất các quyền: `Storage Object Admin`, `BigQuery Data Editor`, `Logs Writer`. Nếu Console cảnh báo quyền Eventarc/PubSub, bấm **Grant**.
5. Deploy và đợi trạng thái `Active`.

> CLI tương đương:
> ```powershell
> gcloud functions deploy etl-cleaner `
>   --gen2 --region=asia-southeast1 --runtime=python311 `
>   --source=gs://etl-gcp-200412-cf-src/cf-src.zip `
>   --entry-point=main `
>   --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" `
>   --trigger-event-filters="bucket=hanoi-bds-raw-data-final" `
>   --set-env-vars="RAW_BUCKET=hanoi-bds-raw-data-final,CLEAN_BUCKET=hanoi-bds-clean-data-final,DATASET_ID=hanoi_real_estate,TABLE_ID=properties"
> ```

## 6. (Tùy chọn) Cloud Composer

Composer là tùy chọn. Khuyến nghị triển khai sau khi các phần còn lại ổn định.

Xem hướng dẫn chi tiết trong **README.md** - Bước 9.

## 7. Test Pipeline

### Test Cloud Run Crawler

```powershell
# Lấy Cloud Run URL từ GCP Console
# Truy cập: https://console.cloud.google.com/run?project=etl-gcp-200412
# Copy URL từ service details (ví dụ: https://crawler-service-xxxxx-as.a.run.app)

$CLOUD_RUN_URL = "https://crawler-service-xxxxx-as.a.run.app"

# Trigger crawler
Invoke-WebRequest -Uri "$CLOUD_RUN_URL?raw_bucket=hanoi-bds-raw-data-final" -Method POST
```

### Test Cloud Function

Upload một file test vào raw bucket:

```powershell
# Tạo file test
echo '{"url":"https://mogi.vn/test","price":"2 tỷ","address":"Hà Nội"}' | Out-File -Encoding utf8 test.jsonl

# Upload
gsutil cp test.jsonl gs://hanoi-bds-raw-data-final/source=mogi/dt=2024-01-15/test.jsonl
```

Cloud Function sẽ tự động trigger và xử lý file này.

## 8. Demo theo các "Cốt lõi"

### Cốt lõi 1: Cloud Computing Core
- **Serverless Architecture**: Tất cả services tự động scale, không cần quản lý infrastructure
- **Show**: Có thể dùng `gcloud` commands để tạo và quản lý resources
- **Giải thích**: Cloud-native approach với managed services

### Cốt lõi 2: Elastic Compute & Serverless
- **Cloud Run**: 
  - Show logs, metrics trong Cloud Console
  - Giải thích: Tự động scale based on traffic, scale to zero
- **Cloud Function**: 
  - Upload file test → xem logs → thấy function tự động trigger và scale
  - Giải thích: Event-driven, serverless

### Cốt lõi 3: Managed Services (PaaS)
- **BigQuery**: 
  - Chạy query mẫu trên dataset
  - Giải thích: Serverless data warehouse, không cần quản lý cluster
- **Cloud Composer** (tùy chọn): 
  - Mở Airflow UI, show DAG graph
  - Giải thích: Managed Airflow, tự động scale

### Cốt lõi 4: Accessibility & Observability (SaaS)
- **Looker Studio**: 
  - Tạo dashboard kết nối BigQuery → share link cho end-user
  - Giải thích: SaaS, truy cập qua web, không cần cài đặt
- **Cloud Monitoring**: 
  - Show metrics, tạo alert mẫu cho error rate hoặc latency
  - Giải thích: Observability và monitoring tích hợp

## Troubleshooting

### Lỗi Cloud Run không deploy được
- Kiểm tra image đã push chưa: 
  ```powershell
  gcloud artifacts docker images list asia-southeast1-docker.pkg.dev/etl-gcp-200412/etl-repo/crawler
  ```
- Kiểm tra IAM permissions cho service account: https://console.cloud.google.com/iam-admin/iam?project=etl-gcp-200412

### Lỗi Cloud Function không trigger
- Kiểm tra Eventarc trigger đã tạo: 
  ```powershell
  gcloud eventarc triggers list --location=asia-southeast1
  ```
- Kiểm tra service account có quyền đọc GCS và write BigQuery
- Nếu báo Eventarc service agent thiếu quyền: gán role
  ```powershell
  $PROJECT_NUMBER = (gcloud projects describe etl-gcp-200412 --format="value(projectNumber)")
  gcloud projects add-iam-policy-binding etl-gcp-200412 `
    --member="serviceAccount:service-$PROJECT_NUMBER@gcp-sa-eventarc.iam.gserviceaccount.com" `
    --role="roles/eventarc.serviceAgent"
  ```

### Lỗi BigQuery insert
- Kiểm tra schema match với data
- Kiểm tra service account có quyền `roles/bigquery.dataEditor`

---

**Xem thêm:** 
- **README.md**: Hướng dẫn chi tiết triển khai qua GCP Console UI
- **FULL_CHECKLIST.md**: Checklist đầy đủ từ đầu đến cuối
