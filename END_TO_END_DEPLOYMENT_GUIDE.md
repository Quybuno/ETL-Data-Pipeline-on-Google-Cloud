# 🚀 Triển khai End-to-End trên GCP cho dự án Nhadat

Tài liệu này hướng dẫn từng bước triển khai toàn bộ hệ thống theo kiến trúc cloud-native, phù hợp tiêu chí “đúng core” cho bài tiểu luận Cloud Computing.

Liên quan:
- Cấp quyền & APIs: xem `SETUP_GCP_PERMISSIONS.md`
- Hướng dẫn Looker Studio: `analysis/LOOKER_STUDIO_STEP_BY_STEP.md`
- Kiến trúc: `architecture_diagram.md`
- Hướng dẫn deployment manual: `DEPLOYMENT.md`
- Hướng dẫn triển khai qua UI: `README.md`

---

## 1) Chuẩn bị môi trường

- Cài Google Cloud SDK trên Windows (PowerShell).
- Đăng nhập và chọn Project:

```powershell
# Đăng nhập
gcloud auth login
# Application Default (cho SDK/clients)
gcloud auth application-default login
# Chọn project
$PROJECT="etl-gp-200501"
gcloud config set project $PROJECT
```

- Bật các API cần thiết (nếu chưa): xem `SETUP_GCP_PERMISSIONS.md` mục Enable Required APIs.
- Bật Docker Desktop (nếu build image local cho Cloud Run).

---

## 2) Tạo Infrastructure qua GCP Console

Thực hiện theo hướng dẫn trong **README.md** để tạo các resources sau qua GCP Console UI:

1. **Cloud Storage Buckets**: 
   - `hanoi-bds-raw-data-f` (raw data)
   - `hanoi-bds-clean-data-f` (clean data)
   - `etl-gp-200501-cf-src` (Cloud Function source code)

2. **Artifact Registry Repository**: 
   - `etl-repo` (Docker images)

3. **BigQuery Dataset**: 
   - `hanoi_real_estate` (region: asia-southeast1)

Xem chi tiết từng bước trong **README.md** - Bước 2, 3, 4.

---

## 3) Build & Push Docker image cho Cloud Run (Crawler)

Thực hiện theo `DEPLOYMENT.md` hoặc chạy nhanh như sau:

```powershell
# Bước 1: Chuyển đến thư mục cloud-run (QUAN TRỌNG)
cd D:\Nhadat\cloud-run
$REGION = "asia-southeast1"
$PROJECT = "etl-gp-200501"
$REPO    = "etl-repo"
$IMAGE   = "crawler"

# Bước 4: Đăng nhập Docker với Artifact Registry
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# Bước 5: Build (QUAN TRỌNG: phải có $IMAGE:latest ở cuối tag)
# Dấu chấm (.) ở cuối nghĩa là build từ thư mục hiện tại
docker build -t "${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${IMAGE}:latest" .

# Bước 6: Push
docker push "${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${IMAGE}:latest"
```

**Lưu ý:** 
- Image URL phải đầy đủ: `asia-southeast1-docker.pkg.dev/etl-gp-200501/etl-repo/crawler:latest`
- Phải chạy lệnh từ thư mục `D:\Nhadat\cloud-run` (nơi có Dockerfile)
- Dấu chấm (`.`) ở cuối lệnh `docker build` là bắt buộc - nó chỉ định build context là thư mục hiện tại

**Troubleshooting:**
- Lỗi "no such file or directory" → Kiểm tra đã `cd D:\Nhadat\cloud-run` chưa
- Lỗi "invalid tag" → Kiểm tra đã set đủ biến: `$REGION`, `$PROJECT`, `$REPO`, `$IMAGE`
- Tag phải kết thúc bằng `/${IMAGE}:latest` (ví dụ: `/crawler:latest`)

Sử dụng image URL này khi tạo Cloud Run service trong GCP Console (xem **README.md** - Bước 6).

---

## 4) Tạo BigQuery dataset/table

Có 3 cách, khuyến nghị dùng Python:

```powershell
cd D:\Nhadat\bigquery
pip install google-cloud-bigquery
python create_table.py
```

Hoặc Web UI: tạo dataset `hanoi_real_estate` (region: asia-southeast1), sau đó chạy `schema.sql`.

Hoặc bq CLI (xem `DEPLOYMENT.md`).

---

## 5) Package & Upload Cloud Function source

Dùng script có sẵn:

```powershell
cd D:\Nhadat\cloud-function
pip install google-cloud-storage
python upload_source.py
```


Source code location sẽ là: `gs://etl-gp-200501-cf-src/cf-src.zip`

Sử dụng path này khi tạo Cloud Function trong GCP Console. Đặt environment variables:
- `RAW_BUCKET` = `hanoi-bds-raw-data-f`
- `CLEAN_BUCKET` = `hanoi-bds-clean-data-f`
- `DATASET_ID` = `hanoi_real_estate`
- `TABLE_ID` = `properties`

