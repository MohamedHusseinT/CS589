
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import os
import boto3
from datetime import datetime

AWS_BUCKET_NAME = "cs589-aiproject"
BASE_URL = "https://www.uscis.gov"
START_URL = "https://www.uscis.gov/policy-manual"
BATCH_LIMIT = 1000
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Agent/1.0; +https://yourdomain.com)"
}

VISITED_DIR = "uscis_batches_visited"
PAGES_DIR = "uscis_batches_pages"
VISITED_FILE = os.path.join(VISITED_DIR, "visited_all.txt")

os.makedirs(VISITED_DIR, exist_ok=True)
os.makedirs(PAGES_DIR, exist_ok=True)

def load_visited_links():
    if not os.path.exists(VISITED_FILE):
        return set()
    with open(VISITED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

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

def extract_text_from_page(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        content_div = soup.find("div", class_="region-content")
        if content_div:
            text = content_div.get_text(separator="\n", strip=True)
            return text, soup
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
    return None, None

def upload_to_s3(file_path, s3_filename):
    try:
        s3 = boto3.client("s3")
        s3.upload_file(file_path, AWS_BUCKET_NAME, s3_filename)
        print(f"✅ Uploaded {file_path} to S3 bucket '{AWS_BUCKET_NAME}' as '{s3_filename}'")
    except Exception as e:
        print(f"❌ Failed to upload to S3: {e}")

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def sanitize_filename(url):
    return url.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_").replace("&", "_")

def save_text_chunks(text, base_filename, url):
    chunk_size = 1000
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i+chunk_size]
        chunk_filename = f"{base_filename}_chunk_{i//chunk_size + 1}.txt"
        chunk_path = os.path.join(PAGES_DIR, chunk_filename)
        with open(chunk_path, "w", encoding="utf-8") as f:
            f.write(f"---\n{url}\n{chunk}\n")
        upload_to_s3(chunk_path, f"uscis_batches/{chunk_filename}")

def run_continuous_scraper():
    visited_links = load_visited_links()
    processed_links = set(visited_links)
    unprocessed_links = set([START_URL])
    batch_number = 1

    while True:
        new_links_scraped = 0
        page_counter = 1
        internal_links_found = 0
        batch_start_time = time.time()

        print(f"\n🚀 Starting Batch #{batch_number}")
        while unprocessed_links and new_links_scraped < BATCH_LIMIT:
            current_url = unprocessed_links.pop()
            full_url = urljoin(BASE_URL, current_url)

            if full_url in processed_links:
                continue

            print(f"🔎 Scraping [{page_counter}]: {full_url}")
            text, soup = extract_text_from_page(full_url)

            if text:
                file_base = sanitize_filename(full_url)
                save_text_chunks(text, file_base, full_url)
                new_links_scraped += 1
                page_counter += 1
                save_visited_link(full_url)
                processed_links.add(full_url)

            if soup:
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if is_valid_link(href):
                        full_href = urljoin(BASE_URL, href)
                        if full_href not in processed_links:
                            unprocessed_links.add(href)
                            internal_links_found += 1

            time.sleep(0.5)

        batch_duration = round(time.time() - batch_start_time, 2)
        print(f"\n✅ Finished Batch #{batch_number}")
        print(f"📄 Pages scraped: {new_links_scraped}")
        print(f"🔗 New internal links discovered: {internal_links_found}")
        print(f"⏱️ Time taken: {batch_duration} seconds")

        if new_links_scraped == 0:
            print("🎉 All available USCIS links have been scraped. Exiting loop.")
            break

        batch_number += 1
        print("🔄 Starting next batch...\n")

if __name__ == "__main__":
    run_continuous_scraper()
