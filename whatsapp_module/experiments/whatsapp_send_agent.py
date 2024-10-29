import os
import time
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import signal
import sys
import random

# Load environment variables
load_dotenv()

# Flag to control UI mode
ui_mode = True  # Set to True for visible mode, False for headless/background mode

# Detect OS and set the Chrome user data directory path
def get_chrome_profile_path():
    system = platform.system()
    if system == "Windows":
        return r"C:\Users\maaza\AppData\Local\Google\Chrome\User Data\Default"
    elif system == "Darwin":  # macOS
        return r"/Users/ATIFHANIF/Library/Application Support/Google/Chrome/Default"
    elif system == "Linux":
        return r"/home/yourusername/.config/google-chrome/Default"
    else:
        raise ValueError("Unsupported operating system.")

# Set up WebDriver options for WhatsApp Web with user profile
chrome_profile_path = get_chrome_profile_path()
chrome_options = Options()
chrome_options.add_argument(f"user-data-dir={chrome_profile_path}")

if not ui_mode:
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

# Initialize the WebDriver
try:
    driver = webdriver.Chrome(options=chrome_options)
except Exception as e:
    print("Error initializing WebDriver:", e)
    sys.exit(1)

# File to read messages to be sent
input_file = "send_whatsapp.txt"
last_modified_time = None  # Track file modification time to detect updates

# Function to load messages from the file into a list of dictionaries
def load_messages():
    messages_to_send = []
    try:
        with open(input_file, "r", encoding="utf-8") as file:
            content = file.read().split("---------\n")
            for entry in content:
                if entry.strip():
                    lines = entry.strip().split("\n")
                    contact_name = lines[0].split(": ", 1)[1]
                    sent_time = lines[1].split(": ", 1)[1]
                    message_text = lines[2].split(": ", 1)[1]
                    
                    # Add to list of messages to send
                    messages_to_send.append({
                        "contact_name": contact_name,
                        "sent_time": sent_time,  # Track sent time if needed
                        "message_text": message_text,
                    })
    except FileNotFoundError:
        print("send_whatsapp.txt not found.")
    except Exception as e:
        print(f"Error loading messages: {e}")
    return messages_to_send

# Function to save unsent messages back to the file after attempting to send
def save_remaining_messages(messages_to_send):
    try:
        with open(input_file, "w", encoding="utf-8") as file:
            for message in messages_to_send:
                file.write(f"Contact Name/Phone Number: {message['contact_name']}\n")
                file.write(f"Sent Time: {message['sent_time']}\n")  # Retain original sent time
                file.write(f"Message: {message['message_text']}\n")
                file.write("---------\n")
    except Exception as e:
        print(f"Error saving remaining messages: {e}")

# Function to send a message to a specific contact
def send_message(contact_name, message_text):
    try:
        # Locate search box and type contact name
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"))
        )
        search_box.clear()
        search_box.send_keys(contact_name)
        search_box.send_keys(Keys.ENTER)
        print(f"Searching for contact: {contact_name}")
        time.sleep(2)  # Wait for chat to open

        # Locate message input box and send the message with realistic typing delay
        message_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']"))
        )
        print("Typing message...")

        message_box.clear()
        for char in message_text:
            message_box.send_keys(char)
            # Simulate realistic typing delay for 70 WPM with slight randomization
            typing_delay = random.uniform(0.12, 0.18)  # Delay between characters
            time.sleep(typing_delay)

        message_box.send_keys(Keys.ENTER)
        print(f"Message sent to {contact_name}: {message_text}")
        return True

    except NoSuchElementException:
        print(f"Contact {contact_name} not found.")
        return False
    except TimeoutException:
        print("Timeout occurred while sending message.")
        return False
    except Exception as e:
        print(f"Error sending message to {contact_name}: {e}")
        return False

# Function to handle graceful shutdown
def shutdown(signal, frame):
    print("\nShutting down gracefully...")
    driver.quit()
    sys.exit(0)

# Register the shutdown function for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, shutdown)

# Main function to read, send, and update messages
def main():
    global last_modified_time

    print("Starting the WhatsApp sending agent...")

    # Load WhatsApp Web once
    driver.get("https://web.whatsapp.com")
    print("Waiting for WhatsApp Web to load...")
    time.sleep(8)  # Wait for WhatsApp Web to load

    while True:
        try:
            # Check if the file has been modified
            current_modified_time = os.path.getmtime(input_file)
            if last_modified_time is None or current_modified_time > last_modified_time:
                print("New messages detected in send_whatsapp.txt")
                last_modified_time = current_modified_time  # Update last checked time

                # Load messages from file
                messages_to_send = load_messages()

                # Attempt to send each message
                unsent_messages = []
                for message in messages_to_send:
                    success = send_message(message["contact_name"], message["message_text"])
                    if not success:
                        unsent_messages.append(message)  # Keep unsent messages to retry

                # Save remaining unsent messages
                save_remaining_messages(unsent_messages)

            # Wait before checking for new messages
            time.sleep(5)

        except FileNotFoundError:
            print("send_whatsapp.txt not found. Waiting for file...")
            time.sleep(10)
        except Exception as e:
            print(f"Unexpected error in main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
