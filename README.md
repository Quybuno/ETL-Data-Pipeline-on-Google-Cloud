

- Cấp quyền & APIs: xem `SETUP_GCP_PERMISSIONS.md`
- Hướng dẫn Looker Studio: `analysis/LOOKER_STUDIO_STEP_BY_STEP.md`
- Kiến trúc: `architecture_diagram.md`
- Hướng dẫn sau Terraform: `DEPLOYMENT.md`

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
$PROJECT="etl-gcp-200501"
gcloud config set project $PROJECT
```

- Bật các API cần thiết (nếu chưa): xem `SETUP_GCP_PERMISSIONS.md` mục Enable Required APIs.
- Bật Docker Desktop (nếu build image local cho Cloud Run).

---

## 2) Khởi tạo hạ tầng bằng Terraform (IaC)

```powershell
cd D:\Nhadat\terraform
# Kiểm tra biến trong terraform.tfvars (region, repo, tên buckets, dataset, v.v.)
terraform init
terraform plan
terraform apply -auto-approve
```

Kết quả: Artifact Registry repo, Cloud Storage buckets (raw/clean), BigQuery dataset, Cloud Run/Function scaffolding, Composer (nếu khai báo), IAM bindings.

Lưu ý: Khuyến nghị cấu hình Remote State (GCS backend) cho Terraform trong lần sau.

---

## 3) Build & Push Docker image cho Cloud Run (Crawler)

Thực hiện theo `DEPLOYMENT.md` hoặc chạy nhanh như sau:

```powershell
cd D:\Nhadat\cloud-run
$REGION = "asia-southeast1"
$PROJECT = "etl-gcp-200501"
$REPO    = "etl-repo"
$IMAGE   = "crawler"

# Đăng nhập Docker với Artifact Registry
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet

# Build
docker build -t "$REGION-docker.pkg.dev/$PROJECT/$REPO/$IMAGE:latest" .

# Push
docker push "$REGION-docker.pkg.dev/$PROJECT/$REPO/$IMAGE:latest"
```

Cập nhật `terraform.tfvars` để Cloud Run dùng image mới:

```hcl
crawler_image = "asia-southeast1-docker.pkg.dev/etl-gcp-200501/etl-repo/crawler:latest"
```

Áp dụng lại:

```powershell
cd D:\Nhadat\terraform
terraform apply -auto-approve
```

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

Cập nhật `terraform.tfvars` khớp bucket/object nguồn:

```hcl
cf_source_bucket = "etl-gcp-200501-cf-src"
cf_source_object = "cf-src.zip"
```

Đặt environment variables cho Cloud Function:

```hcl
cf_env = {
  RAW_BUCKET   = "hanoi-bds-raw-data"
  CLEAN_BUCKET = "hanoi-bds-clean-data"
  DATASET_ID   = "hanoi_real_estate"
  TABLE_ID     = "properties"
}
```

Áp dụng lại Terraform:

```powershell
cd D:\Nhadat\terraform
terraform apply -auto-approve
```

---

## 6) Tạo và triển khai DAG lên Cloud Composer 3 (tuỳ chọn)

1. Bật API (nếu chưa):
```powershell
gcloud config set project etl-gcp-200401
gcloud services enable composer.googleapis.com container.googleapis.com compute.googleapis.com
```

2. Tạo Composer 3 (mất ~15–30 phút, có chi phí):
```powershell
gcloud composer environments create etl-orchestrator `
  --location=asia-southeast1 `
  --image-version=composer-3-airflow-2
```

3. Lấy thông tin và DAG bucket:
```powershell
gcloud composer environments describe etl-orchestrator --location asia-southeast1
# Ghi lại giá trị dag_gcs_prefix (ví dụ: gs://us-central1-etl-orchestrator-xxxx-bucket/dags)
```

4. Copy DAG lên bucket Composer:
```powershell
$DAG_BUCKET_PATH="gs://<DAG_BUCKET>/dags"   # thay bằng dag_gcs_prefix (bỏ phần /dags nếu đã có)
gsutil cp D:\Nhadat\airflow\dags\etl_pipeline.py $DAG_BUCKET_PATH/etl_pipeline.py
```

5. Mở Airflow UI (từ output của bước describe), bật DAG và chạy thử; xem Logs trong Airflow.

---

## 7) Kiểm thử end-to-end

- Lấy URL Cloud Run từ Terraform output và trigger crawler:

```powershell
cd D:\Nhadat\terraform
$CLOUD_RUN_URL = (terraform output -raw cloud_run_url)
# Trigger (ví dụ):
curl -X POST "$CLOUD_RUN_URL?raw_bucket=hanoi-bds-raw-data"
```

- Test Cloud Function bằng cách upload 1 file mẫu:

```powershell
cd D:\Nhadat
"{""url"":""https://mogi.vn/test"",""price"":""2 tỷ"",""address"":""Hà Nội""}" | Out-File -Encoding utf8 test.jsonl
ps: gsutil cp test.jsonl gs://hanoi-bds-raw-data/source=mogi/dt=2024-01-15/test.jsonl
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
- IaC bằng Terraform, có thể destroy/apply tái tạo toàn bộ
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
$PROJECT = "etl-gcp-200501"
$REGION  = "asia-southeast1"
$REPO    = "etl-repo"
$IMAGE   = "crawler"
```

(Terraform apply, Artifact Registry, Cloud Run revision, BigQuery rows, Airflow DAG, Looker dashboard, Monitoring charts).


