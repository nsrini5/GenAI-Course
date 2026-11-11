"""
run_meal_prompts.py - runs both meal-plan prompts through Qwen 2.5 (Ollama) in a
real Terminal window and saves a screenshot of each run.

    Run 1: meal_plan_prompt.md              -> run1.png + run1_output.md
    Run 2: meal_plan_prompt_gluten_free.md  -> run2.png + run2_output.md

Ollama must be running (open the Ollama app). From the VS Code terminal:
    cd "/Users/srini/GenAI Course/meal-plan-prompt"
    python3 run_meal_prompts.py                 # uses qwen2.5:3b
    python3 run_meal_prompts.py qwen2.5         # the larger 7B model
If macOS asks "Visual Studio Code wants to control Terminal", click OK.
"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:3b"
RUNS = [("meal_plan_prompt.md", "run1"), ("meal_plan_prompt_gluten_free.md", "run2")]


def osa(script):
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True).stdout.strip()


def prompt_text(md_file):
    """The part of the file to paste into the AI: from the PROFILE block to the end."""
    text = (HERE / md_file).read_text()
    start = text.find("## ✏️ PROFILE")
    return text[start:] if start != -1 else text


def run_one(md_file, name):
    tmp = HERE / f"_{name}_prompt.txt"
    tmp.write_text(prompt_text(md_file))
    folder = str(HERE).replace('"', '\\\\"')
    shell_cmd = (f'cd \\"{folder}\\"; clear; '
                 f'echo \\"$ ollama run {MODEL}   (prompt: {md_file})\\"; echo; '
                 f'ollama run {MODEL} --verbose \\"$(cat _{name}_prompt.txt)\\" | tee {name}_output.md; '
                 f'rm -f _{name}_prompt.txt')
    print(f"{name}: asking {MODEL} with {md_file} ... (about 1-2 minutes)")
    osa('tell application "Terminal" to activate')
    osa(f'tell application "Terminal" to do script "{shell_cmd}"')
    time.sleep(1)
    osa('tell application "Terminal" to set bounds of front window to {0, 25, 1470, 956}')
    osa('tell application "Terminal" to set font size of current settings of selected tab of front window to 10')

    for _ in range(600):                      # wait for the final timing line
        text = osa('tell application "Terminal" to get contents of selected tab of front window')
        if any(l.strip().startswith("eval rate:") for l in text.splitlines()):
            break
        time.sleep(1)
    time.sleep(1.5)
    window_id = osa('tell application "Terminal" to id of front window')
    shot = HERE / f"{name}.png"
    subprocess.run(["screencapture", "-o", f"-l{window_id}", str(shot)])
    print(f"   saved {shot.name}" if shot.exists() else "   no screenshot - check Screen Recording permission")


if __name__ == "__main__":
    for md_file, name in RUNS:
        run_one(md_file, name)
    print("Done: run1.png, run2.png (and the full answers in run1_output.md, run2_output.md)")