> **Lưu ý:** Trên Console, Cloud Functions Gen2 nằm trong mục **Cloud Run → Fimage.pngnctions** (tên mới: *Cloud Run functions*). Làm theo Bước 8 trong `README.md` để tạo function `etl-cleaner` với entry point `main` hoặc deploy bằng CLI.

Xem chi tiết trong **README.md** - Bước 8.

---

## 6) Tạo và triển khai DAG lên Cloud Composer 3

**⚠️ Lưu ý:** Cloud Composer tốn chi phí (~$0.10-0.50/giờ) và mất 15-30 phút để tạo environment.

### 6.1. Bật API (nếu chưa)

```powershell
$PROJECT = "etl-gp-200501"
gcloud config set project $PROJECT
gcloud services enable composer.googleapis.com container.googleapis.com compute.googleapis.com
```

### 6.2. Tạo Composer 3 Environment

```powershell
$PROJECT = "etl-gp-200501"
$REGION = "asia-southeast1"
$ENV_NAME = "etl-orchestrator"

# Tạo Composer environment (mất ~15-30 phút)
gcloud composer environments create $ENV_NAME `
  --location=$REGION `
  --project=$PROJECT `
  --image-version=composer-3-airflow-2
```

**Lưu ý:** 
- Quá trình tạo mất 15-30 phút, đợi đến khi status = RUNNING
- Có thể kiểm tra status: `gcloud composer environments describe $ENV_NAME --location=$REGION`

### 6.3. Lấy thông tin DAG bucket

Sau khi environment ready, lấy DAG bucket path:

```powershell
$ENV_NAME = "etl-orchestrator"
$REGION = "asia-southeast1"

# Lấy thông tin environment
gcloud composer environments describe $ENV_NAME --location=$REGION

# Tìm dòng "dagGcsPrefix" trong output (ví dụ: gs://asia-southeast1-etl-orchestrator-xxxx-bucket/dags)
# Hoặc lấy trực tiếp:
$DAG_PREFIX = (gcloud composer environments describe $ENV_NAME --location=$REGION --format="value(config.dagGcsPrefix)")
Write-Host "DAG bucket path: $DAG_PREFIX"
```

### 6.4. Upload DAG file

```powershell
# Thay <DAG_BUCKET> bằng giá trị từ bước trên (ví dụ: asia-southeast1-etl-orchestrator-xxxx-bucket)
$DAG_BUCKET = "<DAG_BUCKET>"  # Chỉ tên bucket, không có gs://
gsutil cp D:\Nhadat\airflow\dags\etl_pipeline.py "gs://$DAG_BUCKET/dags/etl_pipeline.py"
```

**Hoặc dùng DAG_PREFIX từ bước trên:**
```powershell
$DAG_PREFIX = (gcloud composer environments describe $ENV_NAME --location=$REGION --format="value(config.dagGcsPrefix)")
gsutil cp D:\Nhadat\airflow\dags\etl_pipeline.py "$DAG_PREFIX/etl_pipeline.py"
```

### 6.5. Thiết lập Cloud Run URL cho Airflow

- Mở Airflow UI → **Admin → Variables** → thêm biến
  - Key: `cloud_run_crawler_url`
  - Value: URL Cloud Run `crawler-service` (ví dụ: `https://crawler-service-xxxxx-as.a.run.app`)
