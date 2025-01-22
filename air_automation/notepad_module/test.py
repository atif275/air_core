import os
import time
import subprocess
import pyautogui

def write_text_in_notes(text, visual_mode=True):
    # Open Notes on macOS, Notepad on Windows, and Gedit on Linux
    if os.name == 'nt':  # Windows
        subprocess.Popen(["notepad.exe"])
        time.sleep(1)  # Allow time for Notepad to open
    elif os.name == 'posix':  # macOS and Linux
        if 'darwin' in os.sys.platform:  # macOS
            subprocess.Popen(["open", "-a", "Notes"])
        else:  # Linux
            subprocess.Popen(["gedit"])  # Assuming Gedit is available; change if needed
        time.sleep(1)  # Allow time for Notes or Gedit to open

    # Simulate typing in the selected application
    if visual_mode:
        for char in text:
            pyautogui.write(char)  # Type character by character
            time.sleep(0.6 / 100)  # Delay to simulate 100 WPM
    else:
        pyautogui.write(text)  # Paste the entire text quickly

# Example usage:
text_to_write = "This is a note written by Python in the Notes app!"
write_text_in_notes(text_to_write, visual_mode=False)  # Set visual_mode=False for fast typing
