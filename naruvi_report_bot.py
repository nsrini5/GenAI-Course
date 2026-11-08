"""
naruvi_report_bot.py  -  Gen AI Architect Program, Assignment 1 (PyAutoGUI)
=========================================================================
macOS version.

What the bot does, on screen, like a person would:
  1. Opens Google Chrome and goes to the Naruvi Hospitals website.
  2. Scrolls to the bottom, searches for "Facilities" (Cmd+F) and opens it.
  3. Copies ALL the text on the Facilities page and takes a screenshot of it.
  4. Opens Microsoft Excel and adds a new row:
        date & time | facilities summary | comment
     -> saves  daily_report_YYYY-MM-DD.xlsx  + a screenshot of the sheet.
  5. Opens Microsoft Word and writes the report
     (date & time, source, the FULL Facilities page text, screenshot, comment)
     -> saves  daily_naruvi_report_YYYY-MM-DD.docx  + a screenshot of it.

Before the first run (one time only):
  * System Settings > Privacy & Security > Accessibility     -> allow Terminal
  * System Settings > Privacy & Security > Screen Recording  -> allow Terminal
    (use "Visual Studio Code" instead of Terminal if you run it from VS Code)
  * Open Excel and Word once and close any welcome / sign-in screens.

Safety: move the mouse into any screen corner to stop the bot (FAILSAFE).
"""

import os
import subprocess
import sys
import time
from datetime import datetime

import pyautogui
import pyperclip
from openpyxl import Workbook, load_workbook
from docx import Document
from PIL import Image

# ---------------------------------------------------------------------------
# Settings you may want to change
# ---------------------------------------------------------------------------
SITE_URL = "https://www.naruvihospitals.com/"
SITE_NAME = "Naruvi Hospitals, Vellore"
# Menu links to try, in order. The first one found on the page is opened.
# Change this list if the menu on the website uses different words.
SECTION_LINK_TEXTS = ["Facilities", "Our Facilities", "FACILITIES"]
COMMENT = "Useful snapshot of Naruvi Hospitals' facilities"

# If find-in-page cannot click a link on your screen, run
#     python3 daily_report_bot.py --where
# hover over the link, note the X/Y it prints, and put it here, e.g. (1180, 95)
SECTION_CLICK_XY = None

# Waits in seconds - increase these if your internet or Mac is slow
APP_OPEN_WAIT = 5
PAGE_LOAD_WAIT = 6
SHORT_WAIT = 1.0

# ---------------------------------------------------------------------------
# Run-time values (generated automatically, never typed by hand)
# ---------------------------------------------------------------------------
NOW = datetime.now()
TODAY = NOW.strftime("%Y-%m-%d")
TIMESTAMP = NOW.strftime("%Y-%m-%d %H:%M:%S")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHOT_DIR = os.path.join(BASE_DIR, "screenshots")
os.makedirs(SHOT_DIR, exist_ok=True)

XLSX_PATH = os.path.join(BASE_DIR, f"daily_report_{TODAY}.xlsx")
DOCX_PATH = os.path.join(BASE_DIR, f"daily_naruvi_report_{TODAY}.docx")
PAGE_SHOT = os.path.join(SHOT_DIR, f"naruvi_page_{TODAY}.png")
EXCEL_SHOT = os.path.join(SHOT_DIR, f"daily_report_{TODAY}.png")
WORD_SHOT = os.path.join(SHOT_DIR, f"daily_naruvi_report_{TODAY}.png")
VIDEO_RAW = os.path.join(BASE_DIR, f"bot_recording_raw_{TODAY}.mov")

VERSION = "v10 (safe Excel retry, longer video)"

pyautogui.FAILSAFE = True   # mouse to a corner = emergency stop
pyautogui.PAUSE = 0.3       # small pause after every pyautogui action


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def hotkey(*keys):
    """Mac-safe shortcut: press keys down one by one, release in reverse.
    (pyautogui.hotkey is sometimes too fast for macOS and misses the Cmd key.)"""
    for k in keys:
        pyautogui.keyDown(k)
        time.sleep(0.05)
    for k in reversed(keys):
        pyautogui.keyUp(k)
        time.sleep(0.05)
    time.sleep(0.3)


