# simulate.py
import sys
import pyautogui

if len(sys.argv) < 2:
    print("Brak argumentu - znak do naciśnięcia")
    sys.exit(1)

key = sys.argv[1]

try:
    pyautogui.press(key)
    print(f"[simulate.py] Naciśnięto: {key}")
except Exception as e:
    print(f"[simulate.py] Błąd: {e}")
