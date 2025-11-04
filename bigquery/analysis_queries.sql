-- ============================================
-- PHÂN TÍCH DỮ LIỆU BẤT ĐỘNG SẢN HÀ NỘI
-- ============================================

-- 1. TỔNG QUAN DỮ LIỆU
SELECT 
  COUNT(*) as total_records,
  COUNT(DISTINCT url) as unique_properties,
  COUNT(DISTINCT DATE(run_date)) as total_days,
  MIN(run_date) as first_date,
  MAX(run_date) as latest_date,
  COUNT(DISTINCT loai_hinh) as total_property_types,
  COUNT(DISTINCT address) as unique_addresses
FROM `etl-gcp-200501.hanoi_real_estate.properties`
WHERE run_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY);

-- 2. PHÂN BỐ GIÁ THEO LOẠI HÌNH
SELECT 
  loai_hinh,
  COUNT(*) as so_luong,
  AVG(price_billion_vnd) as gia_tb_tỷ_vnd,
  MIN(price_billion_vnd) as gia_thap_nhat,
  MAX(price_billion_vnd) as gia_cao_nhat,
  PERCENTILE_CONT(price_billion_vnd, 0.5) OVER (PARTITION BY loai_hinh) as gia_median
FROM `etl-gcp-200501.hanoi_real_estate.properties`
WHERE price_billion_vnd IS NOT NULL AND price_billion_vnd > 0
GROUP BY loai_hinh
ORDER BY so_luong DESC;

-- 3. PHÂN BỐ DIỆN TÍCH THEO LOẠI HÌNH
SELECT 
  loai_hinh,
  COUNT(*) as so_luong,
  AVG(area_m2) as dien_tich_tb_m2,
  MIN(area_m2) as dien_tich_nho_nhat,
  MAX(area_m2) as dien_tich_lon_nhat
FROM `etl-gcp-200501.hanoi_real_estate.properties`
WHERE area_m2 IS NOT NULL AND area_m2 > 0
GROUP BY loai_hinh
ORDER BY so_luong DESC;

-- 4. TOP 10 QUẬN/HUYỆN CÓ NHIỀU TIN ĐĂNG NHẤT
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
    WHEN address LIKE '%Cầu Giấy%' THEN 'Cầu Giấy'
    ELSE 'Khác'
  END as quan_huyen,
  COUNT(*) as so_tin_dang,
  AVG(price_billion_vnd) as gia_tb_tỷ_vnd,
  AVG(area_m2) as dien_tich_tb_m2
FROM `etl-gcp-200501.hanoi_real_estate.properties`
WHERE address IS NOT NULL
GROUP BY quan_huyen
ORDER BY so_tin_dang DESC
LIMIT 10;

-- 5. PHÂN TÍCH GIÁ/M2 THEO LOẠI HÌNH
SELECT 
  loai_hinh,
  COUNT(*) as so_luong,
  AVG(price_billion_vnd) as gia_tb_tỷ_vnd,
  AVG(area_m2) as dien_tich_tb_m2,
  AVG(price_billion_vnd / area_m2 * 1000) as gia_tb_trên_m2_trieu_vnd
FROM `etl-gcp-200501.hanoi_real_estate.properties`
WHERE price_billion_vnd IS NOT NULL 
  AND area_m2 IS NOT NULL 
  AND price_billion_vnd > 0 
  AND area_m2 > 0
GROUP BY loai_hinh
ORDER BY so_luong DESC;

-- 6. PHÂN TÍCH THEO THỜI GIAN (Xu hướng giá theo ngày)
SELECT 
  run_date,
  COUNT(*) as so_tin_dang,
  AVG(price_billion_vnd) as gia_tb_tỷ_vnd,
  MIN(price_billion_vnd) as gia_min,
  MAX(price_billion_vnd) as gia_max
FROM `etl-gcp-200501.hanoi_real_estate.properties`
WHERE price_billion_vnd IS NOT NULL 
  AND price_billion_vnd > 0
  AND run_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY run_date
ORDER BY run_date DESC;

-- 7. PHÂN TÍCH PHÁP LÝ
SELECT 
  phap_ly,
  COUNT(*) as so_luong,
  AVG(price_billion_vnd) as gia_tb_tỷ_vnd,
  AVG(area_m2) as dien_tich_tb_m2
FROM `etl-gcp-200501.hanoi_real_estate.properties`
WHERE phap_ly IS NOT NULL
GROUP BY phap_ly
ORDER BY so_luong DESC;

