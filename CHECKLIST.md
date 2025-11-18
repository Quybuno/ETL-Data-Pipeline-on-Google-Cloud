# ✅ Checklist Triển Khai Project

## 📋 Các Bước Cần Làm (Theo Thứ Tự)

### ✅ 1. Đã Hoàn Thành:
- [x] Enable APIs trên GCP Console
- [x] Tạo BigQuery dataset và table (dùng Python script)

### 🔄 2. Đang Cần Làm:

#### **Bước 1: Build và Push Docker Image**
```powershell
cd D:\Nhadat\cloud-run

# Cấu hình Docker auth
gcloud auth configure-docker asia-southeast1-docker.pkg.dev --quiet

# Build image
docker build -t "asia-southeast1-docker.pkg.dev/etl-gcp-200501/etl-repo/crawler:latest" .

# Push image
docker push "asia-southeast1-docker.pkg.dev/etl-gcp-200501/etl-repo/crawler:latest"
```
⚠️ **Quan trọng:** Phải push image TRƯỚC khi tạo Cloud Run service!

---

#### **Bước 2: Package và Upload Cloud Function Source**
```powershell
cd D:\Nhadat\cloud-function
pip install google-cloud-storage
python upload_source.py
```

---

#### **Bước 3: Tạo Infrastructure qua GCP Console**

Thực hiện theo hướng dẫn trong **README.md**:

1. **Tạo Cloud Storage Buckets** (Bước 2):
   - `hanoi-bds-raw-data-final`
   - `hanoi-bds-clean-data-final`
   - `etl-gcp-200412-cf-src`

2. **Tạo Artifact Registry Repository** (Bước 4):
   - Name: `etl-repo`
   - Format: Docker
   - Location: `asia-southeast1`

3. **Tạo Cloud Run Service** (Bước 6):
   - Service name: `crawler-service`
   - Image: `asia-southeast1-docker.pkg.dev/etl-gcp-200412/etl-repo/crawler:latest`
   - Environment variables:
     - `RAW_BUCKET` = `hanoi-bds-raw-data-final`
     - `SOURCE` = `mogi`
     - `MAX_PAGES` = `40`

4. **Tạo Cloud Run Function (Gen2)** (Bước 8 trong README):
   - Truy cập mục **Cloud Run → Functions** (search “Cloud Run functions”), chọn region `asia-southeast1`
   - Function name: `etl-cleaner`
   - Runtime: `Python 3.11`, Entry point: `main`
   - Source: `gs://etl-gcp-200412-cf-src/cf-src.zip`
   - Trigger: Cloud Storage → Object finalized từ `hanoi-bds-raw-data-final`
   - Env vars: `RAW_BUCKET`, `CLEAN_BUCKET`, `DATASET_ID`, `TABLE_ID`
   - **Airflow Variable (Composer)**: tạo `cloud_run_crawler_url` = URL Cloud Run crawler

---

#### **Bước 4: Test Pipeline**
```powershell
# Lấy Cloud Run URL từ GCP Console
# Truy cập: https://console.cloud.google.com/run?project=etl-gcp-200412
# Copy URL từ service details

$CLOUD_RUN_URL = "https://crawler-service-xxxxx-as.a.run.app"

# Test crawler (trigger qua HTTP)
Invoke-WebRequest -Uri "$CLOUD_RUN_URL?raw_bucket=hanoi-bds-raw-data-final" -Method POST
```

---

### 📝 Lưu ý:
1. **Composer** sẽ tốn chi phí và mất 20-30 phút để tạo (tùy chọn)
2. Đảm bảo **Docker Desktop đang chạy** trước khi build image
3. Nếu bucket name bị conflict → đổi tên khác hoặc dùng bucket đã có
4. Image phải được **push trước** khi tạo Cloud Run service

---

### 🎯 Tóm Tắt Ngắn Gọn:
1. Push Docker image → 2. Upload CF source → 3. Tạo resources qua GCP Console → 4. Test

---

### 📚 Tài Liệu Tham Khảo:
- **README.md**: Hướng dẫn chi tiết triển khai qua GCP Console UI
- **DEPLOYMENT.md**: Hướng dẫn manual deployment
- **FULL_CHECKLIST.md**: Checklist đầy đủ từ đầu đến cuối
