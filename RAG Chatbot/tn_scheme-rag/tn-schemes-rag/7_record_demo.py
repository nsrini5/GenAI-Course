"""
Records a ~3 minute demo video of the app, driven automatically but with human-like
mouse movement, typing and pauses.  Output: recordings/demo_<date>.mp4

One-time setup (in the project's .venv):
    pip install playwright imageio-ffmpeg
    playwright install chromium

Before recording:
    1. Start the app in another terminal tab:   streamlit run 3_app.py
    2. Open it once in Safari and choose தமிழ் so the Tamil translation is cached
       (otherwise the one-minute translation progress bar appears in the video).

Record:
    python 7_record_demo.py
"""
import math
import re
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

APP_URL = "http://localhost:8501"
SIZE = {"width": 1440, "height": 900}
OUT_DIR = Path("recordings")
DISTRICT = "Vellore"
LAND_ACRES = "2"
CHAT_QUESTION = "நெல் விதைக்கு என்ன மானியம் கிடைக்கும்?"
FEATURED_ORDER = ["oilseeds", "crops", "horticulture", "poultry", "goat", "cattle", "fish", "allied"]

# Fake mouse pointer + click ripple, because recorded videos do not show the real cursor
CURSOR_JS = """
window.addEventListener('DOMContentLoaded', () => {
  const c = document.createElement('div');
  c.id = '__demo_cursor';
  c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 2l14 9-6.5 1.5L15 20l-3 1.5-3.4-7.3L4 18z" fill="#111" stroke="#fff" stroke-width="1.4"/></svg>';
  Object.assign(c.style, {position:'fixed', left:'0px', top:'0px', zIndex:2147483647, pointerEvents:'none',
                          transition:'transform 0.04s linear', transform:'translate(-200px,-200px)'});
  document.body.appendChild(c);
  document.addEventListener('mousemove', e => { c.style.transform = `translate(${e.clientX-3}px,${e.clientY-2}px)`; }, true);
  document.addEventListener('mousedown', e => {
    const r = document.createElement('div');
    Object.assign(r.style, {position:'fixed', left:(e.clientX-18)+'px', top:(e.clientY-18)+'px', width:'36px', height:'36px',
      borderRadius:'50%', background:'rgba(255,140,0,0.45)', zIndex:2147483646, pointerEvents:'none',
      transition:'all 0.45s ease-out'});
    document.body.appendChild(r);
    requestAnimationFrame(() => { r.style.transform = 'scale(1.8)'; r.style.opacity = '0'; });
    setTimeout(() => r.remove(), 500);
  }, true);
});
"""


