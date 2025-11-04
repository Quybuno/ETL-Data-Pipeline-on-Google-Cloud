# Phân Tích Dữ Liệu Bất Động Sản Hà Nội

Thư mục này chứa các công cụ và scripts để phân tích dữ liệu bất động sản Hà Nội từ BigQuery.

## 📁 Cấu Trúc Files:

- `data_analysis.py` - Python script phân tích và visualize dữ liệu
- `analysis_queries.sql` - SQL queries để chạy trực tiếp trên BigQuery
- `LOOKER_STUDIO_GUIDE.md` - Hướng dẫn tạo dashboard Looker Studio
- `requirements.txt` - Python dependencies

## 🚀 Cách Sử Dụng:

### Option 1: Chạy Python Script (Khuyến nghị)

```powershell
cd D:\Nhadat\analysis
pip install -r requirements.txt
python data_analysis.py
```

Script sẽ:
- ✅ Load data từ BigQuery
- ✅ Thực hiện các phân tích
- ✅ Tạo các biểu đồ và lưu thành file PNG
- ✅ Hiển thị kết quả phân tích trên console

### Option 2: Chạy SQL Queries trên BigQuery Console

1. Mở BigQuery Console: https://console.cloud.google.com/bigquery?project=etl-gcp-200501
2. Copy query từ `analysis_queries.sql`
3. Paste vào Query editor và chạy

### Option 3: Tạo Dashboard Looker Studio

Xem hướng dẫn chi tiết trong `LOOKER_STUDIO_GUIDE.md`

## 📊 Các Phân Tích Được Thực Hiện:

1. **Tổng quan dữ liệu** - Số lượng records, unique properties, date range
2. **Phân bố giá theo loại hình** - Giá trung bình, min, max theo từng loại
3. **Phân bố diện tích** - Diện tích trung bình theo loại hình
4. **Top quận/huyện** - Các quận có nhiều tin đăng nhất
5. **Giá trên m²** - Phân tích giá/m² theo loại hình
6. **Xu hướng giá** - Giá biến động theo thời gian
7. **Phân khúc giá** - Phân chia theo mức giá (dưới 2 tỷ, 2-5 tỷ, etc.)
8. **Phân khúc diện tích** - Phân chia theo diện tích
9. **Phân tích môi giới** - Top môi giới có nhiều tin đăng
10. **Phân tích hướng nhà** - Phân bố theo hướng

## 📈 Biểu Đồ Được Tạo:

- `price_by_type.png` - Giá và số lượng theo loại hình
- `area_by_type.png` - Diện tích theo loại hình  
- `price_trend.png` - Xu hướng giá theo thời gian
- `price_per_m2.png` - Giá trên m² theo loại hình
- `top_districts.png` - Top 10 quận/huyện

## 🎯 Next Steps:

1. ✅ Chạy phân tích cơ bản với Python script
2. ✅ Tạo Looker Studio dashboard để trực quan hóa
3. ✅ Phân tích sâu hơn với SQL queries
4. ✅ Tạo báo cáo định kỳ

