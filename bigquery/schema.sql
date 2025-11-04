-- BigQuery table schema cho dữ liệu bất động sản
CREATE TABLE IF NOT EXISTS `etl-gcp-200501.hanoi_real_estate.properties` (
  url STRING,
  source STRING,
  run_date DATE,
  title STRING,
  address STRING,
  price_raw STRING,
  price_billion_vnd FLOAT64,
  area_raw STRING,
  area_m2 FLOAT64,
  loai_hinh STRING,
  phap_ly STRING,
  phong_ngu STRING,
  phong_tam STRING,
  huong_nha STRING,
  mo_gioi_ten STRING,
  mo_gioi_phone STRING,
  _loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY run_date
CLUSTER BY source, loai_hinh
OPTIONS(
  description="Bảng lưu dữ liệu bất động sản Hà Nội đã được transform",
  labels=[("env", "production"), ("team", "etl")]
);