class Human:
    """Moves, clicks, types and scrolls like a person."""

    def __init__(self, page):
        self.page = page
        self.x, self.y = SIZE["width"] / 2, SIZE["height"] / 2
        self.t0 = time.time()

    # ---- timing
    def pause(self, a=0.4, b=0.9):
        time.sleep(random.uniform(a, b))

    def until(self, seconds):
        """Wait until the given point in the timeline (seconds since start)."""
        left = seconds - (time.time() - self.t0)
        if left > 0:
            time.sleep(left)

    def settle(self, extra=0.6):
        """Wait for Streamlit to finish re-running the page."""
        time.sleep(0.4)
        try:
            self.page.wait_for_selector('[data-testid="stSpinner"]', state="detached", timeout=60000)
            self.page.wait_for_function(
                "() => !document.querySelector('[data-testid=\"stStatusWidget\"] [data-testid=\"stStatusWidgetRunningIcon\"]')",
                timeout=60000)
        except Exception:
            pass
        time.sleep(extra)

    # ---- mouse
    def move_to(self, x, y):
        sx, sy = self.x, self.y
        dist = math.hypot(x - sx, y - sy)
        steps = max(12, int(dist / 18))
        # gentle curve: control point offset sideways
        cx = (sx + x) / 2 + random.uniform(-0.15, 0.15) * dist
        cy = (sy + y) / 2 + random.uniform(-0.15, 0.15) * dist
        for i in range(1, steps + 1):
            t = i / steps
            t = t * t * (3 - 2 * t)  # ease in-out
            px = (1 - t) ** 2 * sx + 2 * (1 - t) * t * cx + t ** 2 * x
            py = (1 - t) ** 2 * sy + 2 * (1 - t) * t * cy + t ** 2 * y
            self.page.mouse.move(px, py)
            time.sleep(random.uniform(0.006, 0.014))
        self.x, self.y = x, y

    def hover(self, locator):
        dismiss_dialogs(self.page, rounds=1)  # close any pop-up before moving
        locator.scroll_into_view_if_needed()
        box = locator.bounding_box()
        if not box:
            raise RuntimeError("element not visible")
        x = box["x"] + box["width"] * random.uniform(0.35, 0.65)
        y = box["y"] + box["height"] * random.uniform(0.4, 0.6)
        self.move_to(x, y)
        self.pause(0.15, 0.35)

    def click(self, locator, settle=True):
        self.hover(locator)
        self.page.mouse.down()
        time.sleep(random.uniform(0.06, 0.12))
        self.page.mouse.up()
        if settle:
            self.settle()

    def type(self, text):
        for ch in text:
            self.page.keyboard.type(ch)
            time.sleep(random.uniform(0.07, 0.17) if ch != " " else random.uniform(0.12, 0.25))

    def scroll(self, total, step=120):
        n = max(1, abs(total) // step)
        for _ in range(n):
            self.page.mouse.wheel(0, step if total > 0 else -step)
            time.sleep(random.uniform(0.12, 0.22))

    # ---- Streamlit widgets (found by their key, so they work in any language)
    def select(self, key, search=None, option_text=None, index=None):
        # works with both the older (BaseWeb) and newer (combobox) Streamlit dropdowns
        box = self.page.locator(f".st-key-{key} [role='combobox'], .st-key-{key} [data-baseweb='select']").first
        self.click(box, settle=False)
        self.pause(0.3, 0.6)
        if search:
            self.page.keyboard.press("Meta+A" if sys.platform == "darwin" else "Control+A")
            self.type(search)
            self.pause(0.4, 0.6)
        opts = self.page.locator("[role='listbox'] [role='option'], [data-baseweb='popover'] [role='option']")
        opts.first.wait_for(timeout=10000)
        target = opts.filter(has_text=option_text).first if option_text else opts.nth(index or 0)
        self.click(target)


DIALOG = '[role="dialog"], [data-testid="stDialog"], [data-baseweb="modal"]'
CLOSE_BUTTONS = ('button[aria-label="Close"], button:has-text("Close"), button:has-text("Got it"), '
                 'button:has-text("Dismiss"), button:has-text("OK"), button:has-text("Continue")')


def dismiss_dialogs(page, rounds=3):
    """Tick "Don't show again" (if offered) and close any pop-up dialog."""
    for _ in range(rounds):
        dlg = page.locator(DIALOG).filter(visible=True)
        if not dlg.count():
            return
        d = dlg.first
        try:
            again = d.locator("label, span, p").filter(has_text=re.compile(r"(don.?t|do not).{0,12}show", re.I))
            if again.count():
                box = d.locator('input[type="checkbox"]')
                if box.count() and not box.first.is_checked():
                    box.first.check(force=True)
                else:
                    again.first.click(force=True)
            btn = d.locator(CLOSE_BUTTONS)
            if btn.count():
                btn.first.click(force=True)
            else:
                page.keyboard.press("Escape")
        except Exception:
            page.keyboard.press("Escape")
        time.sleep(0.6)


def featured_key(page):
    for k in FEATURED_ORDER:
        if page.locator(f".st-key-feat_{k} button").count():
            return k
    return None


def demo(h: Human, page):
    side = page.locator('section[data-testid="stSidebar"]')

    # 0:00-0:20  Home page tour
    h.settle(1.5)
    for sel in ["h1", '[data-testid="stSidebar"] h2', ".st-key-feat_oilseeds, .st-key-feat_crops"]:
        loc = page.locator(sel).first
        if loc.count():
            h.hover(loc)
            h.pause(1.5, 2.5)
    for k in FEATURED_ORDER:
        loc = page.locator(f".st-key-feat_{k}")
        if loc.count():
            h.hover(loc.first)
            h.pause(0.6, 1.0)
    h.until(20)

    # 0:20-0:45  Click a featured card -> matching schemes table
    k = featured_key(page)
    if k:
        h.click(page.locator(f".st-key-feat_{k} button").first)
    h.pause(1.5, 2)
    table = page.locator('[data-testid="stDataFrame"]').first
    if table.count():
        h.hover(table)
        h.pause(1, 1.5)
        h.move_to(h.x + 250, h.y + 40)
    h.until(45)

    # 0:45-1:15  Open one scheme and read the card
    h.select("f_scheme", index=1)
    h.pause(1.5, 2)
    for sel in ['[data-testid="stAlertContentSuccess"]', '[data-testid="stCheckbox"]']:
        loc = page.locator(sel).first
        if loc.count():
            h.hover(loc)
            h.pause(1.2, 1.8)
    box = page.locator('[data-testid="stCheckbox"] label').first
    if box.count():
        h.click(box, settle=False)
        h.pause(0.8, 1.2)
    h.scroll(480)
    h.pause(2, 3)
    h.scroll(-480)
    h.until(75)

    # 1:15-1:40  District + land size filters
    h.click(side.locator("button", has_text="↺").first)  # reset
    exp = side.locator('[data-testid="stExpander"] summary').nth(1)  # "Where, when & land size"
    h.click(exp, settle=False)
    h.pause(0.6, 1)
    h.select("f_district", search=DISTRICT[:4], option_text=DISTRICT)
    acres = page.locator(".st-key-f_acres input").first
    h.click(acres, settle=False)
    page.keyboard.press("Meta+A" if sys.platform == "darwin" else "Control+A")
    h.type(LAND_ACRES)
    page.keyboard.press("Enter")
    h.settle(1.5)
    table = page.locator('[data-testid="stDataFrame"]').first
    if table.count():
        h.hover(table)
    h.until(100)

    # 1:40-2:00  Training programmes
    h.click(side.locator("button", has_text="↺").first)
    radio = page.locator(".st-key-f_type [role='radiogroup'] label", has_text="🎓").first
    h.click(radio)
    if page.locator(".st-key-f_ttopic").count():
        h.select("f_ttopic", index=1)
    h.pause(1.5, 2)
    h.until(120)

    # 2:00-2:25  Switch the whole app to Tamil
    h.click(side.locator("button", has_text="↺").first)
    h.select("lang_ui", option_text="தமிழ்")
    h.settle(2)
    for sel in ['[data-testid="stSidebar"] h2', ".st-key-feat_oilseeds, .st-key-feat_crops", "h3"]:
        loc = page.locator(sel).first
        if loc.count():
            h.hover(loc)
            h.pause(1.5, 2.5)
    h.until(145)

    # 2:25-2:55  Ask a question in Tamil
    chat = page.locator('[data-testid="stChatInput"] textarea').first
    h.click(chat, settle=False)
    h.pause(0.5, 0.8)
    h.type(CHAT_QUESTION)
    h.pause(0.6, 1)
    page.keyboard.press("Enter")
    n_before = page.locator('[data-testid="stChatMessage"]').count()
    try:
        page.wait_for_function(
            f"() => document.querySelectorAll('[data-testid=\"stChatMessage\"]').length >= {n_before + 1}", timeout=30000)
    except Exception:
        pass
    h.settle(1)
    h.scroll(600)
    h.pause(3, 4)
    h.until(175)

    # 2:55-3:00  Back to start
    h.scroll(-1200)
    h.click(side.locator("button", has_text="↺").first)
    h.until(180)


def to_mp4(webm: Path, mp4: Path, trim_start: float):
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        print(f"imageio-ffmpeg not installed - video kept as {webm} (open it in Chrome)")
        return webm
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-ss", f"{trim_start:.2f}", "-i", str(webm),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(mp4)], check=True)
    webm.unlink(missing_ok=True)
    return mp4


def main():
    OUT_DIR.mkdir(exist_ok=True)
    random.seed()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless="--headless" in sys.argv)
        ctx = browser.new_context(viewport=SIZE, record_video_dir=str(OUT_DIR), record_video_size=SIZE,
                                  device_scale_factor=1)
        ctx.add_init_script(CURSOR_JS)
        page = ctx.new_page()
        t_open = time.time()
        try:
            page.goto(APP_URL, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            sys.exit(f"Could not open {APP_URL} - start the app first:  streamlit run 3_app.py")
        page.wait_for_selector("h1", timeout=90000)
        page.wait_for_selector('[data-testid="stSidebar"]', timeout=90000)
        time.sleep(3)
        dismiss_dialogs(page)  # Streamlit pop-ups are closed before the video starts (trimmed off)
        time.sleep(1)
        # ...and if one pops up later, close it automatically before the next action
        try:
            page.add_locator_handler(page.locator(DIALOG).filter(visible=True).first,
                                     lambda _: dismiss_dialogs(page), no_wait_after=True)
        except Exception:
            pass
        h = Human(page)
        trim = time.time() - t_open  # cut the page-loading part from the video
        print("Recording... (about 3 minutes, don't touch the browser window)")
        try:
            demo(h, page)
        except Exception as e:
            print(f"Demo step failed ({e}) - saving what was recorded so far")
        video = page.video.path()
        ctx.close()
        browser.close()

    out = OUT_DIR / f"demo_{datetime.now():%Y%m%d_%H%M}.mp4"
    final = to_mp4(Path(video), out, trim)
    print(f"Saved: {final}")


if __name__ == "__main__":
    main()
