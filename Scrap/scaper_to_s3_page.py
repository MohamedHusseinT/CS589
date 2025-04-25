import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import os
import boto3
from datetime import datetime
import re

AWS_BUCKET_NAME = "cs589-aiproject"
BASE_URL = "https://www.uscis.gov"
START_URL = "https://www.uscis.gov/policy-manual"
BATCH_LIMIT = 1000
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Agent/1.0; +https://yourdomain.com)"
}

VISITED_DIR = "uscis_batches_visited"
PAGES_DIR = "uscis_batches_pages"
VISITED_FILE = os.path.join(VISITED_DIR, "visited_urls.txt")

os.makedirs(VISITED_DIR, exist_ok=True)
os.makedirs(PAGES_DIR, exist_ok=True)


def clean_text(text):
    """Remove headers/footers and boilerplate."""
    lines = text.strip().splitlines()
    filtered = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.search(r'uscis\.gov|last reviewed|last updated', line, re.IGNORECASE):
            continue
        if len(line) < 3:
            continue
        filtered.append(line)
    return "\n".join(filtered)


def chunk_text(text, max_length=800):
    """Split long text into chunks under max_length, preserving line boundaries."""
    chunks = []
    current_chunk = []
    current_len = 0

    for line in text.splitlines():
        if current_len + len(line) > max_length:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_len = 0
        current_chunk.append(line)
        current_len += len(line)

    if current_chunk:
        chunks.append("\n".join(current_chunk))
    return chunks


def slugify_url(url):
    path = urlparse(url).path.strip("/").replace("/", "_")
    return re.sub(r"[^\w\-_.]", "_", path) or "root"


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
            raw_text = content_div.get_text(separator="\n", strip=True)
            return clean_text(raw_text), soup
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
    return None, None


def upload_to_s3(file_path, s3_filename):
    try:
        s3 = boto3.client("s3")
        s3.upload_file(file_path, AWS_BUCKET_NAME, s3_filename)
        print(f"✅ Uploaded {file_path} to S3 as '{s3_filename}'")
    except Exception as e:
        print(f"❌ Failed to upload to S3: {e}")


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


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
        timestamp = get_timestamp()

        print(f"\n🚀 Starting Batch #{batch_number} - {timestamp}")

        while unprocessed_links and new_links_scraped < BATCH_LIMIT:
            current_url = unprocessed_links.pop()
            full_url = urljoin(BASE_URL, current_url)

            if full_url in processed_links:
                continue

            print(f"🔎 Scraping [{page_counter}]: {full_url}")
            text, soup = extract_text_from_page(full_url)

            if text:
                slug = slugify_url(full_url)
                chunks = chunk_text(text)

                for i, chunk in enumerate(chunks):
                    file_name = f"{timestamp}_{slug}_chunk{i+1}.txt"
                    file_path = os.path.join(PAGES_DIR, file_name)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(chunk)
                    upload_to_s3(file_path, f"uscis_batches_pages/{file_name}")

                save_visited_link(full_url)
                processed_links.add(full_url)
                new_links_scraped += 1
                page_counter += 1

            if soup:
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if is_valid_link(href):
                        full_href = urljoin(BASE_URL, href)
                        if full_href not in processed_links:
                            unprocessed_links.add(href)
                            internal_links_found += 1

            time.sleep(0.5)

        duration = round(time.time() - batch_start_time, 2)
        print(f"\n✅ Finished Batch #{batch_number}")
        print(f"📄 Pages scraped: {new_links_scraped}")
        print(f"🔗 New links found: {internal_links_found}")
        print(f"⏱️ Duration: {duration} seconds")

        upload_to_s3(VISITED_FILE, f"uscis_batches_visited/visited_urls_{timestamp}.txt")

        if new_links_scraped == 0:
            print("🎉 All available links scraped.")
            break

        batch_number += 1
        print("🔄 Starting next batch...\n")


if __name__ == "__main__":
    run_continuous_scraper()
