"""
Week 3 - Day 5: Print the Top 5 Headlines from a News Site
Fetches BBC News with requests and extracts headlines with BeautifulSoup.

Selector found by inspecting the page (right-click a headline > Inspect):
    <h2 data-testid="card-headline" class="IndexCardHeading-styles__...">...</h2>
The class names are auto-generated and change between deployments, so the
script uses the stable data-testid attribute instead. Section titles such as
"Most read" use a different data-testid, so they are not picked up.
"""

import sys

import requests
from bs4 import BeautifulSoup

URL = "https://www.bbc.com/news"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}
SELECTOR = 'h2[data-testid="card-headline"]'
TOP_N = 5


def fetch_page(url):
    """Download the page and return its HTML, or exit with a clear message."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
    except requests.RequestException as err:
        sys.exit(f"Could not reach {url}: {err}")

    if response.status_code != 200:
        sys.exit(f"Request failed: HTTP {response.status_code} from {url}")
    return response.text


def extract_headlines(html, limit=TOP_N):
    """Return up to `limit` unique, non-empty headlines in page order."""
    soup = BeautifulSoup(html, "html.parser")
    headlines = []
    seen = set()
    for tag in soup.select(SELECTOR):
        text = tag.get_text(strip=True)
        if not text or text in seen:
            continue  # skip empty and duplicate entries
        seen.add(text)
        headlines.append(text)
        if len(headlines) == limit:
            break
    return headlines


def main():
    html = fetch_page(URL)
    headlines = extract_headlines(html)

    if not headlines:
        print("No headlines found. The page layout may have changed, or the "
              "headlines are loaded with JavaScript.")
        return

    if len(headlines) < TOP_N:
        print(f"Only {len(headlines)} headline(s) found:")

    for i, headline in enumerate(headlines, 1):
        print(f"{i}. {headline}")


if __name__ == "__main__":
    main()
