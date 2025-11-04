# ✅ Checklist Triển Khai Project

## 📋 Các Bước Cần Làm (Theo Thứ Tự)

### ✅ 1. Đã Hoàn Thành:
- [x] Enable APIs trên GCP Console
- [x] Tạo BigQuery dataset và table (dùng Python script)
- [x] Terraform đã tạo Artifact Registry repository (`etl-repo`)

### 🔄 2. Đang Cần Làm:

#### **Bước 1: Import Resources Đã Tồn Tại vào Terraform**
```powershell
cd D:\Nhadat\terraform
terraform import google_bigquery_dataset.dataset projects/etl-gcp-200501/datasets/hanoi_real_estate
```

**Nếu bucket đã tồn tại, import:**
```powershell
terraform import google_storage_bucket.raw_bucket hanoi-bds-raw-data
terraform import google_storage_bucket.clean_bucket hanoi-bds-clean-data
```
**Hoặc nếu muốn tạo mới, đổi tên trong `terraform.tfvars`**

---

#### **Bước 2: Build và Push Docker Image**
```powershell
cd D:\Nhadat\cloud-run
docker build -t "asia-southeast1-docker.pkg.dev/etl-gcp-200501/etl-repo/crawler:latest" .
docker push "asia-southeast1-docker.pkg.dev/etl-gcp-200501/etl-repo/crawler:latest"
```
⚠️ **Quan trọng:** Phải push image TRƯỚC khi chạy terraform apply để tạo Cloud Run!

---

#### **Bước 3: Package và Upload Cloud Function Source**
```powershell
cd D:\Nhadat\cloud-function
pip install google-cloud-storage
python upload_source.py
```

---

#### **Bước 4: Cập nhật terraform.tfvars (nếu chưa có)**
Mở `D:\Nhadat\terraform\terraform.tfvars` và đảm bảo có:
```hcl
cf_env = {
  RAW_BUCKET    = "hanoi-bds-raw-data"
  CLEAN_BUCKET  = "hanoi-bds-clean-data"
  DATASET_ID    = "hanoi_real_estate"
  TABLE_ID      = "properties"
}
```

---

#### **Bước 5: Chạy Terraform Apply**
```powershell
cd D:\Nhadat\terraform
terraform apply
```

---

#### **Bước 6: Test Pipeline**
```powershell
# Lấy Cloud Run URL
cd D:\Nhadat\terraform
terraform output cloud_run_url

# Test crawler (trigger qua HTTP)
curl -X POST "<CLOUD_RUN_URL>?raw_bucket=hanoi-bds-raw-data"
```

---

### 📝 Lưu Ý:
1. **Composer** sẽ tốn chi phí và mất 20-30 phút để tạo
2. Đảm bảo **Docker Desktop đang chạy** trước khi build image
3. Nếu bucket name bị conflict → đổi tên trong `terraform.tfvars` hoặc import bucket đã có
4. Image phải được **push trước** khi terraform tạo Cloud Run service

---

### 🎯 Tóm Tắt Ngắn Gọn:
1. Import dataset → 2. Push Docker image → 3. Upload CF source → 4. Terraform apply → 5. Test

