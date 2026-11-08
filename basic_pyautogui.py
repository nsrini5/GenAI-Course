"""
basic_pyautogui.py - PyAutoGUI basics on macOS
Shows screen size, mouse position, a screenshot and the fail-safe.
Run:  python basic_pyautogui.py
Emergency stop: move the mouse into any screen corner.
"""
import time
import pyautogui

pyautogui.FAILSAFE = True   # mouse to a corner = stop
pyautogui.PAUSE = 0.5       # pause after every action

print("Starting in 3 seconds - hands off the mouse...")
time.sleep(3)

width, height = pyautogui.size()
print(f"Screen size: {width} x {height}")

x, y = pyautogui.position()
print(f"Mouse is now at: X={x}, Y={y}")

pyautogui.moveTo(width // 2, height // 2, duration=1)   # glide to centre
print("Moved mouse to the centre of the screen")

img = pyautogui.screenshot()
img.save("basic_screenshot.png")
print("Saved screenshot -> basic_screenshot.png")

print("Done.")
