import os
import time
import platform
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import concurrent.futures
import signal
import sys
from utils.forward_messages import forward_recent_message_to
from utils.download_voice_messages import download_voice_message
from utils.download_audio_messages import download_audio_message

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
chrome_options.add_argument(f"user-data-dir={chrome_profile_path}")

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
    sys.exit(1)

# Files to manage messages
send_file = "send_whatsapp.txt"
recv_file = "whatsapp_recv.txt"
contacts_file = "contacts.txt"
saved_messages = {}
last_modified_time = None  # Track modification time for send file

# Function to ensure send_whatsapp.txt exists
def ensure_send_file():
    try:
        if not os.path.exists(send_file):
            print(f"Creating {send_file}...")
            with open(send_file, "w", encoding="utf-8") as file:
                pass  # Create empty file
            print(f"{send_file} created successfully.")
    except Exception as e:
        print(f"Error creating {send_file}: {e}")

# Function to ensure contacts.txt exists
def ensure_contacts_file():
    try:
        if not os.path.exists(contacts_file):
            print(f"Creating {contacts_file}...")
            with open(contacts_file, "w", encoding="utf-8") as file:
                # file.write("# WhatsApp Contacts List\n")
                # file.write("# Format: Contact Name/Phone Number\n")
                # file.write("# Add contacts below this line\n")
                # file.write("---------\n")
                pass  # Create empty file
            print(f"{contacts_file} created successfully.")
    except Exception as e:
        print(f"Error creating {contacts_file}: {e}")

# Initialize files
ensure_contacts_file()
ensure_send_file()

def fetch_contacts_from_chat_list(count=None):
    """
    Fetch contacts from WhatsApp Web chat list and save them to contacts.txt.
    
    Args:
        count (int, optional): Number of recent contacts to fetch. If None, fetches all contacts.
    
    Returns:
        list: List of fetched contacts
    """
    try:
        print("Fetching contacts from chat list...")
        # Wait for chat list to be visible
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Chat list']"))
        )
        
        # Get all chat containers
        chat_containers = driver.find_elements(
            By.XPATH, 
            "//div[@aria-label='Chat list']//div[contains(@class, '_ak72') and contains(@class, '_ak73')]"
        )
        
        contacts = []
        for container in chat_containers:
            try:
                # Extract contact name/number
                contact_element = container.find_element(By.XPATH, ".//span[@title]")
                contact_name = contact_element.get_attribute("title")
                
                if contact_name:
                    contacts.append(contact_name)
            except Exception as e:
                print(f"Error extracting contact: {e}")
                continue
        
        # If count is specified, take only the most recent contacts
        if count is not None and isinstance(count, int):
            contacts = contacts[:count]
        
        # Save contacts to file
        try:
            with open(contacts_file, "w", encoding="utf-8") as file:
                # file.write("# WhatsApp Contacts List\n")
                # file.write("# Format: Contact Name/Phone Number\n")
                # file.write("# Most recent contacts at the top\n")
                file.write("---------\n")
                for contact in contacts:
                    file.write(f"{contact}\n")
                    file.write("---------\n")
            print(f"Successfully saved {len(contacts)} contacts to {contacts_file}")
        except Exception as e:
            print(f"Error saving contacts to file: {e}")
        
        return contacts
    
    except Exception as e:
        print(f"Error fetching contacts: {e}")
        return []

# Function to load messages to send from the file
def load_messages_to_send():
    messages_to_send = []
    try:
        with open(send_file, "r", encoding="utf-8") as file:
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
                        "sent_time": sent_time,
                        "message_text": message_text,
                    })
    except FileNotFoundError:
        print("send_whatsapp.txt not found.")
    except Exception as e:
        print(f"Error loading messages: {e}")
    return messages_to_send

# Function to save remaining unsent messages back to file
def save_remaining_messages(messages_to_send):
    try:
        with open(send_file, "w", encoding="utf-8") as file:
            for message in messages_to_send:
                file.write(f"Contact Name/Phone Number: {message['contact_name']}\n")
                file.write(f"Sent Time: {message['sent_time']}\n")
                file.write(f"Message: {message['message_text']}\n")
                file.write("---------\n")
    except Exception as e:
        print(f"Error saving remaining messages: {e}")

# Function to send message to a specific contact
def send_message(contact_name, message_text):
    try:
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"))
        )
        search_box.clear()
        search_box.send_keys(contact_name)
        search_box.send_keys(Keys.ENTER)
        time.sleep(2)

        message_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']"))
        )
        for char in message_text:
            message_box.send_keys(char)
            time.sleep(random.uniform(0.12, 0.18))  # Typing delay

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

