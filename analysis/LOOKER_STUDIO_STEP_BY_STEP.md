# 🎯 Hướng Dẫn Tạo Dashboard Looker Studio - Từng Bước

## 📋 Bước 1: Kết Nối với BigQuery

### 1.1. Mở Looker Studio
1. Truy cập: **https://datastudio.google.com/**
2. Đăng nhập bằng Google account có quyền truy cập project `etl-gcp-200501`

### 1.2. Tạo Data Source Mới
1. Click **"Create"** (góc trên bên trái)
2. Chọn **"Data source"**

### 1.3. Chọn BigQuery Connector
1. Trong danh sách connectors, scroll xuống và tìm **"BigQuery"**
2. Click vào **"BigQuery"**

### 1.4. Kết Nối với Project
1. Chọn **"My projects"** tab
2. Tìm và chọn project: **`etl-gcp-200501`**
3. Expand project → chọn **`hanoi_real_estate`** dataset
4. Chọn table: **`properties`**
5. Click **"Connect"** (góc trên bên phải)

---

## 📊 Bước 2: Cấu Hình Data Source

### 2.1. Kiểm Tra Fields
Sau khi connect, bạn sẽ thấy danh sách các fields từ BigQuery table:
- ✅ Dimensions: `url`, `source`, `run_date`, `title`, `address`, `loai_hinh`, etc.
- ✅ Metrics: `price_billion_vnd`, `area_m2`

### 2.2. Tạo Calculated Fields (Quan Trọng!)

Click **"Add a field"** để tạo các calculated fields:

#### **Field 1: "Phân khúc giá"**
```
CASE
  WHEN price_billion_vnd < 2 THEN "Dưới 2 tỷ"
  WHEN price_billion_vnd >= 2 AND price_billion_vnd < 5 THEN "2-5 tỷ"
  WHEN price_billion_vnd >= 5 AND price_billion_vnd < 10 THEN "5-10 tỷ"
  WHEN price_billion_vnd >= 10 AND price_billion_vnd < 20 THEN "10-20 tỷ"
  WHEN price_billion_vnd >= 20 THEN "Trên 20 tỷ"
  ELSE "Không xác định"
END
```
- Type: **Text**

#### **Field 2: "Phân khúc diện tích"**
```
CASE
  WHEN area_m2 < 50 THEN "Dưới 50m²"
  WHEN area_m2 >= 50 AND area_m2 < 70 THEN "50-70m²"
  WHEN area_m2 >= 70 AND area_m2 < 100 THEN "70-100m²"
  WHEN area_m2 >= 100 AND area_m2 < 150 THEN "100-150m²"
  WHEN area_m2 >= 150 THEN "Trên 150m²"
  ELSE "Không xác định"
END
```
- Type: **Text**

#### **Field 3: "Giá trên m² (triệu VNĐ)"**
```
SAFE_DIVIDE(price_billion_vnd, area_m2) * 1000
```
- Type: **Number**
- Aggregation: **Average**

#### **Field 4: "Quận/Huyện" (Extract từ address)**
```
CASE
  WHEN REGEXP_CONTAINS(address, r'Cầu Giấy') THEN "Cầu Giấy"
  WHEN REGEXP_CONTAINS(address, r'Đống Đa') THEN "Đống Đa"
  WHEN REGEXP_CONTAINS(address, r'Hai Bà Trưng') THEN "Hai Bà Trưng"
  WHEN REGEXP_CONTAINS(address, r'Ba Đình') THEN "Ba Đình"
  WHEN REGEXP_CONTAINS(address, r'Hoàn Kiếm') THEN "Hoàn Kiếm"
  WHEN REGEXP_CONTAINS(address, r'Tây Hồ') THEN "Tây Hồ"
  WHEN REGEXP_CONTAINS(address, r'Thanh Xuân') THEN "Thanh Xuân"
  WHEN REGEXP_CONTAINS(address, r'Long Biên') THEN "Long Biên"
  WHEN REGEXP_CONTAINS(address, r'Nam Từ Liêm') THEN "Nam Từ Liêm"
  WHEN REGEXP_CONTAINS(address, r'Bắc Từ Liêm') THEN "Bắc Từ Liêm"
  WHEN REGEXP_CONTAINS(address, r'Hà Đông') THEN "Hà Đông"
  WHEN REGEXP_CONTAINS(address, r'Hoàng Mai') THEN "Hoàng Mai"
  ELSE "Khác"
END
```
- Type: **Text**

### 2.3. Đổi Tên Fields (Optional nhưng Recommended)
Click vào từng field để đổi tên cho dễ đọc:
- `price_billion_vnd` → **"Giá (tỷ VNĐ)"**
- `area_m2` → **"Diện tích (m²)"**
- `loai_hinh` → **"Loại hình"**
- `phap_ly` → **"Pháp lý"**
- `phong_ngu` → **"Số phòng ngủ"**
- `huong_nha` → **"Hướng nhà"**