def osascript(script):
    """Run a short AppleScript and return its output (empty string on error)."""
    result = subprocess.run(["osascript", "-e", script],
                            capture_output=True, text=True)
    return result.stdout.strip()


def frontmost_app():
    return osascript('tell application "System Events" to get name of '
                     'first application process whose frontmost is true')


def focus(app_name, timeout=15):
    """Bring an app to the front and wait until macOS confirms it is in front."""
    osascript(f'tell application "{app_name}" to activate')
    end = time.time() + timeout
    while time.time() < end:
        front = frontmost_app()
        if front and app_name.lower().split()[-1] in front.lower():
            time.sleep(SHORT_WAIT)
            return True
        time.sleep(0.5)
    log(f"  ! could not confirm {app_name} is in front - continuing anyway")
    return False


def paste_text(text):
    """Put text on the clipboard and paste it (handles any characters)."""
    pyperclip.copy(text)
    time.sleep(0.2)
    hotkey("command", "v")


def copy_image_to_clipboard(png_path):
    """Put a PNG on the macOS clipboard so it can be pasted into Word."""
    osascript(f'set the clipboard to (read (POSIX file "{png_path}") '
              f'as «class PNGf»)')
    time.sleep(0.5)


def current_url():
    """Read Chrome's address bar the way a person would: Cmd+L, Cmd+C."""
    hotkey("command", "l")
    hotkey("command", "c")
    pyautogui.press("escape")
    time.sleep(0.3)
    return pyperclip.paste().strip()


