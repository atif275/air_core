import time
import pyautogui
from PIL import ImageGrab
from datetime import datetime
import os

# Path to the log file
log_file_path = "whatsapp_recv.txt"

# Green color range for unread message time (adjust based on the exact color)
GREEN_COLOR_RANGE = [(100, 150, 100), (170, 255, 170)]  # Example range

# Function to log messages
def log_message(contact_name, message):
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")
    time_str = now.strftime("%H:%M")

    with open(log_file_path, 'a') as f:
        f.write(f"Date: {date_str}\n")
        f.write(f"Time: {time_str}\n")
        f.write(f"Contact Name: {contact_name}\n")
        f.write(f"Message: {message}\n")
        f.write("--------------------\n")
    
    print(f"Message logged from {contact_name}")

# Function to open WhatsApp Desktop
def open_whatsapp():
    os.system("open /Applications/WhatsApp.app")  # macOS
    # os.system("start whatsapp")  # Uncomment for Windows
    time.sleep(5)  # Wait for WhatsApp to open

# Function to check if the color is in the green family
def is_color_in_green_range(color):
    return GREEN_COLOR_RANGE[0][0] <= color[0] <= GREEN_COLOR_RANGE[1][0] and \
           GREEN_COLOR_RANGE[0][1] <= color[1] <= GREEN_COLOR_RANGE[1][1] and \
           GREEN_COLOR_RANGE[0][2] <= color[2] <= GREEN_COLOR_RANGE[1][2]

# Function to detect unread messages based on green color in the time field
def check_for_unread_messages():
    # Define the region where the usernames and times are displayed (adjust as per your screen)
    while True:
        try:
            screenshot = ImageGrab.grab(bbox=(200, 150, 450, 800))  # Adjust bbox as needed

            # Scan through the region for the "green" time (unread message indicator)
            for x in range(200, 450):
                for y in range(150, 800):
                    color = screenshot.getpixel((x, y))

                    if is_color_in_green_range(color):
                        print(f"Unread message detected at pixel ({x}, {y})")

                        # Get the contact name (you'll need to adjust the logic for scraping the name)
                        pyautogui.click(x, y)  # Click to open the chat
                        time.sleep(1)

                        # Simulate copying the message (you can use OCR for real content)
                        contact_name = "Contact Name"  # Replace with logic to extract the contact name
                        message = "Unread message detected!"  # Replace with logic to extract the message

                        # Log the message
                        log_message(contact_name, message)

                        # Wait before the next check
                        time.sleep(5)
                        break
        except Exception as e:
            print(f"Error: {e}")

        # Re-check after some time
        time.sleep(5)

if __name__ == "__main__":
    # Step 1: Open WhatsApp
    open_whatsapp()

    # Step 2: Start checking for unread messages
    check_for_unread_messages()
