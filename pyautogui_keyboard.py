"""
pyautogui_keyboard.py - keyboard control on macOS
Opens TextEdit, types text, uses Mac shortcuts (Cmd keys).
Run:  python pyautogui_keyboard.py
Emergency stop: move the mouse into any screen corner.
"""
import subprocess
import time
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3


def hotkey(*keys):
    """Mac-safe shortcut: hold keys down one by one, release in reverse."""
    for k in keys:
        pyautogui.keyDown(k)
        time.sleep(0.05)
    for k in reversed(keys):
        pyautogui.keyUp(k)
        time.sleep(0.05)
    time.sleep(0.3)


print("Opening TextEdit...")
subprocess.run(["open", "-a", "TextEdit"])
time.sleep(3)
hotkey("command", "n")                          # new document
time.sleep(1)

pyautogui.write("Hello from PyAutoGUI on my MacBook!", interval=0.05)
pyautogui.press("enter")
pyautogui.write("This line was typed by a Python bot.", interval=0.05)
pyautogui.press("enter", presses=2)
print("Typed text")

hotkey("command", "a")                          # select all
hotkey("command", "c")                          # copy
pyautogui.press("down")
hotkey("command", "end")                        # go to the end
hotkey("command", "v")                          # paste
print("Selected all, copied and pasted (Cmd+A, Cmd+C, Cmd+V)")

hotkey("command", "z")                          # undo the paste
print("Undid the paste (Cmd+Z)")

print("Done. Close TextEdit without saving when you are finished.")
