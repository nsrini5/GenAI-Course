"""
take_ollama_screenshot.py - runs the 5% prompt in a real Terminal window with
`ollama run qwen2.5:3b --verbose` and saves a screenshot of that window as
ollama_session.png (prompt, answer and timing all visible).

Run from the VS Code terminal:
    cd "/Users/srini/GenAI Course/ollama-qwen"
    python3 take_ollama_screenshot.py
    python3 take_ollama_screenshot.py --shot-only   (just photograph the open Terminal window)
If macOS asks "Visual Studio Code wants to control Terminal", click OK.
"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:3b"
SHOT = HERE / "ollama_session.png"
PROMPT_FILE = HERE / "prompt.txt"

PROMPT = """A hospital pharmacy places this purchase order:
- Nitrile gloves (box): 120 units at Rs 245 each
- Syringes 5 ml (pack): 75 units at Rs 180 each
- Hand sanitiser 500 ml (bottle): 40 units at Rs 95 each
GST is 5% on the subtotal.
Give the line total for each item, the subtotal, the GST amount and the grand total. Show each figure as a plain number in rupees."""


def osa(script):
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True).stdout.strip()


def terminal_text():
    return osa('tell application "Terminal" to get contents of selected tab of front window')


def wait_until_finished(timeout=300):
    """Ollama --verbose ends with the line 'eval rate: ... tokens/s'.
    'prompt eval rate' comes first, so wait for the LAST line to be 'eval rate'."""
    for _ in range(timeout):
        lines = [l.strip() for l in terminal_text().splitlines() if l.strip()]
        if any(l.startswith("eval rate:") for l in lines):
            return True
        time.sleep(1)
    return False


def snap():
    osa('tell application "Terminal" to activate')
    time.sleep(1)
    window_id = osa('tell application "Terminal" to id of front window')
    subprocess.run(["screencapture", "-o", f"-l{window_id}", str(SHOT)])
    print(f"Saved {SHOT}" if SHOT.exists() else
          "No screenshot saved - check Screen Recording permission for VS Code")


def main():
    if "--shot-only" in sys.argv:          # Terminal already shows the session
        snap()
        return

    PROMPT_FILE.write_text(PROMPT)
    folder = str(HERE).replace('"', '\\"')
    shell_cmd = (f'cd \\"{folder}\\"; clear; '
                 f'echo \\"$ ollama run {MODEL} --verbose\\"; printf \\">>> \\"; cat prompt.txt; echo; echo; '
                 f'ollama run {MODEL} --verbose \\"$(cat prompt.txt)\\"; rm -f prompt.txt')

    print(f"Opening Terminal and asking {MODEL} ...")
    osa('tell application "Terminal" to activate')
    osa(f'tell application "Terminal" to do script "{shell_cmd}"')
    time.sleep(1)
    # big window so the whole answer and the timing lines fit
    osa('tell application "Terminal" to set bounds of front window to {0, 25, 1300, 1000}')
    osa('tell application "Terminal" to set font size of current settings of selected tab of front window to 11')

    print("Waiting for the answer and the timing lines ...")
    if not wait_until_finished():
        print("Did not see 'eval rate' after 5 minutes - taking the screenshot anyway.")
    time.sleep(1.5)
    snap()

if __name__ == "__main__":
    main()
