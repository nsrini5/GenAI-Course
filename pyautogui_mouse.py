"""
pyautogui_mouse.py - mouse control on macOS
Move, click, double-click, right-click, drag and scroll.
Run:  python pyautogui_mouse.py
Tip:  python pyautogui_mouse.py --where   shows live X/Y of the mouse
Emergency stop: move the mouse into any screen corner.
"""
import sys
import time
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

if "--where" in sys.argv:
    print("Hover anywhere. Press Ctrl+C to stop.\n")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"\rX={x:5d}  Y={y:5d}", end="", flush=True)
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nDone.")
    sys.exit()

print("Starting in 3 seconds - hands off the mouse...")
time.sleep(3)

w, h = pyautogui.size()
cx, cy = w // 2, h // 2

pyautogui.moveTo(cx, cy, duration=1)            # move (absolute)
pyautogui.moveRel(100, 0, duration=0.5)         # move (relative)
pyautogui.moveRel(-100, 0, duration=0.5)
print("Moved the mouse")

pyautogui.click()                               # single left click
print("Clicked")

pyautogui.doubleClick()                         # double click
print("Double-clicked")

pyautogui.rightClick()                          # right click (context menu)
time.sleep(1)
pyautogui.press("escape")                       # close the menu
print("Right-clicked and closed the menu")

pyautogui.moveTo(cx - 100, cy, duration=0.5)
pyautogui.dragTo(cx + 100, cy, duration=1, button="left")   # drag
print("Dragged")

pyautogui.scroll(-5)                            # scroll down
time.sleep(0.5)
pyautogui.scroll(5)                             # scroll up
print("Scrolled down and up")

print("Done.")