### 2.4. Set Aggregation cho Metrics
- `price_billion_vnd`: **Average** (Giá trung bình)
- `area_m2`: **Average** (Diện tích trung bình)
- Tạo metric **"Số lượng tin đăng"**: `COUNT(url)` hoặc `COUNT_DISTINCT(url)`

### 2.5. Click **"Add to Report"** (hoặc "Create Report")

---

## 📈 Bước 3: Tạo Dashboard

### Trang 1: Tổng Quan (Overview)

#### **3.1. Scorecard Cards (Số liệu tổng quan)**
1. Thêm **Scorecard** từ menu bên phải
2. Tạo 3 scorecards:

**Card 1: Tổng số tin đăng**
- Metric: **"Số lượng tin đăng"** (COUNT)
- Label: "Tổng số tin đăng"

**Card 2: Giá trung bình**
- Metric: **"Giá (tỷ VNĐ)"** (Average)
- Label: "Giá trung bình"
- Format: Number → 2 decimals → Thêm " tỷ VNĐ"

**Card 3: Diện tích trung bình**
- Metric: **"Diện tích (m²)"** (Average)
- Label: "Diện tích trung bình"
- Format: Number → 0 decimals → Thêm " m²"

#### **3.2. Bar Chart - Phân bố theo loại hình**
1. Thêm **Bar chart** (horizontal bar)
2. Configuration:
   - Dimension: **"Loại hình"** (`loai_hinh`)
   - Metric: **"Số lượng tin đăng"**
   - Sort: Descending (Giảm dần)
   - Chart title: "Phân bố số lượng tin đăng theo loại hình"

#### **3.3. Time Series Chart - Xu hướng giá**
1. Thêm **Time series chart**
2. Configuration:
   - Dimension: **"run_date"** (Date)
   - Metric: **"Giá (tỷ VNĐ)"** (Average)
   - Date range: Last 30 days
   - Chart title: "Xu hướng giá theo thời gian"
   - Show: Line chart with markers

---

### Trang 2: Phân Tích Chi Tiết (Detailed Analysis)

#### **4.1. Table - Chi tiết giá theo loại hình**
1. Thêm **Table**
2. Configuration:
   - Dimensions: **"Loại hình"**
   - Metrics:
     - **"Số lượng tin đăng"** (COUNT)
     - **"Giá (tỷ VNĐ)"** (Average) → Format: 2 decimals
     - **"Diện tích (m²)"** (Average) → Format: 0 decimals
     - **"Giá trên m² (triệu VNĐ)"** (Average) → Format: 2 decimals
   - Sort by: Số lượng (Descending)
   - Chart title: "Chi tiết giá và diện tích theo loại hình"

#### **4.2. Pie Chart - Phân khúc giá**
1. Thêm **Pie chart**
2. Configuration:
   - Dimension: **"Phân khúc giá"** (calculated field)
   - Metric: **"Số lượng tin đăng"**
   - Chart title: "Phân bố theo phân khúc giá"
   - Show percentage: Yes

#### **4.3. Bar Chart - Top 10 quận/huyện**
1. Thêm **Bar chart** (horizontal)
2. Configuration:
   - Dimension: **"Quận/Huyện"** (calculated field)
   - Metric: **"Số lượng tin đăng"**
   - Filter: Top 10
   - Sort: Descending
   - Chart title: "Top 10 quận/huyện có nhiều tin đăng nhất"

---

### Trang 3: Bản Đồ và Phân Tích Địa Lý

#### **5.1. Geo Chart**
1. Thêm **Geo chart**
2. Configuration:
   - Dimension: **"address"** (Geographic → City)
   - Metric: **"Số lượng tin đăng"**
   - Color by: **"Giá (tỷ VNĐ)"** (Average)
   - Chart title: "Phân bố tin đăng theo địa điểm"

---

### Trang 4: So Sánh và Phân Tích Nâng Cao

#### **6.1. Scatter Chart - Mối quan hệ giá và diện tích**
1. Thêm **Scatter chart**
2. Configuration:
   - X-axis: **"Diện tích (m²)"** (Average)
   - Y-axis: **"Giá (tỷ VNĐ)"** (Average)
   - Color: **"Loại hình"**
   - Size: **"Số lượng tin đăng"**
   - Chart title: "Mối quan hệ giữa giá và diện tích"

#### **6.2. Table - So sánh giá/m²**
1. Thêm **Table**
2. Configuration:
   - Dimension: **"Loại hình"**
   - Metrics:
     - **"Giá trên m² (triệu VNĐ)"** (Average)
     - **"Số lượng tin đăng"**
   - Sort by: Giá trên m² (Descending)
   - Chart title: "So sánh giá trên m² theo loại hình"

