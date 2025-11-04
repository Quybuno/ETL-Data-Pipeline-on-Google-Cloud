# Hướng Dẫn Tạo Looker Studio Dashboard

## Bước 1: Kết Nối với BigQuery

1. Truy cập Looker Studio: https://datastudio.google.com/
2. Click **"Create"** → **"Data Source"**
3. Chọn **"BigQuery"** từ danh sách connectors
4. Chọn connection:
   - **Project**: `etl-gcp-200501`
   - **Dataset**: `hanoi_real_estate`
   - **Table**: `properties`
5. Click **"Connect"**

## Bước 2: Tạo Các Metrics & Dimensions

### Dimensions (Kích thước):
- `loai_hinh` - Loại hình BĐS
- `address` - Địa chỉ
- `run_date` - Ngày thu thập
- `phap_ly` - Pháp lý
- `phong_ngu` - Số phòng ngủ
- `huong_nha` - Hướng nhà

### Metrics (Số liệu):
- `COUNT(url)` - Tổng số tin đăng (đổi tên thành "Số lượng tin đăng")
- `AVG(price_billion_vnd)` - Giá trung bình (đổi tên thành "Giá TB (tỷ VNĐ)")
- `AVG(area_m2)` - Diện tích trung bình (đổi tên thành "Diện tích TB (m²)")
- `AVG(price_billion_vnd / area_m2 * 1000)` - Giá trên m² (tạo calculated field)

## Bước 3: Tạo Dashboard

### Trang 1: Tổng Quan

1. **Scorecard Cards:**
   - Tổng số tin đăng: `COUNT(url)`
   - Giá trung bình: `AVG(price_billion_vnd)` (định dạng: Number → 2 decimals)
   - Diện tích trung bình: `AVG(area_m2)` (định dạng: Number → 0 decimals)

2. **Bar Chart - Phân bố theo loại hình:**
   - Dimension: `loai_hinh`
   - Metric: `COUNT(url)`
   - Sắp xếp: Giảm dần

3. **Time Series Chart - Xu hướng giá theo thời gian:**
   - Dimension: `run_date` (Date)
   - Metric: `AVG(price_billion_vnd)`
   - Chọn period: Last 30 days

### Trang 2: Phân Tích Chi Tiết

1. **Table - Chi tiết giá theo loại hình:**
   - Dimensions: `loai_hinh`
   - Metrics:
     - `COUNT(url)` - Số lượng
     - `AVG(price_billion_vnd)` - Giá TB
     - `MIN(price_billion_vnd)` - Giá thấp nhất
     - `MAX(price_billion_vnd)` - Giá cao nhất
     - `AVG(area_m2)` - Diện tích TB

2. **Pie Chart - Phân bố phân khúc giá:**
   - Tạo calculated field: "Phân khúc giá"
     ```
     CASE
       WHEN price_billion_vnd < 2 THEN "Dưới 2 tỷ"
       WHEN price_billion_vnd >= 2 AND price_billion_vnd < 5 THEN "2-5 tỷ"
       WHEN price_billion_vnd >= 5 AND price_billion_vnd < 10 THEN "5-10 tỷ"
       WHEN price_billion_vnd >= 10 THEN "Trên 10 tỷ"
       ELSE "Không xác định"
     END
     ```
   - Dimension: Phân khúc giá (calculated field)
   - Metric: `COUNT(url)`

3. **Bar Chart - Top 10 quận/huyện:**
   - Tạo calculated field: "Quận/Huyện" (extract từ address)
   - Dimension: Quận/Huyện
   - Metric: `COUNT(url)`
   - Filter: Top 10

### Trang 3: Bản Đồ và Địa Lý

1. **Geo Chart:**
   - Dimension: `address` (Geographic → City)
   - Metric: `COUNT(url)`
   - Color by: `AVG(price_billion_vnd)`

### Trang 4: So Sánh

1. **Table - So sánh giá/m²:**
   - Dimension: `loai_hinh`
   - Metric: Calculated field "Giá trên m²" = `AVG(price_billion_vnd / area_m2 * 1000)`
   - Sort: Giảm dần

2. **Scatter Chart - Mối quan hệ giá và diện tích:**
   - X-axis: `area_m2`
   - Y-axis: `price_billion_vnd`
   - Color: `loai_hinh`
   - Size: `COUNT(url)`

## Bước 4: Tạo Filters (Bộ Lọc)

1. **Date Range Filter:**
   - Dimension: `run_date`
   - Type: Date Range

2. **Dropdown Filter - Loại hình:**
   - Dimension: `loai_huyen`
   - Type: Dropdown list

3. **Slider Filter - Giá:**
   - Metric: `price_billion_vnd`
   - Type: Numeric range slider

## Bước 5: Styling & Formatting

1. **Theme:** Chọn theme phù hợp (Light/Dark)
2. **Colors:** Customize màu sắc cho charts
3. **Fonts:** Chọn font hỗ trợ tiếng Việt
4. **Number Formatting:**
   - Giá: Number → 2 decimals → Thêm " tỷ VNĐ"
   - Diện tích: Number → 0 decimals → Thêm " m²"

## Bước 6: Share Dashboard

1. Click **"Share"** button (góc trên bên phải)
2. Chọn quyền:
   - **Viewer**: Chỉ xem
   - **Editor**: Có thể chỉnh sửa
3. Copy link và share cho người khác

## Templates & Examples

Có thể sử dụng các template có sẵn:
- **Real Estate Dashboard Template**
- **Market Analysis Template**
- **Time Series Analysis Template**

## Tips:

1. **Performance:** Sử dụng filters để giảm lượng data query
2. **Refresh:** Data tự động refresh từ BigQuery (có thể set schedule)
3. **Calculated Fields:** Tạo calculated fields để tính toán phức tạp
4. **Blending:** Có thể blend nhiều data sources nếu cần

