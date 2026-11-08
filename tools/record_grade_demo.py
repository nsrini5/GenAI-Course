"""
record_grade_demo.py - Playwright "robot" that demonstrates grade_app.py and
records the whole screen while it does so (macOS).

1. Terminal 1:   cd "/Users/srini/GenAI Course/grade-app"
                 source venv/bin/activate
                 streamlit run grade_app.py
2. Terminal 2:   cd "/Users/srini/GenAI Course/grade-app"
                 source venv/bin/activate
                 python ../tools/record_grade_demo.py

What the robot shows:
  a) the plain `students = []` experiment - the first student disappears
  b) the session_state version - five students, table + metrics update each time
  c) a mark of 105 and an empty name being rejected
Saves:  ~/Downloads/grade_app_demo_<date>.mov
        grade-app/grade_app_screenshot.png  (browser with several students)
"""
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

APP_URL = "http://localhost:8501"
VIDEO = Path.home() / "Downloads" / f"grade_app_demo_{datetime.now():%Y-%m-%d}.mov"
SCREENSHOT = Path.cwd() / "grade_app_screenshot.png"
RECORD_SECONDS = 110
PAUSE = 2.0
HEADLESS_TEST = "--test" in sys.argv          # used only for checking without recording

STUDENTS = [("Priya", 92), ("Arun", 78), ("Divya", 83), ("Karthik", 59), ("Meena", 100)]


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def pause(seconds=PAUSE):
    if not HEADLESS_TEST:
        time.sleep(seconds)


def add_student(page, name, mark):
    page.get_by_label("Name").fill("")
    page.get_by_label("Name").type(name, delay=0 if HEADLESS_TEST else 90)
    mark_box = page.get_by_label("Mark")
    mark_box.fill("")
    mark_box.type(str(mark), delay=0 if HEADLESS_TEST else 120)
    page.get_by_role("button", name="Add").click()
    # wait for Streamlit to finish re-running the script
    page.get_by_text(f"Added {name}:").wait_for()
    pause()


def wait_rows(page, n):
    """Wait until the results table shows exactly n students."""
    page.wait_for_function(
        f"document.querySelectorAll('table tbody tr').length === {n}", timeout=15_000)
    return n


def set_plain_list(page, on):
    toggle = page.get_by_role("switch")          # the sidebar toggle
    if toggle.is_checked() != on:
        page.get_by_text("Experiment: plain").click()
        page.wait_for_function(
            f"document.querySelector('input[role=switch]').checked === {str(on).lower()}")
        page.wait_for_timeout(1000)               # let the rerun finish
    pause()


def main():
    try:
        urllib.request.urlopen(APP_URL, timeout=3)
    except Exception:
        sys.exit("The app is not running. Start it first:  streamlit run grade_app.py")

    rec = None
    if not HEADLESS_TEST:
        log(f"Recording the screen for {RECORD_SECONDS} s -> {VIDEO}")
        rec = subprocess.Popen(["screencapture", "-v", "-C", "-V", str(RECORD_SECONDS), str(VIDEO)],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
        time.sleep(2)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=HEADLESS_TEST)
        except Exception:
            browser = p.chromium.launch(headless=HEADLESS_TEST)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(APP_URL)
        page.get_by_label("Name").wait_for()
        pause()

        log("a) Plain list experiment: add two students")
        set_plain_list(page, True)
        add_student(page, "Priya", 92)
        wait_rows(page, 1)
        add_student(page, "Arun", 78)
        wait_rows(page, 1)
        log("   table still has only 1 row (Arun) - Priya was lost on the rerun")
        pause(3)

        log("b) session_state version: add five students")
        set_plain_list(page, False)
        for n, (name, mark) in enumerate(STUDENTS, start=1):
            add_student(page, name, mark)
            log(f"   added {name} {mark} - table rows: {wait_rows(page, n)}")

        page.screenshot(path=str(SCREENSHOT), full_page=True)
        log(f"Screenshot with {len(STUDENTS)} students saved -> {SCREENSHOT}")

        log("c) Invalid input: mark 105, then an empty name")
        page.get_by_label("Name").fill("")
        page.get_by_label("Name").type("Test", delay=0 if HEADLESS_TEST else 90)
        mark_box = page.get_by_label("Mark")
        mark_box.fill("")
        mark_box.type("105", delay=0 if HEADLESS_TEST else 120)
        page.get_by_role("button", name="Add").click()
        page.get_by_text("outside the allowed range").wait_for()
        log("   105 rejected: 'Number is outside the allowed range'")
        pause(3)
        page.get_by_label("Name").fill("")
        mark_box.fill("")
        mark_box.press("Tab")
        page.get_by_role("button", name="Add").click()
        page.get_by_text("Please enter a name.").wait_for()
        log("   empty name rejected: 'Please enter a name.'")
        wait_rows(page, len(STUDENTS))
        pause()

        pause(3)
        browser.close()

    if rec:
        log("Demo finished - waiting for the recording to save...")
        rec.wait(timeout=RECORD_SECONDS + 60)
        log(f"Saved {VIDEO}" if VIDEO.exists() else "Recording not saved - check Screen Recording permission")


if __name__ == "__main__":
    main()
