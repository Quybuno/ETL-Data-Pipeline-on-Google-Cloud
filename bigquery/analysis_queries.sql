-- ============================================
-- PHÂN TÍCH DỮ LIỆU BẤT ĐỘNG SẢN HÀ NỘI (SCHEMA CLEAN)
-- ============================================

-- 1. TỔNG QUAN DỮ LIỆU
SELECT 
  COUNT(*) AS total_records,
  COUNT(DISTINCT ma_bds) AS unique_properties,
  COUNT(DISTINCT ngay_dang) AS total_days,
  MIN(ngay_dang) AS first_date,
  MAX(ngay_dang) AS latest_date,
  COUNT(DISTINCT loai_hinh) AS total_property_types,
  COUNT(DISTINCT CONCAT(IFNULL(phuong_xa,''), '|', IFNULL(quan_huyen,''), '|', IFNULL(thanh_pho,''))) AS unique_addresses
FROM `final-478205.hanoi_real_estate.properties`
WHERE ngay_dang >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY);

-- 2. PHÂN BỐ GIÁ THEO LOẠI HÌNH
SELECT 
  loai_hinh,
  COUNT(*) AS so_luong,
  AVG(gia_ty) AS gia_tb_tyty,
  MIN(gia_ty) AS gia_thap_nhat,
  MAX(gia_ty) AS gia_cao_nhat,
  PERCENTILE_CONT(gia_ty, 0.5) OVER (PARTITION BY loai_hinh) AS gia_median
FROM `final-478205.hanoi_real_estate.properties`
WHERE gia_ty IS NOT NULL AND gia_ty > 0
GROUP BY loai_hinh
ORDER BY so_luong DESC;

-- 3. PHÂN BỐ DIỆN TÍCH SỬ DỤNG THEO LOẠI HÌNH
SELECT 
  loai_hinh,
  COUNT(*) AS so_luong,
  AVG(dien_tich_su_dung_m2) AS dien_tich_tb_m2,
  MIN(dien_tich_su_dung_m2) AS dien_tich_nho_nhat,
  MAX(dien_tich_su_dung_m2) AS dien_tich_lon_nhat
FROM `final-478205.hanoi_real_estate.properties`
WHERE dien_tich_su_dung_m2 IS NOT NULL AND dien_tich_su_dung_m2 > 0
GROUP BY loai_hinh
ORDER BY so_luong DESC;

-- 4. TOP 10 QUẬN/HUYỆN CÓ NHIỀU TIN ĐĂNG NHẤT
SELECT 
  SAFE_CAST(quan_huyen AS STRING) AS quan_huyen,
  COUNT(*) AS so_tin_dang,
  AVG(gia_ty) AS gia_tb_tyty,
  AVG(dien_tich_su_dung_m2) AS dien_tich_tb_m2
FROM `final-478205.hanoi_real_estate.properties`
WHERE quan_huyen IS NOT NULL AND LENGTH(TRIM(quan_huyen)) > 0
GROUP BY quan_huyen
ORDER BY so_tin_dang DESC
LIMIT 10;

-- 5. GIÁ/M2 THEO LOẠI HÌNH
SELECT 
  loai_hinh,
  COUNT(*) AS so_luong,
  AVG(gia_ty) AS gia_tb_tyty,
  AVG(dien_tich_su_dung_m2) AS dien_tich_tb_m2,
  AVG(gia_ty / dien_tich_su_dung_m2 * 1000) AS gia_tb_tren_m2_trieu_vnd
FROM `final-478205.hanoi_real_estate.properties`
WHERE gia_ty IS NOT NULL 
  AND dien_tich_su_dung_m2 IS NOT NULL 
  AND gia_ty > 0 
  AND dien_tich_su_dung_m2 > 0
GROUP BY loai_hinh
ORDER BY so_luong DESC;

-- 6. XU HƯỚNG GIÁ THEO NGÀY
SELECT 
  ngay_dang,
  COUNT(*) AS so_tin_dang,
  AVG(gia_ty) AS gia_tb_tyty,
  MIN(gia_ty) AS gia_min,
  MAX(gia_ty) AS gia_max
FROM `final-478205.hanoi_real_estate.properties`
WHERE gia_ty IS NOT NULL 
  AND gia_ty > 0
  AND ngay_dang >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY ngay_dang
ORDER BY ngay_dang DESC;

