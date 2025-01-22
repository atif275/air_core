import os
import time
import random
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
import concurrent.futures
import signal
import sys
import re
# Load environment variables
load_dotenv()

# Flag to control UI mode
ui_mode = True  # Set to True for visible mode, False for headless/background mode

# Detect OS and set the Chrome user data directory path
def get_chrome_profile_path():
    print("Entering get_chrome_profile_path()")
    system = platform.system()
    if system == "Windows":
        print("Detected Windows OS")
        return r"C:\Users\maaza\AppData\Local\Google\Chrome\User Data\Default"
    elif system == "Darwin":  # macOS
        print("Detected macOS")
        return r"/Users/ATIFHANIF/Library/Application Support/Google/Chrome/Default"
    elif system == "Linux":
        print("Detected Linux OS")
        return r"/home/yourusername/.config/google-chrome/Default"
    else:
        raise ValueError("Unsupported operating system.")

# Set up WebDriver options for WhatsApp Web with user profile
print("Setting up WebDriver options...")
chrome_profile_path = get_chrome_profile_path()
chrome_options = Options()
chrome_options.add_argument(f"user-data-dir={chrome_profile_path}")  # Use your existing Chrome profile

if not ui_mode:
    print("Running in headless (background) mode")
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
else:
    print("Running in UI (visible) mode")

# Initialize the WebDriver
try:
    driver = webdriver.Chrome(options=chrome_options)
    print("WebDriver initialized successfully with the specified user profile.")
except Exception as e:
    print("Error initializing WebDriver:", e)
    sys.exit(1)  # Exit if WebDriver fails to initialize

# File to save received WhatsApp messages
output_file = "whatsapp_recv.txt"
saved_messages = {}

# Function to load existing messages from the file into a dictionary
def load_existing_messages():
    try:
        with open(output_file, "r", encoding="utf-8") as file:
            content = file.read().split("---------\n")
            for entry in content:
                if entry.strip():  # Only process non-empty entries
                    # Parse each entry
                    lines = entry.strip().split("\n")
                    contact_name = lines[0].split(": ", 1)[1]
                    received_time = lines[1].split(": ", 1)[1]
                    unread_count = lines[2].split(": ", 1)[1]
                    message_text = lines[3].split(": ", 1)[1]
                    
                    # Store entry in dictionary
                    saved_messages[contact_name] = {
                        "received_time": received_time,
                        "unread_count": unread_count,
                        "message_text": message_text,
                    }
    except FileNotFoundError:
        # If the file doesn't exist, initialize an empty dictionary
        pass
    except Exception as e:
        print(f"Error loading existing messages: {e}")

# Function to save message details to the dictionary and update the file
def save_message(contact_name, received_time, message_text, unread_count):
    # Update the dictionary with the latest message details
    saved_messages[contact_name] = {
        "received_time": received_time,
        "unread_count": unread_count,
        "message_text": message_text,
    }
    # Rewrite the file with the updated dictionary content
    rewrite_file()

# Function to remove read messages from the dictionary and update the file
def remove_read_message(contact_name):
    if contact_name in saved_messages:
        print(f"Removing read message from {contact_name}")
        del saved_messages[contact_name]
        rewrite_file()

# Function to rewrite the file with the current dictionary content
def rewrite_file():
    try:
        with open(output_file, "w", encoding="utf-8") as file:
            for contact, details in saved_messages.items():
                file.write(f"Contact Name/Phone Number: {contact}\n")
                file.write(f"Received Time: {details['received_time']}\n")
                file.write(f"Unread Messages Count: {details['unread_count']}\n")
                file.write(f"Message: {details['message_text']}\n")
                file.write("---------\n")
    except Exception as e:
        print(f"Error rewriting file: {e}")

