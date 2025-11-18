import os, re, csv, json, time, random, math, argparse, tempfile, pathlib
from datetime import date
from urllib.parse import urljoin
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google.cloud import storage

# ====== Tham số hoá ======
parser = argparse.ArgumentParser()
parser.add_argument("--run_date", default=os.getenv("RUN_DATE", date.today().isoformat()))
parser.add_argument("--source", default=os.getenv("SOURCE", "mogi"))
parser.add_argument("--raw_bucket", default=os.getenv("RAW_BUCKET"))
parser.add_argument("--max_pages", type=int, default=40)
parser.add_argument("--workers", type=int, default=12)
parser.add_argument("--batch_size", type=int, default=500)
args = parser.parse_args()

RUN_DATE   = args.run_date
SOURCE     = args.source
RAW_BUCKET = args.raw_bucket
MAX_PAGES  = args.max_pages
WORKERS    = args.workers
BATCH_SIZE = args.batch_size

if not RAW_BUCKET:
    raise SystemExit("Missing --raw_bucket or RAW_BUCKET env")

BASE = "https://mogi.vn"
base_URL = "https://mogi.vn/ha-noi/mua-nha-dat"

# ====== HTTP session + retry ======
session = requests.Session()
retry = Retry(
    total=5, connect=3, read=3, status=5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "HEAD"],
    backoff_factor=1.2,
)
adapter = HTTPAdapter(max_retries=retry, pool_connections=50, pool_maxsize=50)
session.mount("http://", adapter); session.mount("https://", adapter)
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8"
})

def bs(html):
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")

# ====== GCS client ======
gcs = storage.Client()
bucket = gcs.bucket(RAW_BUCKET)
prefix = f"source={SOURCE}/dt={RUN_DATE}/"
pathlib.Path("tmp_out").mkdir(exist_ok=True)

def flush_batch_to_gcs(batch_records, batch_idx):
    """Ghi batch ra jsonl tạm rồi upload GCS theo prefix/part-xxxxx.jsonl"""
    if not batch_records:
        return None
    local_tmp = f"tmp_out/part-{batch_idx:05d}.jsonl"
    with open(local_tmp, "w", encoding="utf-8") as f:
        for rec in batch_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    blob_name = prefix + f"part-{batch_idx:05d}.jsonl"
    blob = bucket.blob(blob_name)
    # Nếu đã có trên GCS, bỏ qua để idempotent (tuỳ chọn)
    if blob.exists():
        print(f"[skip] đã tồn tại {blob_name}")
        return blob_name
    blob.upload_from_filename(local_tmp)
    print(f"[upload] gs://{RAW_BUCKET}/{blob_name} ({len(batch_records)} rec)")
    return blob_name

# ====== Producer: đẩy link chi tiết vào queue ======
def produce_links(link_queue: Queue):
    empty_streak = 0
    seen = set()
    for page in range(1, MAX_PAGES + 1):
        url = f"{base_URL}?cp={page}"
        try:
            resp = session.get(url, timeout=25)
        except Exception as e:
            print("List GET error:", e); time.sleep(random.uniform(0.6,1.2)); continue
        if resp.status_code != 200 or not resp.text:
            print("List bad status:", resp.status_code); time.sleep(random.uniform(0.6,1.2)); continue

        soup = bs(resp.text)
        anchors = soup.find_all("a", class_="link-overlay")
        if not anchors:
            empty_streak += 1
            print(f"[page {page}] không thấy tin (streak={empty_streak})")
            if empty_streak >= 3:
                print(f"Stop: không thấy tin {empty_streak} trang liền.")
                break
        else:
            empty_streak = 0
            for a in anchors:
                href = a.get("href")
                if not href: continue
                link = urljoin(BASE, href)
                if link not in seen:
                    seen.add(link)
                    link_queue.put(link)
        # ngủ ngẫu nhiên chống bị chặn
        time.sleep(random.uniform(0.6,1.2))

    # Gửi tín hiệu hết việc cho consumers
    for _ in range(WORKERS):
        link_queue.put(None)

# ====== Helper functions ======
def extract_number_from_text(text: str) -> float | None:
    """Extract số đầu tiên từ text (hỗ trợ format VN: 60,5 hoặc 60.5)"""
    if not text:
        return None
    # Tìm số đầu tiên (có thể có dấu phẩy hoặc chấm)
    match = re.search(r'(\d+(?:[.,]\d+)?)', str(text).replace(',', '.'))
    if match:
        try:
            return float(match.group(1).replace(',', '.'))
        except ValueError:
            return None
    return None