# Function to prioritize sending messages if send_whatsapp.txt is updated
def send_agent():
    global last_modified_time

    while True:
        try:
            # Ensure send file exists
            # ensure_send_file()
            
            current_modified_time = os.path.getmtime(send_file)
            if (last_modified_time is None or current_modified_time > last_modified_time) and os.path.getsize(send_file) > 0:
                print("New messages detected in send_whatsapp.txt")

                last_modified_time = current_modified_time
                messages_to_send = load_messages_to_send()
                unsent_messages = []
                for message in messages_to_send:
                    success = send_message(message["contact_name"], message["message_text"])
                    if not success:
                        unsent_messages.append(message)

                save_remaining_messages(unsent_messages)

            time.sleep(5)

        except FileNotFoundError:
            print("send_whatsapp.txt not found. Creating file...")
            # ensure_send_file()
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error in send agent: {e}")
            time.sleep(5)

# Function to save received message details to file
# Function to save only unread messages to the file
def save_received_message(contact_name, received_time, message_text, unread_count):
    if contact_name:  # If there's an unread message, update saved_messages
        saved_messages[contact_name] = {
            "received_time": received_time,
            "unread_count": unread_count,
            "message_text": message_text,
        }
    
    # Write only unread messages to recv_whatsapp.txt
    with open(recv_file, "w", encoding="utf-8") as file:
        for contact, details in saved_messages.items():
            file.write(f"Contact Name/Phone Number: {contact}\n")
            file.write(f"Received Time: {details['received_time']}\n")
            file.write(f"Unread Messages Count: {details['unread_count']}\n")
            file.write(f"Message: {details['message_text']}\n")
            file.write("---------\n")


