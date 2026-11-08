"""
cricbuzz_score.py - Week 1 · Day 3 · Task 1: Capture a live cricket score with Playwright

Opens cricbuzz.com in a real browser, WAITS for the score cards that
JavaScript adds after the page loads, prints the latest score and saves
a screenshot as score.png.

Run headed (watch the browser):   python cricbuzz_score.py
Run headless (no window):         python cricbuzz_score.py --headless
"""
import re
import sys

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

URL = "https://www.cricbuzz.com/"

# Found with Chrome -> right-click the score -> Inspect.
# Each match card on the home page is a link to its live-score page:
#   <a href="https://www.cricbuzz.com/live-cricket-scores/..." class="h-full block w-[316px]">
# Checked in the browser console first:
#   document.querySelectorAll("a[href*='/live-cricket-scores/'][class*='w-[316px]']")
SCORE_CARD = "a[href*='/live-cricket-scores/'][class*='w-[316px]']"

# Text that looks like a score: 147-2, 287/4, 134 (41), 356 & 147-2
SCORE_PATTERN = re.compile(r"\d+\s*[-/]\s*\d+|\d+\s*\(\d+(\.\d)?\)")
# Words that mean the match is already over (used to prefer a LIVE match)
FINISHED = ("won", "drawn", "draw", "tied", "abandoned", "no result")

HEADLESS = "--headless" in sys.argv


def tidy(card_text):
    """Turn the card's raw text into two clean lines, e.g.
    'Test | WI 356 & 147-2 | BAN 386'  and  'Day 4: ... lead by 117 runs'."""
    lines = []
    for line in card_text.splitlines():
        line = line.strip()
        if not line or line.upper() == "WATCH NOW":
            continue
        if lines and lines[-1] == line:          # team names appear twice
            continue
        lines.append(line)

    parts, i = [], 0
    while i < len(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if nxt and SCORE_PATTERN.search(nxt) and not SCORE_PATTERN.search(lines[i]):
            parts.append(f"{lines[i]} {nxt}")    # team + its score
            i += 2
        else:
            parts.append(lines[i])
            i += 1

    status = parts.pop() if len(parts) > 1 else ""
    return " | ".join(parts), status


def pick_card(cards):
    """Prefer a match that is still in progress; otherwise the latest result."""
    texts = [cards.nth(i).inner_text() for i in range(cards.count())]
    with_score = [i for i, t in enumerate(texts) if SCORE_PATTERN.search(t)]
    for i in with_score:
        if not any(word in texts[i].lower() for word in FINISHED):
            return i, texts[i], True
    if with_score:
        return with_score[0], texts[with_score[0]], False
    return None, None, False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=0 if HEADLESS else 400)
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        print(f"Opening {URL} ({'headless' if HEADLESS else 'headed'}) ...")
        page.goto(URL, wait_until="domcontentloaded", timeout=60_000)

        # Wait for the score cards themselves - no fixed sleep().
        try:
            page.wait_for_selector(SCORE_CARD, state="visible", timeout=20_000)
        except PlaywrightTimeout:
            print("No score cards appeared within 20 s - Cricbuzz may be slow "
                  "or its layout has changed.")
            page.screenshot(path="score.png")
            print("\nsaved score.png")
            browser.close()
            sys.exit(1)

        cards = page.locator(SCORE_CARD)
        index, text, is_live = pick_card(cards)

        if index is None:
            print("No live match right now - Cricbuzz shows only upcoming fixtures.")
        else:
            card = cards.nth(index)
            card.scroll_into_view_if_needed()
            card.hover()                          # highlight the card we read
            score, status = tidy(text)
            if not is_live:
                print("No match is live right now - latest result:")
            print(score)
            if status:
                print(status)

        page.screenshot(path="score.png")
        print("\nsaved score.png")
        browser.close()


if __name__ == "__main__":
    main()