def extract_dimensions(text: str) -> tuple[float | None, float | None]:
    """Extract chiều dài và chiều rộng từ text như '60m² (12x5)' hoặc '12m x 5m'"""
    if not text:
        return None, None
    text_str = str(text).lower()
    # Pattern: (12x5) hoặc 12x5 hoặc 12m x 5m
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*[mx×]\s*(\d+(?:[.,]\d+)?)', text_str)
    if match:
        try:
            num1 = float(match.group(1).replace(',', '.'))
            num2 = float(match.group(2).replace(',', '.'))
            # Số lớn hơn là chiều dài, nhỏ hơn là chiều rộng
            return max(num1, num2), min(num1, num2)
        except ValueError:
            pass
    return None, None

# ====== Consumer: tải & parse 1 link ======
def parse_detail(link: str) -> dict | None:
    try:
        res = session.get(link, timeout=12)
    except Exception as e:
        print("Detail GET error:", e, link); return None
    if res.status_code != 200 or not res.text:
        print("Detail bad status:", res.status_code, link); return None

    soup = bs(res.text)
    data = {"url": link, "_source": SOURCE, "_run_date": RUN_DATE}

    # === 1. TITLE: Lấy từ nhiều nguồn với fallback ===
    # Ưu tiên 1: Breadcrumb
    bc = soup.find('ul', class_="breadcrumb clearfix")
    if bc:
        spans = bc.find_all('span')
        if len(spans) > 1: 
            data['loai_hinh'] = spans[1].get_text(strip=True)
        if len(spans) > 4: 
            title = spans[4].get_text(strip=True)
            if title:
                data['title'] = title
    
    # Ưu tiên 2: H1 tag
    if not data.get('title'):
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
            if title and len(title) > 5:  # Tránh lấy title quá ngắn
                data['title'] = title
    
    # Ưu tiên 3: Meta tags (og:title hoặc <title>)
    if not data.get('title'):
        meta_title = soup.find('meta', property='og:title') or soup.find('meta', attrs={'name': 'title'})
        if meta_title:
            title = meta_title.get('content', '').strip()
            if title and len(title) > 5:
                data['title'] = title
    
    # Ưu tiên 4: Standard <title> tag
    if not data.get('title'):
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
            if title and len(title) > 5:
                # Loại bỏ suffix như " - Mogi.vn"
                title = re.sub(r'\s*[-|]\s*(Mogi|mogi).*$', '', title, flags=re.IGNORECASE).strip()
                if title:
                    data['title'] = title

    # === 2. ADDRESS ===
    addr = soup.find('div', class_="address")
    if not addr:
        # Thử các selector khác
        addr = soup.find('div', class_="detail-address") or soup.find('span', class_="address")
    data['address'] = addr.get_text(strip=True) if addr else None

    # === 3. PRICE ===
    price = soup.find('div', class_="price")
    if not price:
        # Thử các selector khác
        price = soup.find('span', class_="price") or soup.find('div', class_="price-value")
    data['price'] = price.get_text(strip=True) if price else None

    # === 4. INFO ATTRIBUTES: Parse tất cả các thông tin chi tiết ===
    # Tìm tất cả info-attr divs
    for info in soup.find_all("div", class_="info-attr clearfix"):
        spans = info.find_all('span')
        if len(spans) >= 2:
            key = spans[0].get_text(strip=True)
            val = spans[1].get_text(strip=True)
            if key and val:
                data[key] = val
    
    # Thử tìm thêm từ các selector khác (nếu website dùng cấu trúc khác)
    info_sections = soup.find_all("div", class_=re.compile(r"info|detail|attribute", re.I))
    for section in info_sections:
        # Tìm các pattern như "Diện tích: 60m²"
        text = section.get_text(strip=True)
        if ':' in text:
            for line in text.split('\n'):
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip()
                        if key and val and key not in data:
                            data[key] = val

    # === 5. EXTRACT THÔNG TIN BỔ SUNG TỪ TITLE ===
    # Nếu một số trường chưa có, thử parse từ title
    if data.get('title') and not data.get('Diện tích'):
        # Parse diện tích từ title: "Nhà 60m²..." hoặc "60m2"
        area_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', data['title'], re.IGNORECASE)
        if area_match:
            area_val = extract_number_from_text(area_match.group(0))
            if area_val and 'Diện tích' not in data:
                data['Diện tích'] = f"{area_val} m²"
            
            # Parse chiều dài x chiều rộng từ title nếu có: "60m² (12x5)"
            chieu_dai, chieu_rong = extract_dimensions(data['title'])
            if chieu_dai and 'Chiều dài' not in data:
                data['Chiều dài'] = f"{chieu_dai} m"
            if chieu_rong and 'Chiều rộng' not in data:
                data['Chiều rộng'] = f"{chieu_rong} m"

    # === 6. EXTRACT CHIỀU DÀI/RỘNG TỪ DIỆN TÍCH (nếu có format đặc biệt) ===
    dien_tich_text = data.get('Diện tích') or data.get('Diện tích sử dụng') or data.get('Diện tích đất')
    if dien_tich_text and not (data.get('Chiều dài') or data.get('Chiều rộng')):
        chieu_dai, chieu_rong = extract_dimensions(dien_tich_text)
        if chieu_dai:
            data['Chiều dài'] = f"{chieu_dai} m"
        if chieu_rong:
            data['Chiều rộng'] = f"{chieu_rong} m"

    # === 7. NGÀY ĐĂNG: Tìm từ nhiều nguồn ===
    if 'Ngày đăng' not in data and 'Ngày cập nhật' not in data:
        # Tìm trong các div có chứa "ngày"
        date_divs = soup.find_all(string=re.compile(r'ngày.*đăng|ngày.*cập.*nhật', re.I))
        for date_div in date_divs:
            parent = date_div.parent if date_div.parent else None
            if parent:
                date_text = parent.get_text(strip=True)
                date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', date_text)
                if date_match:
                    data['Ngày đăng'] = date_match.group(1)
                    break

    # === 8. AGENT INFO ===
    agent = soup.find('div', class_="agent-widget widget")
    if not agent:
        # Thử các selector khác
        agent = soup.find('div', class_=re.compile(r"agent", re.I))
    
    if agent:
        a = agent.find('a', href=True)
        if a:
            data['mo_gioi_ten'] = a.get_text(strip=True)
            data['mo_gioi_link'] = urljoin(BASE, a['href'])
        
        # Tìm phone number
        phone_span = soup.find("span", attrs={"ng-bind": re.compile(r"PhoneFormat\(")})
        if not phone_span:
            # Thử tìm trong agent section
            phone_text = agent.get_text()
            phone_match = re.search(r'(\d{10,11})', phone_text.replace(' ', '').replace('-', ''))
            if phone_match:
                data['mo_gioi_phone'] = phone_match.group(1)
        else:
            if phone_span.has_attr("ng-bind"):
                m = re.search(r"PhoneFormat\('(\d{8,12})'\)", phone_span["ng-bind"])
                if m:
                    data['mo_gioi_phone'] = m.group(1)

    # === 9. MÔ TẢ/THÔNG TIN CHI TIẾT (nếu cần) ===
    description = soup.find('div', class_="content") or soup.find('div', class_="description")
    if description:
        desc_text = description.get_text(strip=True)
        if desc_text and len(desc_text) > 50:  # Chỉ lấy nếu có nội dung đáng kể
            data['description'] = desc_text[:500]  # Giới hạn 500 ký tự

    # ngủ nhẹ để lịch sự
    time.sleep(random.uniform(0.2, 0.6))
    return data