- Hoặc dùng CLI:
  ```powershell
  gcloud composer environments run $ENV_NAME --location=$REGION variables -- `
    set cloud_run_crawler_url "https://crawler-service-xxxxx-as.a.run.app"
  ```

### 6.6. Truy cập Airflow UI và test DAG

1. **Lấy Airflow UI URL:**
```powershell
$ENV_NAME = "etl-orchestrator"
$REGION = "asia-southeast1"
gcloud composer environments describe $ENV_NAME --location=$REGION --format="value(config.airflowUri)"
```

2. **Mở Airflow UI:**
   - Copy URL từ output trên
   - Đăng nhập bằng Google account
   - Tìm DAG `hanoi_real_estate_etl`
   - Toggle DAG sang ON (bật)
   - Click "Trigger DAG" để test

3. **Kiểm tra logs:**
   - Click vào DAG → Graph View để xem workflow
   - Click vào task để xem logs chi tiết

### 6.7. Cấu hình DAG (nếu cần)

DAG đã được cấu hình để:
- Chạy hàng ngày lúc 2h sáng (`schedule_interval='0 2 * * *'`)
- Trigger Cloud Run service `crawler-service`
- Đợi file xuất hiện trong raw bucket
- Project ID đã được set: `etl-gp-200501`

Nếu cần thay đổi, sửa file `D:\Nhadat\airflow\dags\etl_pipeline.py` và upload lại.

---

## 7) Kiểm thử end-to-end

- Lấy URL Cloud Run từ GCP Console và trigger crawler:

```powershell
# Lấy URL từ GCP Console: https://console.cloud.google.com/run?project=etl-gp-200501
# Copy URL từ service details (ví dụ: https://crawler-service-xxxxx-as.a.run.app)
$CLOUD_RUN_URL = "https://crawler-service-xxxxx-as.a.run.app"
# Trigger:
Invoke-WebRequest -Uri "$CLOUD_RUN_URL?raw_bucket=hanoi-bds-raw-data-f" -Method POST
```

- Test Cloud Function bằng cách upload 1 file mẫu:

```powershell
cd D:\Nhadat
"{""url"":""https://mogi.vn/test"",""price"":""2 tỷ"",""address"":""Hà Nội""}" | Out-File -Encoding utf8 test.jsonl
ps: gsutil cp test.jsonl gs://hanoi-bds-raw-data-f/source=mogi/dt=2024-01-15/test.jsonl
```

- Kiểm tra logs/metrics:
  - Cloud Run & Cloud Function: Cloud Logging
  - BigQuery: xác nhận dữ liệu vào bảng

---

## 8) Dashboard Looker Studio

Làm theo hướng dẫn chi tiết tại: `analysis/LOOKER_STUDIO_STEP_BY_STEP.md`.
- Kết nối đến BigQuery dataset `hanoi_real_estate`
- Tạo biểu đồ, bộ lọc khu vực/giá, chia sẻ liên kết trình bày

---

## 9) Quan sát (Monitoring) & Cảnh báo (tuỳ chọn)

- Tạo dashboard Metrics: request count, latency p95, error rate cho Cloud Run/Function.
- Tạo Alerting Policy (VD: error rate > 5% trong 5 phút): Cloud Monitoring → Alerting.
- Ghi lại SLI/SLO đề xuất (VD: SLO 99.9% cho Cloud Run).

---

## 10) CI/CD (tuỳ chọn nhanh)

Dùng Cloud Build để build & deploy mỗi khi push:

```yaml
# cloudbuild.yaml (đặt ở root hoặc cloud-run/ và chỉnh lại đường dẫn)
steps:
  - name: gcr.io/cloud-builders/docker
    args: ['build','-t','$REGION-docker.pkg.dev/$PROJECT/$REPO/$IMAGE:$COMMIT_SHA','cloud-run']
  - name: gcr.io/cloud-builders/docker
    args: ['push','$REGION-docker.pkg.dev/$PROJECT/$REPO/$IMAGE:$COMMIT_SHA']
  - name: gcr.io/google.com/cloudsdktool/cloud-sdk
    entrypoint: gcloud
    args: [
      'run','deploy','crawler-service',
      '--image','$REGION-docker.pkg.dev/$PROJECT/$REPO/$IMAGE:$COMMIT_SHA',
      '--region','$REGION','--platform','managed','--allow-unauthenticated'
    ]
substitutions:
  _SERVICE: crawler-service
  _IMAGE: crawler
  _REPO: etl-repo
  _REGION: asia-southeast1
images:
  - "$REGION-docker.pkg.dev/$PROJECT/$REPO/$IMAGE:$COMMIT_SHA"
```

Thiết lập Trigger trong Cloud Build theo branch `main`.

---

## 11) Checklist “đúng core” khi bảo vệ

- Kiến trúc cloud-native: Cloud Run + Cloud Function + GCS + BigQuery (+ Composer)
- Cloud Computing Core: Serverless architecture, managed services, auto-scaling
- Bảo mật/IAM: tách bạch service accounts, chỉ quyền cần thiết
- Secrets (nếu có) dùng Secret Manager (khuyến nghị nêu rõ)
- Autoscaling & Serverless billing (Cloud Run/Function)
- Quan sát: Logs + Metrics + (tuỳ chọn) Alerting; nêu SLI/SLO/SLA
- Hiệu năng/Chi phí: concurrency, CPU/memory, partitioning BigQuery (nếu phù hợp)
- BI: Dashboard Looker Studio kết nối BigQuery
- Quy trình: Tài liệu hoá đầy đủ, có CI/CD (tuỳ chọn)

---

## 12) Troubleshooting nhanh

- Cloud Run không deploy: kiểm tra image đã push, quyền Artifact Registry.
- Cloud Function không trigger: kiểm tra Eventarc trigger, quyền đọc GCS/ghi BigQuery.
- BigQuery insert lỗi: đối chiếu schema và kiểm tra roles `bigquery.dataEditor`.
- Thiếu quyền/Thiếu API: xem `SETUP_GCP_PERMISSIONS.md`.

---

## Phụ lục: Biến thường dùng

```powershell
$PROJECT = "etl-gp-200501"
$REGION  = "asia-southeast1"
$REPO    = "etl-repo"
$IMAGE   = "crawler"
```

> Gợi ý trình bày: chụp màn hình mỗi bước (GCP Console resources, Artifact Registry, Cloud Run revision, BigQuery rows, Airflow DAG, Looker dashboard, Monitoring charts).


