"""
Step 1: Scrape the TN Govt scheme list page + every scheme detail page it links to.
Output: data/raw/schemes.jsonl  (one JSON record per page: url, title, text)

Run:  python 1_scrape.py
"""
import json
import sys
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

LIST_URL = "https://www.tn.gov.in/scheme_list.php?dep_id=Mg=="
BASE = "https://www.tn.gov.in/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh) TN-Schemes-RAG/1.0 (personal research)"}
DELAY_SEC = 2          # be polite to a government server
OUT = Path("data/raw/schemes.jsonl")


def robots_allows(url: str) -> bool:
    rp = urllib.robotparser.RobotFileParser(urljoin(BASE, "/robots.txt"))
    try:
        rp.read()
    except Exception:
        return True  # robots.txt unreachable -> assume allowed
    return rp.can_fetch(HEADERS["User-Agent"], url)


def fetch(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding  # handles Tamil text correctly
    return BeautifulSoup(r.text, "lxml")


def clean_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "form", "iframe"]):
        tag.decompose()
    main = soup.find("main") or soup.find(id="content") or soup.find(class_="content") or soup.body or soup
    lines = [ln.strip() for ln in main.get_text("\n").splitlines()]
    return "\n".join(ln for ln in lines if ln)


def find_scheme_links(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Return (title, absolute_url) for links that look like scheme detail pages."""
    links, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full = urljoin(LIST_URL, href)
        p = urlparse(full)
        if p.netloc and "tn.gov.in" not in p.netloc:
            continue
        low = full.lower()
        if "scheme" in low and "scheme_list" not in low and full not in seen:
            seen.add(full)
            links.append((a.get_text(" ", strip=True) or full, full))
    return links


def main():
    if not robots_allows(LIST_URL):
        print(
            "\n[STOP] tn.gov.in's robots.txt does not allow automated fetching of this page.\n"
            "Use the manual route instead:\n"
            "  1. Open the scheme list page in Safari/Chrome.\n"
            "  2. Open each scheme, press Cmd+S (Format: 'Web Page, Complete' or 'Page Source'),\n"
            "     or File > Export as PDF, and save into:  data/manual/\n"
            "  3. Then run:  python 2_build_index.py\n"
        )
        sys.exit(1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    print(f"Fetching list page: {LIST_URL}")
    list_soup = fetch(LIST_URL)
    records = [{"url": LIST_URL, "title": "Scheme list", "text": clean_text(fetch(LIST_URL))}]

    links = find_scheme_links(list_soup)
    print(f"Found {len(links)} scheme links")

    for i, (title, url) in enumerate(links, 1):
        if not robots_allows(url):
            print(f"  skip (robots): {url}")
            continue
        try:
            time.sleep(DELAY_SEC)
            soup = fetch(url)
            page_title = soup.title.get_text(strip=True) if soup.title else title
            text = clean_text(soup)
            records.append({"url": url, "title": title or page_title, "text": text})
            print(f"  [{i}/{len(links)}] {title[:70]}  ({len(text)} chars)")
        except Exception as e:
            print(f"  [{i}] FAILED {url}: {e}")

    with OUT.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nSaved {len(records)} pages -> {OUT}")


if __name__ == "__main__":
    main()