# Function to check for new (unread) messages on WhatsApp Web without opening the chat
def check_new_messages():
    print("Entering check_new_messages()")
    driver.get("https://web.whatsapp.com")
    print("Waiting for WhatsApp Web to load...")
    time.sleep(8)  # Wait for WhatsApp Web to load

    while True:
        try:
            print("Checking for unread messages...")
            
            # Locate all chat containers in the chat list
            chat_containers = driver.find_elements(By.XPATH, "//div[@aria-label='Chat list']//div[contains(@class, '_ak72') and contains(@class, '_ak73')]")
            
            current_unread_contacts = set()  # Track currently unread contacts

            for chat_container in chat_containers:
                try:
                    # Try to locate the unread message count within each chat container
                    unread_indicator = chat_container.find_elements(By.XPATH, ".//span[contains(@aria-label, 'unread message')]")
                    contact_name = chat_container.find_element(By.XPATH, ".//span[@title]").get_attribute("title")
                    
                    # Extract the received time if available
                    received_time_element = chat_container.find_elements(By.XPATH, ".//div[@class='_ak8i']")
                    received_time = received_time_element[0].text if received_time_element else "Unknown"

                    # Check if message text is available
                    message_text_element = chat_container.find_elements(By.XPATH, ".//div[@class='_ak8k']//span[@dir='ltr']")
                    message_text = message_text_element[0].text if message_text_element else "No message text"

                    # If unread indicator is found, process as an unread message
                    if unread_indicator:
                        unread_count = unread_indicator[0].get_attribute("aria-label").replace(" unread message", "").replace(" unread messages", "")
                        unread_count = ''.join(filter(str.isdigit, unread_count))
                        print(f"Unread Message from {contact_name} at {received_time}: {message_text} (Unread Count: {unread_count})")
                        save_message(contact_name, received_time, message_text, unread_count)
                        current_unread_contacts.add(contact_name)
                    # else:
                    #     print(f"Read Message from {contact_name} at {received_time}: {message_text}")
                
                except Exception as e:
                    print("Error extracting details from chat container:", e)

            # Remove messages no longer unread
            for contact in list(saved_messages.keys()):
                if contact not in current_unread_contacts:
                    remove_read_message(contact)

            time.sleep(10)  # Check every 10 seconds

        except Exception as e:
            print("Error checking messages:", e)
            time.sleep(10)


# Function to send a custom message to a specific contact
def send_custom_message(contact_name, message):
    print(f"Attempting to send message to {contact_name}")
    
    try:
        # Locate search box and type contact name using WebDriverWait
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"))
        )
        search_box.clear()
        search_box.send_keys(contact_name)
        search_box.send_keys(Keys.ENTER)
        print(f"Searching for contact: {contact_name}")
        time.sleep(2)  # Wait for chat to open
    except NoSuchElementException:
        print("Search box not found. Check the WhatsApp Web layout or XPaths.")
        return
    except TimeoutException:
        print("Timeout while searching for contact. Please ensure the contact name is correct and visible.")
        return
    except Exception as e:
        print(f"Unexpected error during search: {e}")
        return

    retries = 3  # Attempts for the message input box
    for attempt in range(retries):
        try:
            # Locate message input and send the message using WebDriverWait
            message_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']"))
            )
            print("Typing message...")
            message_box.clear()  # Clear any pre-filled text in the message box
            for char in message:
                message_box.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))  # Simulate typing speed
            message_box.send_keys(Keys.ENTER)
            print("Message sent successfully!")
            break  # Exit loop if successful
        except (NoSuchElementException, StaleElementReferenceException, TimeoutException) as e:
            print(f"Error with message input on attempt {attempt + 1}: {e}")
            time.sleep(2)  # Wait before retrying
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

# Function to handle graceful shutdown
def shutdown(signal, frame):
    print("\nShutting down gracefully...")
    driver.quit()
    sys.exit(0)

# Register the shutdown function for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, shutdown)

# Start the agent
if __name__ == "__main__":
    print("Starting the WhatsApp agent...")
    load_existing_messages()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.submit(check_new_messages)
        
        while True:
            user_request = input("Do you want to send a custom message? (yes/no): ")
            if user_request.lower() == "yes":
                contact_name = input("Enter contact name or phone number: ")
                custom_message = input("What message would you like to send? ")
                send_custom_message(contact_name, custom_message)
            elif user_request.lower() == "no":
                print("Continuing to monitor messages...")
            else:
                print("Please enter 'yes' or 'no'.")
            time.sleep(1)  # Polling interval for checking user input
