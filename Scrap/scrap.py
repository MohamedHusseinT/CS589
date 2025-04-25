import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import os
import boto3
from datetime import datetime
import re

AWS_BUCKET_NAME = "cs589-aiproject"
BASE_URL = "https://www.uscis.gov"
START_URL = "https://www.uscis.gov/policy-manual"
PAGE_DIR = "uscis_batches_pagesV2"
VISITED_FILE = "uscis_batches_visitedV2/visited_links.txt"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Agent/1.0; +https://yourdomain.com)"
}
BATCH_LIMIT = 1000

os.makedirs(PAGE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(VISITED_FILE), exist_ok=True)

def sanitize_filename(url):
    return re.sub(r'\W+', '_', url.strip('/')) + ".txt"

def load_visited_links():
    if not os.path.exists(VISITED_FILE):
        return set()
    with open(VISITED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def save_visited_link(url):
    with open(VISITED_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def is_valid_link(href):
    return href and href.startswith("/") and not any([
        href.startswith("/forms"),
        href.startswith("/sites"),
        href.endswith(".pdf"),
        "mailto:" in href,
        "javascript:" in href
    ])

def extract_clean_text(soup):
    content_div = soup.find("div", class_="region-content")
    if content_div:
        # Remove common headers/footers
        for tag in content_div.find_all(["header", "footer", "nav", "aside"]):
            tag.decompose()
        return content_div.get_text(separator="\n", strip=True)
    return ""

def upload_to_s3(local_file, s3_key):
    try:
        s3 = boto3.client("s3")
        s3.upload_file(local_file, AWS_BUCKET_NAME, s3_key)
        print(f"✅ Uploaded to S3: {s3_key}")
    except Exception as e:
        print(f"❌ Upload error: {e}")

def run_scraper():
    visited = load_visited_links()
    queue = {START_URL}
    processed = set(visited)
    scraped_count = 0

    while queue and scraped_count < BATCH_LIMIT:
        url = queue.pop()
        full_url = urljoin(BASE_URL, url)
        if full_url in processed:
            continue

        try:
            print(f"🔎 Scraping: {full_url}")
            res = requests.get(full_url, headers=HEADERS, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            text = extract_clean_text(soup)

            if text and len(text) > 100:
                filename = sanitize_filename(full_url)
                local_path = os.path.join(PAGE_DIR, filename)
                with open(local_path, "w", encoding="utf-8") as f:
                    f.write(f"{full_url}\n{text}")

                upload_to_s3(local_path, f"{PAGE_DIR}/{filename}")
                save_visited_link(full_url)
                scraped_count += 1

                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if is_valid_link(href):
                        queue.add(href)

            time.sleep(0.5)

        except Exception as e:
            print(f"❌ Failed: {e}")

    print(f"\n🎉 Scraped {scraped_count} new pages.")

if __name__ == "__main__":
    run_scraper()