-- 7. PHÂN TÍCH PHÁP LÝ
SELECT 
  phap_ly,
  COUNT(*) AS so_luong,
  AVG(gia_ty) AS gia_tb_tyty,
  AVG(dien_tich_su_dung_m2) AS dien_tich_tb_m2
FROM `final-478205.hanoi_real_estate.properties`
WHERE phap_ly IS NOT NULL AND LENGTH(TRIM(phap_ly)) > 0
GROUP BY phap_ly
ORDER BY so_luong DESC;

-- 8. PHÂN TÍCH THEO SỐ PHÒNG NGỦ
SELECT 
  CAST(phong_ngu AS INT64) AS so_phong_ngu,
  COUNT(*) AS so_luong,
  AVG(gia_ty) AS gia_tb_tyty,
  AVG(dien_tich_su_dung_m2) AS dien_tich_tb_m2
FROM `final-478205.hanoi_real_estate.properties`
WHERE phong_ngu IS NOT NULL 
  AND SAFE_CAST(phong_ngu AS INT64) IS NOT NULL
GROUP BY so_phong_ngu
ORDER BY so_phong_ngu;

-- 9. TOP 10 MÔI GIỚI CÓ NHIỀU TIN NHẤT
SELECT 
  SAFE_CAST(mo_gioi_ten AS STRING) AS mo_gioi_ten,
  COUNT(*) AS so_tin_dang,
  COUNT(DISTINCT ma_bds) AS so_bat_dong_san
FROM `final-478205.hanoi_real_estate.properties`
WHERE mo_gioi_ten IS NOT NULL AND LENGTH(TRIM(mo_gioi_ten)) > 0
GROUP BY mo_gioi_ten
ORDER BY so_tin_dang DESC
LIMIT 10;

-- 10. PHÂN TÍCH HƯỚNG NHÀ
SELECT 
  SAFE_CAST(huong_nha AS STRING) AS huong_nha,
  COUNT(*) AS so_luong,
  AVG(gia_ty) AS gia_tb_tyty
FROM `final-478205.hanoi_real_estate.properties`
WHERE huong_nha IS NOT NULL AND LENGTH(TRIM(huong_nha)) > 0
GROUP BY huong_nha
ORDER BY so_luong DESC;

-- 11. PHÂN KHÚC GIÁ
SELECT 
  CASE 
    WHEN gia_ty < 2 THEN 'Dưới 2 tỷ'
    WHEN gia_ty >= 2 AND gia_ty < 5 THEN '2-5 tỷ'
    WHEN gia_ty >= 5 AND gia_ty < 10 THEN '5-10 tỷ'
    WHEN gia_ty >= 10 AND gia_ty < 20 THEN '10-20 tỷ'
    WHEN gia_ty >= 20 THEN 'Trên 20 tỷ'
    ELSE 'Không xác định'
  END AS phan_khuc_gia,
  COUNT(*) AS so_luong,
  AVG(dien_tich_su_dung_m2) AS dien_tich_tb_m2,
  AVG(gia_ty) AS gia_tb_tyty
FROM `final-478205.hanoi_real_estate.properties`
WHERE gia_ty IS NOT NULL AND gia_ty > 0
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

-- 12. PHÂN KHÚC DIỆN TÍCH
SELECT 
  CASE 
    WHEN dien_tich_su_dung_m2 < 50 THEN 'Dưới 50m²'
    WHEN dien_tich_su_dung_m2 >= 50 AND dien_tich_su_dung_m2 < 70 THEN '50-70m²'
    WHEN dien_tich_su_dung_m2 >= 70 AND dien_tich_su_dung_m2 < 100 THEN '70-100m²'
    WHEN dien_tich_su_dung_m2 >= 100 AND dien_tich_su_dung_m2 < 150 THEN '100-150m²'
    WHEN dien_tich_su_dung_m2 >= 150 THEN 'Trên 150m²'
    ELSE 'Không xác định'
  END AS phan_khuc_dien_tich,
  COUNT(*) AS so_luong,
  AVG(gia_ty) AS gia_tb_tyty,
  AVG(gia_ty / dien_tich_su_dung_m2 * 1000) AS gia_tb_tren_m2_trieu_vnd
FROM `final-478205.hanoi_real_estate.properties`
WHERE dien_tich_su_dung_m2 IS NOT NULL AND dien_tich_su_dung_m2 > 0
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

