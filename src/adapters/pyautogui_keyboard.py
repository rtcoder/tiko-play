class PyAutoGUIKeyboard:
    def execute(self, keys):
        import pyautogui

        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)