def copy_page_text():
    """Select all text on the page and copy it."""
    pyperclip.copy("")
    pyautogui.press("escape")
    time.sleep(0.3)
    hotkey("command", "a")
    hotkey("command", "c")
    time.sleep(SHORT_WAIT)
    pyautogui.click(pyautogui.size().width // 2, pyautogui.size().height // 2)
    return pyperclip.paste()


def scroll_to_bottom():
    """Scroll down the page with the mouse wheel, like a person reading it."""
    w, h = pyautogui.size()
    pyautogui.moveTo(w // 2, h // 2, duration=0.4)
    for _ in range(25):
        pyautogui.scroll(-10)
        time.sleep(0.15)
    hotkey("command", "down")           # make sure we reach the very bottom
    time.sleep(SHORT_WAIT)


def click_link_by_text(link_text, fallback_xy=None, from_bottom=False):
    """Click a link the way a person would, without hard-coded positions:
    Cmd+F -> type the link text -> Esc (Chrome moves focus to the found link)
    -> Enter (opens it). If a fallback X/Y is set, click there instead."""
    before = current_url()
    if fallback_xy:
        log(f"  clicking '{link_text}' at {fallback_xy}")
        pyautogui.moveTo(*fallback_xy, duration=0.6)
        pyautogui.click()
    else:
        log(f"  finding '{link_text}' on the page and opening it")
        hotkey("command", "f")
        pyautogui.write(link_text, interval=0.05)
        time.sleep(SHORT_WAIT)
        if from_bottom:
            # Shift+Enter jumps back from the first match to the LAST one,
            # i.e. the 'Facilities' link in the footer at the bottom.
            hotkey("shift", "enter")
            time.sleep(SHORT_WAIT)
        pyautogui.press("escape")
        time.sleep(0.5)
        pyautogui.press("enter")
    time.sleep(PAGE_LOAD_WAIT)
    after = current_url()
    moved = after != before
    log(f"  page {'changed' if moved else 'did NOT change'} -> {after}")
    return moved


def pick_headline(page_text):
    """Pick the first line that looks like a news headline."""
    skip = ("book an appointment", "call", "menu", "cookie", "privacy",
            "copyright", "all rights", "login", "@", "+91")
    for line in page_text.splitlines():
        line = line.strip()
        if 25 <= len(line) <= 200 and len(line.split()) >= 4 \
                and not any(w in line.lower() for w in skip):
            return line
    return "Highlight not found - see screenshot"


def tidy_text(page_text):
    """Keep ALL text lines from the page (short facility names included),
    dropping only blank lines and back-to-back duplicates."""
    lines, last = [], None
    for l in page_text.splitlines():
        l = l.strip()
        if l and l != last:
            lines.append(l)
        last = l
    return "\n".join(lines)


def summarise(text, max_chars=300):
    """Short one-line version of the page for the Excel cell.
    Skips the website menu at the top and starts at the first real
    content sentence (e.g. "South Asia's first ever Robotic Hybrid ...")."""
    noise = ("image", "logo", "chervon", "360")
    lines = [l for l in text.splitlines()
             if len(l) > 1 and not any(n in l.lower() for n in noise)]
    start = 0
    for i, l in enumerate(lines):
        if "unmatched care" in l.lower():       # last line of the page header
            start = i + 1
            break
    else:
        for i, l in enumerate(lines):           # fallback: first long sentence
            if len(l.split()) >= 7:
                start = i
                break
    joined = " | ".join(lines[start:])
    return joined[:max_chars] + ("..." if len(joined) > max_chars else "")


def screenshot(path, shrink_to=None):
    img = pyautogui.screenshot()
    if shrink_to and img.width > shrink_to:
        ratio = shrink_to / img.width
        img = img.resize((shrink_to, int(img.height * ratio)), Image.LANCZOS)
    img.save(path)
    log(f"  screenshot saved -> {path}")


# ---------------------------------------------------------------------------
# Step A - Chrome: Naruvi Hospitals home -> highlight -> section page
# ---------------------------------------------------------------------------
def chrome_part():
    log("STEP A: Chrome")
    subprocess.run(["open", "-a", "Google Chrome", SITE_URL])
    time.sleep(APP_OPEN_WAIT)
    focus("Google Chrome")
    time.sleep(PAGE_LOAD_WAIT)

    log("  scrolling to the bottom of the home page")
    scroll_to_bottom()

    section = None
    if SECTION_CLICK_XY:
        if click_link_by_text("section", SECTION_CLICK_XY):
            section = "selected"
    else:
        for name in SECTION_LINK_TEXTS:
            log(f"  searching for '{name}' at the bottom of the page")
            if click_link_by_text(name, from_bottom=True):
                section = name
                break
            focus("Google Chrome")
        if not section:                 # fallback: the top menu link
            for name in SECTION_LINK_TEXTS:
                log(f"  trying the top menu link '{name}'")
                if click_link_by_text(name):
                    section = name
                    break
                focus("Google Chrome")
    if not section:
        log("  ! Facilities link not opened - capturing the current page")

    log("  copying ALL text on the page")
    page_text = tidy_text(copy_page_text())
    if not page_text:
        page_text = "No text could be copied from this page. See the screenshot below."
    with open(os.path.join(BASE_DIR, f"naruvi_facilities_{TODAY}.txt"), "w") as f:
        f.write(page_text)                       # plain-text backup copy
    log(f"  copied {len(page_text.splitlines())} lines")
    screenshot(PAGE_SHOT, shrink_to=1600)
    headline = summarise(page_text)
    return headline, page_text, section


# ---------------------------------------------------------------------------
# Shared helpers for Excel / Word
# ---------------------------------------------------------------------------
def quit_app(app_name):
    """Close an app WITHOUT saving, so no old window or stuck dialog
    (like a leftover Go To box) is left open. Force-quits if it won't close."""
    osascript(f'if application "{app_name}" is running then '
              f'tell application "{app_name}" to quit saving no')
    time.sleep(3)
    if subprocess.run(["pgrep", "-x", app_name], capture_output=True).returncode == 0:
        log(f"  {app_name} did not close - force quitting it")
        subprocess.run(["killall", app_name], capture_output=True)
        time.sleep(3)
    for f in os.listdir(BASE_DIR):              # remove Office lock files
        if f.startswith("~$"):
            try:
                os.remove(os.path.join(BASE_DIR, f))
            except OSError:
                pass


def ensure_front(app_name):
    """Make sure the right app is in front BEFORE every key press group.
    Stops other windows (e.g. iPhone Mirroring) from receiving our typing."""
    for _ in range(3):
        if focus(app_name, timeout=5):
            return
    raise RuntimeError(f"{app_name} would not come to the front - stopping "
                       f"so we don't type into the wrong window.")


# ---------------------------------------------------------------------------
# Step B - Excel: new row with date & time, fetched data, comment
# ---------------------------------------------------------------------------
def prepare_workbook():
    """Make sure today's file exists with headers, and make Excel open it with
    the next empty cell (A2, A3, ...) already selected - no Go To box needed."""
    if os.path.exists(XLSX_PATH):
        wb = load_workbook(XLSX_PATH)
        ws = wb.active
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Daily Report"
        ws.append(["Date & Time",
                   "Fetched Data (Naruvi Hospitals - Facilities page)",
                   "Comment"])
        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["B"].width = 90
        ws.column_dimensions["C"].width = 40
    next_row = ws.max_row + 1
    ws.sheet_view.selection[0].activeCell = f"A{next_row}"
    ws.sheet_view.selection[0].sqref = f"A{next_row}"
    wb.save(XLSX_PATH)
    return next_row


def excel_part(headline):
    log("STEP B: Excel")
    quit_app("Microsoft Excel")
    next_row = prepare_workbook()
    log(f"  opening the workbook with cell A{next_row} selected")
    subprocess.run(["open", "-a", "Microsoft Excel", XLSX_PATH])
    time.sleep(APP_OPEN_WAIT + 3)
    ensure_front("Microsoft Excel")
    pyautogui.press("escape")           # clear any start-up pop-up

    log("  filling the new row (one paste fills A, B and C)")
    time.sleep(1.5)                     # let Excel settle before pasting
    row_text = "\t".join([TIMESTAMP, headline, COMMENT])
    ensure_front("Microsoft Excel")
    paste_text(row_text)                # Tab-separated text = 3 cells
    time.sleep(1.5)
    pyautogui.press("escape")           # leave the paste options menu
    time.sleep(0.5)

    log("  saving the workbook (Cmd+S)")
    ensure_front("Microsoft Excel")
    hotkey("command", "s")
    time.sleep(3)
    screenshot(EXCEL_SHOT)
    osascript('tell application "Microsoft Excel" to close active workbook saving yes')
    time.sleep(2)

    # Check the saved file really has the new row
    ws = load_workbook(XLSX_PATH).active
    row = [ws.cell(next_row, c).value for c in (1, 2, 3)]
    if row[2] == COMMENT and row[0]:
        log(f"  CHECK OK - row {next_row} saved: {row[0]} | {str(row[1])[:40]}... | {row[2]}")
        return True
    log(f"  CHECK FAILED - row {next_row} in the saved file is {row}")
    return False


# ---------------------------------------------------------------------------
# Step C - Word: write the Naruvi Hospitals report
# ---------------------------------------------------------------------------
def word_part(page_text, section):
    log("STEP C: Word")
    quit_app("Microsoft Word")
    Document().save(DOCX_PATH)          # fresh empty document for today
    subprocess.run(["open", "-a", "Microsoft Word", DOCX_PATH])
    time.sleep(APP_OPEN_WAIT + 3)
    ensure_front("Microsoft Word")
    pyautogui.press("escape")           # clear any start-up pop-up
    section = section or "current"

    report_text = (
        f"Daily Naruvi Hospitals Report - {TODAY}\n\n"
        f"Generated on: {TIMESTAMP}\n"
        f"Source: {SITE_NAME} - {SITE_URL}\n\n"
        f"Full content of the {section} page:\n\n"
        f"{page_text}\n"
    )

    log("  pasting the report text")
    ensure_front("Microsoft Word")
    paste_text(report_text)
    time.sleep(2)

    log("  pasting the page screenshot")
    ensure_front("Microsoft Word")
    pyautogui.press("enter")
    copy_image_to_clipboard(PAGE_SHOT)
    hotkey("command", "v")
    time.sleep(3)

    log("  adding the comment")
    ensure_front("Microsoft Word")
    pyautogui.press("enter")
    paste_text(f"Comment: {COMMENT}")
    time.sleep(1)

    log("  saving the document (Cmd+S)")
    ensure_front("Microsoft Word")
    hotkey("command", "home")           # back to the top for the screenshot
    time.sleep(SHORT_WAIT)
    hotkey("command", "s")
    time.sleep(3)
    screenshot(WORD_SHOT)
    # Close the document, saving any last change, so Word never asks
    # "Do you want to save?" (AutoSave only works for OneDrive files).
    osascript('tell application "Microsoft Word" to close active document saving yes')
    time.sleep(2)

    # Check the saved document really has the content and the screenshot.
    doc = Document(DOCX_PATH)
    words = sum(len(p.text.split()) for p in doc.paragraphs)
    images = len(doc.inline_shapes)
    if images == 0 and os.path.exists(PAGE_SHOT):
        log("  screenshot missing in Word - adding it on its own last page")
        from docx.shared import Inches
        from docx.enum.text import WD_BREAK
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        doc.add_paragraph(f"Screenshot of the {section} page ({TIMESTAMP}):")
        doc.add_picture(PAGE_SHOT, width=Inches(6))
        doc.save(DOCX_PATH)
        images = len(Document(DOCX_PATH).inline_shapes)
    if words > 50:
        log(f"  CHECK OK - {words} words and {images} picture(s) saved")
    else:
        log(f"  CHECK FAILED - only {words} words in the saved document")
    log(f"  Word file -> {DOCX_PATH}")


# ---------------------------------------------------------------------------
# Screen recording (macOS built-in 'screencapture', no extra install)
# ---------------------------------------------------------------------------
VIDEO_SECONDS = 200     # a full run takes about 3 minutes


def start_recording():
    """Record the whole screen (with the mouse pointer) for VIDEO_SECONDS.
    screencapture saves the file by itself when the time is up."""
    if os.path.exists(VIDEO_RAW):
        os.remove(VIDEO_RAW)
    errlog = open(os.path.join(BASE_DIR, "recording_log.txt"), "w")
    proc = subprocess.Popen(
        ["screencapture", "-v", "-C", "-V", str(VIDEO_SECONDS), VIDEO_RAW],
        stdin=subprocess.DEVNULL, stdout=errlog, stderr=errlog)
    time.sleep(2)
    if proc.poll() is not None:
        log("  ! screen recorder did not start - see recording_log.txt")
    else:
        log(f"  screen recording started ({VIDEO_SECONDS} s) -> {VIDEO_RAW}")
    return proc


def stop_recording(proc):
    """Wait for the recording to reach its set length and save itself."""
    if proc is None:
        return
    if proc.poll() is None:
        log("  waiting for the screen recording to finish and save...")
        try:
            proc.wait(timeout=VIDEO_SECONDS + 60)
        except subprocess.TimeoutExpired:
            proc.terminate()
    time.sleep(3)
    if os.path.exists(VIDEO_RAW):
        mb = os.path.getsize(VIDEO_RAW) / 1_000_000
        log(f"  screen recording saved -> {VIDEO_RAW} ({mb:.1f} MB)")
    else:
        log("  ! no recording saved - see recording_log.txt")


# ---------------------------------------------------------------------------
# Helper mode: show mouse position to find fallback click points
# ---------------------------------------------------------------------------
def where_mode():
    print("Hover over a link. Press Ctrl+C here to stop.\n")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"\rX={x:5d}  Y={y:5d}", end="", flush=True)
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nDone.")


def main():
    if "--where" in sys.argv:
        where_mode()
        return

    log(f"Naruvi report bot {VERSION}")
    log("Daily report bot starting in 5 seconds - hands off the mouse/keyboard.")
    log("Emergency stop: push the mouse into any screen corner.")
    time.sleep(5)

    recorder = None if "--no-video" in sys.argv else start_recording()
    try:
        headline, page_text, section = chrome_part()
        rows_before = load_workbook(XLSX_PATH).active.max_row \
            if os.path.exists(XLSX_PATH) else 1
        if not excel_part(headline):
            wb = load_workbook(XLSX_PATH)
            if wb.active.max_row > rows_before:     # only remove OUR bad row
                log("  removing the incomplete new row")
                wb.active.delete_rows(wb.active.max_row)
                wb.save(XLSX_PATH)
            log("  trying Excel once more")
            excel_part(headline)
        word_part(page_text, section)
        log("ALL DONE - showing the saved Excel sheet for the video")
        subprocess.run(["open", "-a", "Microsoft Excel", XLSX_PATH])
        time.sleep(5)
    finally:
        stop_recording(recorder)

    log("ALL DONE")
    log(f"  Excel     : {XLSX_PATH}")
    log(f"  Word      : {DOCX_PATH}")
    log(f"  Screenshots in: {SHOT_DIR}")


if __name__ == "__main__":
    try:
        main()
    except pyautogui.FailSafeException:
        log("Stopped by you (mouse moved to a screen corner).")
    except RuntimeError as err:
        log(f"STOPPED: {err}")