# ====== Orchestrate đa luồng + batch flush ======
def run_crawl_multithread():
    link_queue = Queue(maxsize=5000)
    # Producer
    with ThreadPoolExecutor(max_workers=1) as prod_pool:
        prod_pool.submit(produce_links, link_queue)

        # Consumers pool
        results = []
        batch = []
        batch_idx = 1

        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = set()
            done_links = 0

            # vòng lặp lấy link từ queue và nộp job
            while True:
                try:
                    link = link_queue.get(timeout=10)
                except Empty:
                    # có thể đã xong
                    if not futures:
                        break
                    else:
                        # đợi bớt future hoàn thành
                        for f in as_completed(list(futures), timeout=5):
                            futures.remove(f)
                            rec = f.result()
                            if rec:
                                batch.append(rec)
                            if len(batch) >= BATCH_SIZE:
                                flush_batch_to_gcs(batch, batch_idx)
                                batch.clear(); batch_idx += 1
                        continue

                if link is None:
                    # hết link; đợi các futures còn lại
                    for f in as_completed(list(futures)):
                        futures.remove(f)
                        rec = f.result()
                        if rec:
                            batch.append(rec)
                        if len(batch) >= BATCH_SIZE:
                            flush_batch_to_gcs(batch, batch_idx)
                            batch.clear(); batch_idx += 1
                    break

                futures.add(pool.submit(parse_detail, link))

            # flush batch cuối
            if batch:
                flush_batch_to_gcs(batch, batch_idx)

if __name__ == "__main__":
    print(f"Start crawl source={SOURCE} date={RUN_DATE}, region batches to gs://{RAW_BUCKET}/{prefix}")
    run_crawl_multithread()
    print("DONE.")

