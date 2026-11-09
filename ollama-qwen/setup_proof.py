"""
setup_proof.py - records proof that Ollama and Qwen 2.5 are installed on this Mac.

Runs, in a real Terminal window:
    ollama --version          (Ollama is installed and running)
    ollama list               (Qwen 2.5 is pulled, with its size)
    ollama show qwen2.5:3b    (model details: parameters, quantisation, context)
then saves:
    ollama_setup.png   - screenshot of that Terminal window
    setup_log.txt      - the same output as text

Run from the VS Code terminal:
    cd "/Users/srini/GenAI Course/ollama-qwen"
    python3 setup_proof.py
"""
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:3b"
SHOT = HERE / "ollama_setup.png"
LOG = HERE / "setup_log.txt"
COMMANDS = ["ollama --version", "ollama list", f"ollama show {MODEL}"]


def osa(script):
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True).stdout.strip()


def write_log():
    lines = [f"Ollama setup check - {datetime.now():%Y-%m-%d %H:%M}", ""]
    for cmd in COMMANDS:
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        lines += [f"$ {cmd}", (out.stdout + out.stderr).rstrip(), ""]
    LOG.write_text("\n".join(lines) + "\n")
    print(LOG.read_text())
    print(f"Saved {LOG}")


def screenshot():
    folder = str(HERE).replace('"', '\\\\"')
    shown = "; ".join(f'echo \\"$ {c}\\"; {c}; echo' for c in COMMANDS)
    osa('tell application "Terminal" to activate')
    osa(f'tell application "Terminal" to do script "cd \\"{folder}\\"; clear; {shown}; echo SETUP-CHECK-$((40+2))"')
    time.sleep(1)
    osa('tell application "Terminal" to set bounds of front window to {0, 25, 1300, 900}')
    for _ in range(60):                                    # wait for the commands to finish
        if "SETUP-CHECK-42" in osa(
                'tell application "Terminal" to get contents of selected tab of front window'):
            break
        time.sleep(1)
    time.sleep(1)
    window_id = osa('tell application "Terminal" to id of front window')
    subprocess.run(["screencapture", "-o", f"-l{window_id}", str(SHOT)])
    print(f"Saved {SHOT}" if SHOT.exists() else
          "No screenshot saved - check Screen Recording permission for VS Code")


if __name__ == "__main__":
    write_log()
    screenshot()