# Function to check for new messages without opening the chat
def recv_agent():
    print("Entering check_new_messages()")
    driver.get("https://web.whatsapp.com")
    time.sleep(8)

    while True:
        try:
            chat_containers = driver.find_elements(By.XPATH, "//div[@aria-label='Chat list']//div[contains(@class, '_ak72') and contains(@class, '_ak73')]")
            current_unread_contacts = set()

            for chat_container in chat_containers:
                try:
                    unread_indicator = chat_container.find_elements(By.XPATH, ".//span[contains(@aria-label, 'unread message')]")
                    contact_name = chat_container.find_element(By.XPATH, ".//span[@title]").get_attribute("title")
                    received_time_element = chat_container.find_elements(By.XPATH, ".//div[@class='_ak8i']")
                    received_time = received_time_element[0].text if received_time_element else "Unknown"
                    
                    # Check for voice message
                    voice_message = chat_container.find_elements(By.XPATH, ".//span[@data-icon='mic']")
                    # Check for audio message
                    audio_message = chat_container.find_elements(By.XPATH, ".//span[@data-icon='audio-refreshed-thin']")
                    # Check for photo message
                    photo_message = chat_container.find_elements(By.XPATH, ".//span[@data-icon='image-refreshed']")
                    # Check for video message
                    video_message = chat_container.find_elements(By.XPATH, ".//span[@data-icon='video-call-refreshed']")
                    # Check for sticker message
                    sticker_message = chat_container.find_elements(By.XPATH, ".//span[@data-icon='sticker-refreshed-thin']")
                    # Check for missed voice call
                    missed_call = chat_container.find_elements(By.XPATH, ".//span[@data-icon='voice-call-incoming-filled']")
                    # Check for missed video call
                    missed_video_call = chat_container.find_elements(By.XPATH, ".//span[@data-icon='video-call-incoming-filled']")
                    # Check for GIF message
                    gif_message = chat_container.find_elements(By.XPATH, ".//span[@data-icon='gif-refreshed']")
                    # Check for document message
                    document_message = chat_container.find_elements(By.XPATH, ".//span[@data-icon='document-refreshed-thin']")
                    # Check for location message
                    location_message = chat_container.find_elements(By.XPATH, ".//span[@data-icon='location-refreshed-outline']")
                    # Check for poll message
                    poll_message = chat_container.find_elements(By.XPATH, ".//span[@data-icon='poll-refreshed-thin']")
                    # Check for contact sharing message
                    contact_sharing = chat_container.find_elements(By.XPATH, ".//span[@data-icon='person-refreshed-outline-thin']")
                    # Check for event invitation message
                    event_message = chat_container.find_elements(By.XPATH, ".//span[@data-icon='ic-chatlist-event']")
                    
                    if voice_message:
                        # Get voice message duration
                        duration_element = chat_container.find_elements(By.XPATH, ".//span[@class='x78zum5 x1cy8zhl']//span[@dir='auto']")
                        duration = duration_element[0].text if duration_element else "Unknown"
                        message_text = f"Voice Message {duration}"
                        
                        # if unread_indicator:
                        #     print(f"Unread voice message detected from {contact_name}")
                        #     download_voice_message(driver, contact_name)
                    elif audio_message:
                        message_text = "Audio"
                        # if unread_indicator:
                        #     print(f"Unread audio message detected from {contact_name}")
                        #     download_audio_message(driver, contact_name)
                        
                    elif photo_message:
                        message_text = "Photo"
                    elif video_message:
                        message_text = "Video"
                    elif sticker_message:
                        message_text = "Sticker"
                    elif missed_call:
                        message_text = "Missed voice call"
                    elif missed_video_call:
                        message_text = "Missed video call"
                    elif gif_message:
                        message_text = "GIF"
                    elif document_message:
                        # Get document details
                        doc_text_element = chat_container.find_elements(By.XPATH, ".//span[@dir='ltr']")
                        doc_text = doc_text_element[0].text if doc_text_element else "Unknown document"
                        message_text = f'File "{doc_text}"'
                    elif location_message:
                        message_text = "Location"
                    elif poll_message:
                        # Get poll question
                        poll_text_element = chat_container.find_elements(By.XPATH, ".//span[@dir='ltr']")
                        poll_text = poll_text_element[0].text if poll_text_element else "Unknown poll"
                        message_text = f'Poll "{poll_text}"'
                    elif contact_sharing:
                        # Get contact name from the message content
                        contact_text_element = chat_container.find_elements(By.XPATH, ".//div[@class='_ak8k']//span[@dir='auto']")
                        contact_text = contact_text_element[0].text if contact_text_element else "Unknown contact"
                        message_text = f'Contact Sharing "{contact_text}"'
                    elif event_message:
                        # Get event details
                        event_text_element = chat_container.find_elements(By.XPATH, ".//div[@class='_ak8k']//span[@dir='ltr']")
                        event_text = event_text_element[0].text if event_text_element else "Unknown event"
                        message_text = f'Event "{event_text}"'
                    else:
                        # Regular text message
                        message_text_element = chat_container.find_elements(By.XPATH, ".//div[@class='_ak8k']//span[@dir='ltr']")
                        message_text = message_text_element[0].text if message_text_element else "No message text"

                    if unread_indicator:
                        unread_count = unread_indicator[0].get_attribute("aria-label").replace(" unread message", "").replace(" unread messages", "")
                        unread_count = ''.join(filter(str.isdigit, unread_count))
                        print(f"Unread Message from {contact_name} at {received_time}: {message_text} (Unread Count: {unread_count})")

                        save_received_message(contact_name, received_time, message_text, unread_count)
                        current_unread_contacts.add(contact_name)
                        
                        # # Forward the message if it's not an event
                        if not event_message:
                            print(f"Attempting to forward message from {contact_name}")
                            forward_recent_message_to(driver, contact_name, "xyz")  # Replace "Test Contact" with actual recipient
                
                except Exception as e:
                    print("Error extracting details from chat container:", e)

            # Remove read messages no longer in the chat list
            for contact in list(saved_messages.keys()):
                if contact not in current_unread_contacts:
                    print(f"Removing read message from {contact}")
                    del saved_messages[contact]
                    save_received_message("", "", "", 0)  # Update file after deletion

            time.sleep(5)
        
        except Exception as e:
            print("Error checking messages:", e)
            time.sleep(5)

# Function to handle graceful shutdown
def shutdown(signal, frame):
    print("\nShutting down gracefully...")
    driver.quit()
    sys.exit(0)

# Function to periodically update contacts
def contact_update_agent():
    """
    Periodically updates the contacts list from WhatsApp Web.
    Runs every 5 minutes to keep contacts.txt up to date.
    """
    print("Starting contact update agent...")
    while True:
        try:
            fetch_contacts_from_chat_list()
            time.sleep(300)  # Update every 5 minutes
        except Exception as e:
            print(f"Error in contact update agent: {e}")
            time.sleep(60)  # Wait 1 minute before retrying if there's an error

# Register the shutdown function for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, shutdown)


# Main execution with concurrent send and receive agents
if __name__ == "__main__":
    driver.get("https://web.whatsapp.com")
    time.sleep(8)  # Wait for WhatsApp Web to load

    # Initial contact fetch
    print("Performing initial contact fetch...")
    fetch_contacts_from_chat_list()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.submit(send_agent)
        executor.submit(recv_agent)
        executor.submit(contact_update_agent)  # Add contact update agent