-- 8. PHÂN TÍCH SỐ PHÒNG
SELECT 
  CAST(phong_ngu AS INT64) as so_phong_ngu,
  COUNT(*) as so_luong,
  AVG(price_billion_vnd) as gia_tb_tỷ_vnd,
  AVG(area_m2) as dien_tich_tb_m2
FROM `etl-gcp-200501.hanoi_real_estate.properties`
WHERE phong_ngu IS NOT NULL 
  AND SAFE_CAST(phong_ngu AS INT64) IS NOT NULL
GROUP BY so_phong_ngu
ORDER BY so_phong_ngu;

-- 9. TOP 10 MÔI GIỚI CÓ NHIỀU TIN ĐĂNG NHẤT
SELECT 
  mo_gioi_ten,
  COUNT(*) as so_tin_dang,
  COUNT(DISTINCT url) as so_bat_dong_san
FROM `etl-gcp-200501.hanoi_real_estate.properties`
WHERE mo_gioi_ten IS NOT NULL
GROUP BY mo_gioi_ten
ORDER BY so_tin_dang DESC
LIMIT 10;

-- 10. PHÂN TÍCH HƯỚNG NHÀ
SELECT 
  huong_nha,
  COUNT(*) as so_luong,
  AVG(price_billion_vnd) as gia_tb_tỷ_vnd
FROM `etl-gcp-200501.hanoi_real_estate.properties`
WHERE huong_nha IS NOT NULL
GROUP BY huong_nha
ORDER BY so_luong DESC;

-- 11. PHÂN TÍCH PHÂN KHÚC GIÁ
SELECT 
  CASE 
    WHEN price_billion_vnd < 2 THEN 'Dưới 2 tỷ'
    WHEN price_billion_vnd >= 2 AND price_billion_vnd < 5 THEN '2-5 tỷ'
    WHEN price_billion_vnd >= 5 AND price_billion_vnd < 10 THEN '5-10 tỷ'
    WHEN price_billion_vnd >= 10 AND price_billion_vnd < 20 THEN '10-20 tỷ'
    WHEN price_billion_vnd >= 20 THEN 'Trên 20 tỷ'
    ELSE 'Không xác định'
  END as phan_khuc_gia,
  COUNT(*) as so_luong,
  AVG(area_m2) as dien_tich_tb_m2,
  AVG(price_billion_vnd) as gia_tb_tỷ_vnd
FROM `etl-gcp-200501.hanoi_real_estate.properties`
WHERE price_billion_vnd IS NOT NULL AND price_billion_vnd > 0
GROUP BY phan_khuc_gia
ORDER BY 
  CASE phan_khuc_gia
    WHEN 'Dưới 2 tỷ' THEN 1
    WHEN '2-5 tỷ' THEN 2
    WHEN '5-10 tỷ' THEN 3
    WHEN '10-20 tỷ' THEN 4
    WHEN 'Trên 20 tỷ' THEN 5
    ELSE 6
  END;

-- 12. PHÂN TÍCH PHÂN KHÚC DIỆN TÍCH
SELECT 
  CASE 
    WHEN area_m2 < 50 THEN 'Dưới 50m²'
    WHEN area_m2 >= 50 AND area_m2 < 70 THEN '50-70m²'
    WHEN area_m2 >= 70 AND area_m2 < 100 THEN '70-100m²'
    WHEN area_m2 >= 100 AND area_m2 < 150 THEN '100-150m²'
    WHEN area_m2 >= 150 THEN 'Trên 150m²'
    ELSE 'Không xác định'
  END as phan_khuc_dien_tich,
  COUNT(*) as so_luong,
  AVG(price_billion_vnd) as gia_tb_tỷ_vnd,
  AVG(price_billion_vnd / area_m2 * 1000) as gia_tb_trên_m2_trieu_vnd
FROM `etl-gcp-200501.hanoi_real_estate.properties`
WHERE area_m2 IS NOT NULL AND area_m2 > 0
GROUP BY phan_khuc_dien_tich
ORDER BY 
  CASE phan_khuc_dien_tich
    WHEN 'Dưới 50m²' THEN 1
    WHEN '50-70m²' THEN 2
    WHEN '70-100m²' THEN 3
    WHEN '100-150m²' THEN 4
    WHEN 'Trên 150m²' THEN 5
    ELSE 6
  END;