---

## 🎛️ Bước 4: Tạo Filters (Bộ Lọc)

### 4.1. Date Range Filter
1. Thêm **Date range control**
2. Configuration:
   - Dimension: **"run_date"** (Date)
   - Default range: Last 30 days
   - Position: Top of report

### 4.2. Dropdown Filter - Loại hình
1. Thêm **Dropdown filter**
2. Configuration:
   - Dimension: **"Loại hình"**
   - Allow multiple selection: Yes
   - Position: Top of report

### 4.3. Slider Filter - Giá
1. Thêm **Slider control** (Numeric range)
2. Configuration:
   - Metric: **"Giá (tỷ VNĐ)"**
   - Min: 0
   - Max: 100 (hoặc MAX trong data)
   - Position: Top of report

### 4.4. Filter - Quận/Huyện
1. Thêm **Dropdown filter**
2. Configuration:
   - Dimension: **"Quận/Huyện"** (calculated field)
   - Allow multiple selection: Yes

---

## 🎨 Bước 5: Styling & Formatting

### 5.1. Theme & Colors
1. Click **"Theme and layout"** (menu bên phải)
2. Chọn theme: **"Modern"** hoặc **"Classic"**
3. Customize colors:
   - Primary color: Blue (#1a73e8)
   - Secondary color: Green (#34a853)
   - Background: White or Light gray

### 5.2. Number Formatting
- **Giá:** Number → 2 decimals → Suffix: " tỷ VNĐ"
- **Diện tích:** Number → 0 decimals → Suffix: " m²"
- **Giá trên m²:** Number → 2 decimals → Suffix: " triệu/m²"

### 5.3. Font Settings
- Font family: **Roboto** hoặc **Arial** (hỗ trợ tiếng Việt)
- Font size: Adjust cho dễ đọc

### 5.4. Report Title & Header
1. Add **Text box** ở đầu report
2. Title: "📊 Phân Tích Dữ Liệu Bất Động Sản Hà Nội"
3. Subtitle: "Dashboard Analytics - Real Estate Data"
4. Format: Bold, Large font

---

## 🔄 Bước 6: Refresh & Data Freshness

### 6.1. Set Data Refresh Schedule
1. Vào **Report settings** → **Data freshness**
2. Set refresh: **"Daily"** hoặc **"Real-time"**
3. Time: Chọn thời gian refresh (ví dụ: 8:00 AM daily)

---

## 📤 Bước 7: Share Dashboard

### 7.1. Share Settings
1. Click **"Share"** button (góc trên bên phải)
2. Chọn quyền:
   - **"Anyone with the link can view"** (public)
   - **"Anyone with the link can edit"** (collaborators)
   - **"Restricted"** (only specific people)

### 7.2. Get Shareable Link
1. Copy link
2. Share với người cần xem dashboard

### 7.3. Embed (Optional)
1. Click **"Embed report"**
2. Copy embed code
3. Embed vào website nếu cần

---

## ✅ Checklist Hoàn Thành:

- [x] Kết nối BigQuery thành công
- [x] Tạo calculated fields (Phân khúc giá, Quận/Huyện, Giá trên m²)
- [x] Tạo Scorecards (Tổng quan)
- [x] Tạo Bar charts (Phân bố theo loại hình, Quận/Huyện)
- [x] Tạo Time series chart (Xu hướng giá)
- [x] Tạo Tables (Chi tiết, So sánh)
- [x] Tạo Pie chart (Phân khúc giá)
- [x] Tạo Scatter chart (Mối quan hệ giá-diện tích)
- [x] Tạo Geo chart (Bản đồ)
- [x] Tạo Filters (Date range, Loại hình, Quận/Huyện, Giá)
- [x] Formatting (Number format, Colors, Fonts)
- [x] Set data refresh schedule
- [x] Share dashboard

---

## 🎯 Tips & Best Practices:

1. **Performance:**
   - Sử dụng filters để giảm lượng data query
   - Limit date range trong time series charts
   - Sử dụng aggregations thay vì raw data

2. **Visualization:**
   - Chọn chart type phù hợp với loại data
   - Sử dụng màu sắc nhất quán
   - Thêm titles và descriptions rõ ràng

3. **User Experience:**
   - Đặt filters ở vị trí dễ thấy
   - Group related charts trên cùng 1 page
   - Sử dụng conditional formatting để highlight important metrics

4. **Data Quality:**
   - Xử lý NULL values trong calculated fields
   - Validate data ranges trong filters
   - Add data quality checks

---

## 🔗 Quick Links:

- **Looker Studio:** https://datastudio.google.com/
- **BigQuery Console:** https://console.cloud.google.com/bigquery?project=etl-gcp-200501
- **Project Settings:** https://console.cloud.google.com/iam-admin/settings?project=etl-gcp-200501

