import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv, time, random

BASE = "https://mogi.vn/ha-noi/mua-nha-dat"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

def crawl_page(page):
    """Crawl 1 trang"""
    url = f"{BASE}?page={page}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        data = []
        for card in soup.select("div.prop-info"):  # class của từng tin
            title_tag = card.select_one("h2.title a")
            price_tag = card.select_one(".price")
            area_tag = card.select_one(".square")
            location_tag = card.select_one(".location")
            link = title_tag["href"] if title_tag else None

            data.append({
                "page": page,
                "title": title_tag.get_text(strip=True) if title_tag else "",
                "price": price_tag.get_text(strip=True) if price_tag else "",
                "area": area_tag.get_text(strip=True) if area_tag else "",
                "location": location_tag.get_text(strip=True) if location_tag else "",
                "url": "https://mogi.vn" + link if link else ""
            })
        time.sleep(random.uniform(0.5, 1.5))  # tránh spam
        return data
    except Exception as e:
        print(f"⚠️ Lỗi ở trang {page}: {e}")
        return []

def main():
    all_data = []
    total_pages = 100  # bạn có thể tăng lên 500–1000 nếu muốn

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(crawl_page, i) for i in range(1, total_pages + 1)]
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            all_data.extend(result)
            print(f"✅ Đã lấy xong trang {i}/{total_pages}, tổng {len(all_data)} tin")

    with open("mogi_data.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
        writer.writeheader()
        writer.writerows(all_data)
    print('test commit')


    
    print(f"🎯 Hoàn tất! Đã lưu {len(all_data)} tin vào mogi_data.csv")

if __name__ == "__main__":
    main()
