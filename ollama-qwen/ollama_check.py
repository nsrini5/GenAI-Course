"""
ollama_check.py - Week 1 · Day 5: verify Qwen 2.5's answer (runs on your Mac, no internet)

Sends ONE checkable prompt to the local Ollama model TWICE, times each reply,
and checks every figure against the correct answer calculated here in Python.

Usage (Ollama must be running - open the Ollama app first):
    python ollama_check.py                 # uses qwen2.5:3b
    python ollama_check.py qwen2.5         # the default 7B model
"""
import json
import re
import sys
import time
import urllib.request
from datetime import datetime

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:3b"
OLLAMA_URL = "http://localhost:11434/api/generate"

# ---- The task: a purchase order with a checkable answer -------------------
ITEMS = [                       # (item, quantity, unit price in ₹)
    ("Nitrile gloves (box)", 120, 245),
    ("Syringes 5 ml (pack)", 75, 180),
    ("Hand sanitiser 500 ml (bottle)", 40, 95),
]
GST_RATE = 5                    # percent, on the subtotal

PROMPT = (
    "A hospital pharmacy places this purchase order:\n"
    + "\n".join(f"- {name}: {qty} units at Rs {price} each" for name, qty, price in ITEMS)
    + f"\nGST is {GST_RATE}% on the subtotal.\n"
    "Give the line total for each item, the subtotal, the GST amount and the grand total. "
    "Show each figure as a plain number in rupees."
)

# ---- The correct answer, worked out in Python (this is the verification) ---
line_totals = {name: qty * price for name, qty, price in ITEMS}
subtotal = sum(line_totals.values())
gst = subtotal * GST_RATE / 100
grand_total = subtotal + gst
EXPECTED = {**{f"Line total - {k}": v for k, v in line_totals.items()},
            "Subtotal": subtotal, "GST": gst, "Grand total": grand_total}


def ask(prompt):
    """One call to the local model. Returns (answer text, seconds, Ollama stats)."""
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.load(resp)
    seconds = time.perf_counter() - start
    return data["response"].strip(), seconds, data


def numbers_in(text):
    """Every number in the answer, with commas removed: '52,304.00' -> 52304.0"""
    return [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)]


def check(answer):
    found = numbers_in(answer)
    results = []
    for label, value in EXPECTED.items():
        ok = any(abs(n - value) < 0.01 for n in found)
        results.append((label, value, ok))
    return results


def main():
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=3)
    except Exception:
        sys.exit("Ollama is not running. Open the Ollama app (or run 'ollama serve') and try again.")

    print(f"Model: {MODEL}\n\nPROMPT:\n{PROMPT}\n")
    print("CORRECT ANSWER (calculated in Python):")
    for label, value in EXPECTED.items():
        print(f"  {label:45s} {value:>12,.2f}")

    runs = []
    for run in (1, 2):
        print(f"\n{'=' * 70}\nRUN {run} - asking {MODEL} ...")
        answer, seconds, stats = ask(PROMPT)
        results = check(answer)
        correct = sum(ok for *_, ok in results)
        tokens_per_s = stats.get("eval_count", 0) / max(stats.get("eval_duration", 1) / 1e9, 1e-9)
        print(answer)
        print(f"\n-- reply took {seconds:.1f} s  ({tokens_per_s:.0f} tokens/s)")
        for label, value, ok in results:
            print(f"   {'✔' if ok else '✘'} {label}: expected {value:,.2f}")
        print(f"-- {correct}/{len(results)} figures correct")
        runs.append((answer, seconds, correct))

    same = runs[0][0] == runs[1][0]
    print(f"\n{'=' * 70}\nSUMMARY  model={MODEL}")
    for i, (_, s, c) in enumerate(runs, 1):
        print(f"  run {i}: {s:.1f} s, {c}/{len(EXPECTED)} figures correct")
    print(f"  run 2 vs run 1: {'identical text' if same else 'different wording'}"
          f"{' - same figures' if runs[0][2] == runs[1][2] else ' - DIFFERENT figures'}")

    out = f"results_{MODEL.replace(':', '-')}_{datetime.now():%Y-%m-%d}.md"
    with open(out, "w") as f:
        f.write(f"# Qwen 2.5 check - {MODEL} - {datetime.now():%Y-%m-%d %H:%M}\n\n")
        f.write(f"## Prompt\n\n```\n{PROMPT}\n```\n\n## Correct answer\n\n")
        for label, value in EXPECTED.items():
            f.write(f"- {label}: {value:,.2f}\n")
        for i, (a, s, c) in enumerate(runs, 1):
            f.write(f"\n## Run {i} - {s:.1f} s - {c}/{len(EXPECTED)} correct\n\n```\n{a}\n```\n")
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
