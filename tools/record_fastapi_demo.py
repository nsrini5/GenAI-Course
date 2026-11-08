"""
record_fastapi_demo.py - a Playwright "robot" that demonstrates the FastAPI app
and records the whole screen while it does so (macOS).

1. In one VS Code terminal start the app:
       cd "/Users/srini/GenAI Course/fastapi-basic-app"
       source venv/bin/activate
       uvicorn main:app --reload
2. In a second terminal (click + in the terminal panel):
       cd "/Users/srini/GenAI Course/fastapi-basic-app"
       source venv/bin/activate
       python "../tools/record_fastapi_demo.py"

The robot opens Chrome, visits every endpoint, then uses /docs to
"Try it out" and "Execute" each endpoint. The recording is saved to
~/Downloads/fastapi_demo_<date>.mov
"""
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
VIDEO = Path.home() / "Downloads" / f"fastapi_demo_{datetime.now():%Y-%m-%d}.mov"
RECORD_SECONDS = 50
PAUSE = 2.5            # seconds to let the viewer read each screen


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def show(page, path, note):
    log(f"GET {path}  - {note}")
    page.goto(BASE_URL + path)
    page.wait_for_selector("body")
    # Chrome's JSON viewer: tick "Pretty-print" and enlarge the text for the video
    pretty = page.locator("input[type=checkbox]")
    if pretty.count():
        pretty.first.check()
    page.evaluate("document.body.style.zoom = '1.8'")
    time.sleep(PAUSE)


def try_in_docs(page, operation_id, fields):
    """Expand an endpoint in /docs, click Try it out, fill values, Execute."""
    block = page.locator(f"#operations-{operation_id}")
    block.locator(".opblock-summary").click()
    block.locator("button.try-out__btn").click()
    for name, value in fields.items():
        box = block.locator(f"tr[data-param-name='{name}'] input")
        box.click()
        box.fill("")
        box.type(value, delay=120)            # visible typing for the video
    block.locator("button.execute").click()
    block.locator(".live-responses-table .response-col_description").first.wait_for()
    block.locator(".live-responses-table").first.scroll_into_view_if_needed()
    time.sleep(PAUSE + 1)


def main():
    try:
        import urllib.request
        urllib.request.urlopen(BASE_URL, timeout=3)
    except Exception:
        sys.exit("The app is not running. Start it first:  uvicorn main:app --reload")

    log(f"Recording the screen for {RECORD_SECONDS} s -> {VIDEO}")
    rec = subprocess.Popen(["screencapture", "-v", "-C", "-V", str(RECORD_SECONDS), str(VIDEO)],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    time.sleep(2)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=False,
                                        args=["--window-position=0,0"])
        except Exception:
            browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1280, "height": 760})

        show(page, "/", "root endpoint - welcome JSON")
        show(page, "/greet/Srini", "path parameter")
        show(page, "/greet/Srini?language=ta", "path + query parameter")
        show(page, "/add?a=12&b=30.5", "two query parameters")
        show(page, "/add?a=12", "b left out ON PURPOSE -> FastAPI answers 422 'Field required' (expected)")

        log("Opening the interactive docs at /docs")
        page.goto(BASE_URL + "/docs")
        page.wait_for_selector(".opblock-summary")
        time.sleep(PAUSE)
        try_in_docs(page, "Welcome-read_root__get", {})
        try_in_docs(page, "Greeting-greet_greet__name__get", {"name": "Naruvi", "language": "hi"})
        try_in_docs(page, "Calculator-add_add_get", {"a": "250", "b": "750"})
        page.mouse.wheel(0, -4000)
        time.sleep(PAUSE)
        browser.close()

    log("Demo finished - all endpoints shown. Waiting for the recording to save...")
    rec.wait(timeout=RECORD_SECONDS + 60)
    log(f"Saved {VIDEO}" if VIDEO.exists() else "Recording was not saved - check Screen Recording permission")


if __name__ == "__main__":
    main()
