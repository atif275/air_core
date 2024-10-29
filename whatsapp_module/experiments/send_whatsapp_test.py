import os
import platform
import time
from pynput.keyboard import Key, Controller

keyboard = Controller()

# Function to open WhatsApp Desktop based on the operating system
def open_whatsapp():
    current_os = platform.system()  # Get the current OS

    if current_os == "Darwin":  # macOS
        os.system("open /Applications/WhatsApp.app")
    elif current_os == "Windows":  # Windows
        os.system("start whatsapp")
    elif current_os == "Linux":  # Linux
        os.system("whatsapp-desktop")  # Assuming WhatsApp Desktop is installed as 'whatsapp-desktop'
    else:
        raise OSError(f"Unsupported OS: {current_os}")

# Function to trigger Command+F for macOS using AppleScript
def trigger_search_mac():
    script = '''
    osascript -e 'tell application "System Events" to keystroke "f" using {command down}'
    '''
    os.system(script)

# Function to clear the search bar by selecting all and deleting any existing text
def clear_search_bar():
    # Select all (cmd+a for macOS, ctrl+a for Windows/Linux)
    if platform.system() == "Darwin":
        with keyboard.pressed(Key.cmd):
            keyboard.press('a')
            keyboard.release('a')
    else:
        with keyboard.pressed(Key.ctrl):
            keyboard.press('a')
            keyboard.release('a')
    
    time.sleep(0.5)

    # Press Backspace to clear the selected text
    keyboard.press(Key.backspace)
    keyboard.release(Key.backspace)

# Function to automate sending a message on WhatsApp desktop app
def send_whatsapp_message(contact_name, message):
    open_whatsapp()
    time.sleep(5)  # Wait for WhatsApp to load

    # Trigger search using AppleScript on macOS
    if platform.system() == "Darwin":
        trigger_search_mac()
    else:
        print("This script is only configured for macOS at the moment.")
        return

    time.sleep(1)

    # Clear the search bar in case any text is present
    clear_search_bar()
    time.sleep(1)

    # Type the contact's name in the search bar
    keyboard.type(contact_name)
    time.sleep(2)

    # Press Down arrow key twice to select the contact
    keyboard.press(Key.down)
    keyboard.release(Key.down)
    time.sleep(0.5)
    
    keyboard.press(Key.down)
    keyboard.release(Key.down)
    time.sleep(0.5)

    # Press Spacebar to open the contact's chat
    keyboard.press(Key.space)
    keyboard.release(Key.space)
    time.sleep(2)  # Wait for the chat to open

    # Now type the message in the message box
    keyboard.type(message)
    time.sleep(1)

    # Press Enter to send the message
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)

# Example usage
send_whatsapp_message('maaz umt w1', 'Hello, this is an automated message! from air')
