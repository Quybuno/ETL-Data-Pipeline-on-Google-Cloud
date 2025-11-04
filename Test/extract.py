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
parser.add_argument("--max_pages", type=int, default=400)
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

    # breadcrumb an toàn
    bc = soup.find('ul', class_="breadcrumb clearfix")
    if bc:
        spans = bc.find_all('span')
        if len(spans) > 1: data['loai_hinh'] = spans[1].get_text(strip=True)
        if len(spans) > 4: data['title']     = spans[4].get_text(strip=True)

    addr = soup.find('div', class_="address")
    data['address'] = addr.get_text(strip=True) if addr else None
    price = soup.find('div', class_="price")
    data['price'] = price.get_text(strip=True) if price else None

    for info in soup.find_all("div", class_="info-attr clearfix"):
        spans = info.find_all('span')
        if len(spans) >= 2:
            key = spans[0].get_text(strip=True)
            val = spans[1].get_text(strip=True)
            if key and val:
                data[key] = val

    # agent
    agent = soup.find('div', class_="agent-widget widget")
    if agent:
        a = agent.find('a', href=True)
        if a:
            data['mo_gioi_ten']  = a.get_text(strip=True)
            data['mo_gioi_link'] = urljoin(BASE, a['href'])

    span = soup.find("span", attrs={"ng-bind": re.compile(r"PhoneFormat\(")})
    if span and span.has_attr("ng-bind"):
        m = re.search(r"PhoneFormat\('(\d{8,12})'\)", span["ng-bind"])
        if m:
            data['mo_gioi_phone'] = m.group(1)

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
