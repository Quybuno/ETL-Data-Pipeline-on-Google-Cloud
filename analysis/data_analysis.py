"""
Phân tích dữ liệu bất động sản Hà Nội từ BigQuery
Sử dụng để visualize và phân tích chi tiết
"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from google.cloud import bigquery
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Cấu hình
PROJECT_ID = "etl-gcp-200501"
DATASET_ID = "hanoi_real_estate"
TABLE_ID = "properties"

# Setup BigQuery client
client = bigquery.Client(project=PROJECT_ID)

# Thiết lập matplotlib cho tiếng Việt
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['figure.figsize'] = (12, 8)
sns.set_style("whitegrid")


def load_data(query):
    """Load data từ BigQuery"""
    query_job = client.query(query)
    return query_job.to_dataframe()


def analyze_overview():
    """1. Phân tích tổng quan"""
    print("=" * 60)
    print("1. TỔNG QUAN DỮ LIỆU")
    print("=" * 60)
    
    query = f"""
    SELECT 
      COUNT(*) as total_records,
      COUNT(DISTINCT url) as unique_properties,
      COUNT(DISTINCT DATE(run_date)) as total_days,
      MIN(run_date) as first_date,
      MAX(run_date) as latest_date,
      COUNT(DISTINCT loai_hinh) as total_property_types
    FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    WHERE run_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    """
    
    df = load_data(query)
    print(df.to_string(index=False))
    return df


def analyze_price_by_type():
    """2. Phân tích giá theo loại hình"""
    print("\n" + "=" * 60)
    print("2. PHÂN BỐ GIÁ THEO LOẠI HÌNH")
    print("=" * 60)
    
    query = f"""
    SELECT 
      loai_hinh,
      COUNT(*) as so_luong,
      AVG(price_billion_vnd) as gia_tb_tỷ_vnd,
      MIN(price_billion_vnd) as gia_thap_nhat,
      MAX(price_billion_vnd) as gia_cao_nhat
    FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    WHERE price_billion_vnd IS NOT NULL AND price_billion_vnd > 0
    GROUP BY loai_hinh
    ORDER BY so_luong DESC
    """
    
    df = load_data(query)
    print(df.to_string(index=False))
    
    # Vẽ biểu đồ
    if len(df) > 0:
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        
        # Biểu đồ số lượng
        df_sorted = df.sort_values('so_luong', ascending=True)
        axes[0].barh(df_sorted['loai_hinh'], df_sorted['so_luong'])
        axes[0].set_xlabel('Số lượng tin đăng')
        axes[0].set_title('Phân bố số lượng tin đăng theo loại hình')
        axes[0].grid(axis='x', alpha=0.3)
        
        # Biểu đồ giá trung bình
        df_sorted_price = df.sort_values('gia_tb_tỷ_vnd', ascending=True)
        axes[1].barh(df_sorted_price['loai_hinh'], df_sorted_price['gia_tb_tỷ_vnd'])
        axes[1].set_xlabel('Giá trung bình (tỷ VNĐ)')
        axes[1].set_title('Giá trung bình theo loại hình')
        axes[1].grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('price_by_type.png', dpi=300, bbox_inches='tight')
        print(f"\n✅ Đã lưu biểu đồ: price_by_type.png")
        plt.close()
    
    return df


def analyze_area_by_type():
    """3. Phân tích diện tích theo loại hình"""
    print("\n" + "=" * 60)
    print("3. PHÂN BỐ DIỆN TÍCH THEO LOẠI HÌNH")
    print("=" * 60)
    
    query = f"""
    SELECT 
      loai_hinh,
      COUNT(*) as so_luong,
      AVG(area_m2) as dien_tich_tb_m2,
      MIN(area_m2) as dien_tich_nho_nhat,
      MAX(area_m2) as dien_tich_lon_nhat
    FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    WHERE area_m2 IS NOT NULL AND area_m2 > 0
    GROUP BY loai_hinh
    ORDER BY so_luong DESC
    """
    
    df = load_data(query)
    print(df.to_string(index=False))
    
    # Vẽ biểu đồ
    if len(df) > 0:
        plt.figure(figsize=(10, 6))
        df_sorted = df.sort_values('dien_tich_tb_m2', ascending=True)
        plt.barh(df_sorted['loai_hinh'], df_sorted['dien_tich_tb_m2'])
        plt.xlabel('Diện tích trung bình (m²)')
        plt.title('Diện tích trung bình theo loại hình')
        plt.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        plt.savefig('area_by_type.png', dpi=300, bbox_inches='tight')
        print(f"\n✅ Đã lưu biểu đồ: area_by_type.png")
        plt.close()
    
    return df


def analyze_price_trend():
    """4. Phân tích xu hướng giá theo thời gian"""
    print("\n" + "=" * 60)
    print("4. XU HƯỚNG GIÁ THEO THỜI GIAN")
    print("=" * 60)
    
    query = f"""
    SELECT 
      run_date,
      COUNT(*) as so_tin_dang,
      AVG(price_billion_vnd) as gia_tb_tỷ_vnd
    FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    WHERE price_billion_vnd IS NOT NULL 
      AND price_billion_vnd > 0
      AND run_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY run_date
    ORDER BY run_date
    """
    
    df = load_data(query)
    if len(df) > 0:
        print(df.to_string(index=False))
        
        # Vẽ biểu đồ xu hướng
        plt.figure(figsize=(14, 6))
        plt.plot(df['run_date'], df['gia_tb_tỷ_vnd'], marker='o', linewidth=2, markersize=8)
        plt.xlabel('Ngày')
        plt.ylabel('Giá trung bình (tỷ VNĐ)')
        plt.title('Xu hướng giá bất động sản theo thời gian')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('price_trend.png', dpi=300, bbox_inches='tight')
        print(f"\n✅ Đã lưu biểu đồ: price_trend.png")
        plt.close()
    
    return df


def analyze_price_per_m2():
    """5. Phân tích giá/m² theo loại hình"""
    print("\n" + "=" * 60)
    print("5. PHÂN TÍCH GIÁ/M² THEO LOẠI HÌNH")
    print("=" * 60)
    
    query = f"""
    SELECT 
      loai_hinh,
      COUNT(*) as so_luong,
      AVG(price_billion_vnd) as gia_tb_tỷ_vnd,
      AVG(area_m2) as dien_tich_tb_m2,
      AVG(price_billion_vnd / area_m2 * 1000) as gia_tb_trên_m2_trieu_vnd
    FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    WHERE price_billion_vnd IS NOT NULL 
      AND area_m2 IS NOT NULL 
      AND price_billion_vnd > 0 
      AND area_m2 > 0
    GROUP BY loai_hinh
    ORDER BY gia_tb_trên_m2_trieu_vnd DESC
    """
    
    df = load_data(query)
    print(df.to_string(index=False))
    
    # Vẽ biểu đồ
    if len(df) > 0:
        plt.figure(figsize=(12, 6))
        df_sorted = df.sort_values('gia_tb_trên_m2_trieu_vnd', ascending=True)
        plt.barh(df_sorted['loai_hinh'], df_sorted['gia_tb_trên_m2_trieu_vnd'])
        plt.xlabel('Giá trung bình trên m² (triệu VNĐ)')
        plt.title('Giá trên m² theo loại hình bất động sản')
        plt.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        plt.savefig('price_per_m2.png', dpi=300, bbox_inches='tight')
        print(f"\n✅ Đã lưu biểu đồ: price_per_m2.png")
        plt.close()
    
    return df


def analyze_district():
    """6. Phân tích theo quận/huyện"""
    print("\n" + "=" * 60)
    print("6. TOP QUẬN/HUYỆN CÓ NHIỀU TIN ĐĂNG")
    print("=" * 60)
    
    query = f"""
    SELECT 
      CASE 
        WHEN address LIKE '%Cầu Giấy%' THEN 'Cầu Giấy'
        WHEN address LIKE '%Đống Đa%' THEN 'Đống Đa'
        WHEN address LIKE '%Hai Bà Trưng%' THEN 'Hai Bà Trưng'
        WHEN address LIKE '%Ba Đình%' THEN 'Ba Đình'
        WHEN address LIKE '%Hoàn Kiếm%' THEN 'Hoàn Kiếm'
        WHEN address LIKE '%Tây Hồ%' THEN 'Tây Hồ'
        WHEN address LIKE '%Thanh Xuân%' THEN 'Thanh Xuân'
        WHEN address LIKE '%Long Biên%' THEN 'Long Biên'
        WHEN address LIKE '%Nam Từ Liêm%' THEN 'Nam Từ Liêm'
        WHEN address LIKE '%Bắc Từ Liêm%' THEN 'Bắc Từ Liêm'
        WHEN address LIKE '%Hà Đông%' THEN 'Hà Đông'
        WHEN address LIKE '%Hoàng Mai%' THEN 'Hoàng Mai'
        ELSE 'Khác'
      END as quan_huyen,
      COUNT(*) as so_tin_dang,
      AVG(price_billion_vnd) as gia_tb_tỷ_vnd
    FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    WHERE address IS NOT NULL
    GROUP BY quan_huyen
    ORDER BY so_tin_dang DESC
    LIMIT 10
    """
    
    df = load_data(query)
    print(df.to_string(index=False))
    
    # Vẽ biểu đồ
    if len(df) > 0:
        plt.figure(figsize=(12, 6))
        df_sorted = df.sort_values('so_tin_dang', ascending=True)
        plt.barh(df_sorted['quan_huyen'], df_sorted['so_tin_dang'])
        plt.xlabel('Số lượng tin đăng')
        plt.title('Top 10 quận/huyện có nhiều tin đăng nhất')
        plt.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        plt.savefig('top_districts.png', dpi=300, bbox_inches='tight')
        print(f"\n✅ Đã lưu biểu đồ: top_districts.png")
        plt.close()
    
    return df


def main():
    """Chạy tất cả các phân tích"""
    print("\n" + "=" * 60)
    print("PHÂN TÍCH DỮ LIỆU BẤT ĐỘNG SẢN HÀ NỘI")
    print("=" * 60)
    print(f"Project: {PROJECT_ID}")
    print(f"Dataset: {DATASET_ID}")
    print(f"Table: {TABLE_ID}")
    print(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Chạy các phân tích
        analyze_overview()
        analyze_price_by_type()
        analyze_area_by_type()
        analyze_price_trend()
        analyze_price_per_m2()
        analyze_district()
        
        print("\n" + "=" * 60)
        print("✅ HOÀN THÀNH PHÂN TÍCH!")
        print("=" * 60)
        print("Các biểu đồ đã được lưu trong thư mục hiện tại:")
        print("  - price_by_type.png")
        print("  - area_by_type.png")
        print("  - price_trend.png")
        print("  - price_per_m2.png")
        print("  - top_districts.png")
        
    except Exception as e:
        print(f"\n❌ Lỗi: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

