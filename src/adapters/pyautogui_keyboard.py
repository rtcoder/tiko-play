class PyAutoGUIKeyboard:
    def execute(self, keys):
        import pyautogui

        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)

    def key_down(self, key):
        import pyautogui

        pyautogui.keyDown(key, _pause=False)

    def key_up(self, key):
        import pyautogui

        # PyAutoGUI 0.9.54 wraps keyUp in a corner fail-safe. Cleanup must
        # still reach the OS after that fail-safe has stopped new keyDowns.
        # Unwrap only this release call; never change the global FAILSAFE flag.
        pyautogui.keyUp.__wrapped__(key, _pause=False)

    def check_failsafe(self):
        import pyautogui

        pyautogui.failSafeCheck()
