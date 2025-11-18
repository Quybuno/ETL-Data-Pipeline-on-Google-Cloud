-- Kiểm tra số lượng records trong BigQuery
SELECT COUNT(*) as total_records 
FROM `final-478205.hanoi_real_estate.properties`;

-- Kiểm tra số lượng records unique (theo ma_bds)
SELECT COUNT(DISTINCT ma_bds) as unique_records
FROM `final-478205.hanoi_real_estate.properties`;

-- Kiểm tra duplicate (nếu có)
SELECT ma_bds, COUNT(*) as count
FROM `final-478205.hanoi_real_estate.properties`
GROUP BY ma_bds
HAVING COUNT(*) > 1
ORDER BY count DESC
LIMIT 10;

-- Xem dữ liệu mới nhất
SELECT ma_bds, title, ngay_dang, gia_ty
FROM `final-478205.hanoi_real_estate.properties`
ORDER BY ngay_dang DESC
LIMIT 10;


