import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Function to download voice message
def download_voice_message(driver, contact_name):
    try:
        print(f"Attempting to download voice message from {contact_name}")
        
        # Click on the chat to open it
        chat_element = driver.find_element(By.XPATH, f"//span[@title='{contact_name}']")
        chat_element.click()
        print(f"Opened chat with {contact_name}")
        time.sleep(3)  # Increased wait time for chat to load
        
        # Wait for voice message to be visible
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//span[@data-icon='audio-play']"))
            )
        except Exception as e:
            print("No voice message found in the chat")
            # Close chat before returning
            try:
                header_menu = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@id='main']//header//button[@data-tab='6' and @aria-label='Menu']"))
                )
                header_menu.click()
                print("Clicked header menu")
                time.sleep(1)
                
                close_chat = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Close chat']"))
                )
                close_chat.click()
                print("Closed chat")
            except Exception as e:
                print(f"Error closing chat: {e}")
            return False
        
        # Find all message containers and get the last one
        message_containers = driver.find_elements(By.XPATH, "//div[contains(@class, 'message-in')]")
        if not message_containers:
            print("No messages found in chat")
            # Close chat before returning
            try:
                header_menu = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@id='main']//header//button[@data-tab='6' and @aria-label='Menu']"))
                )
                header_menu.click()
                print("Clicked header menu")
                time.sleep(1)
                
                close_chat = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Close chat']"))
                )
                close_chat.click()
                print("Closed chat")
            except Exception as e:
                print(f"Error closing chat: {e}")
            return False
            
        # Get the last (most recent) message container
        last_message = message_containers[-1]
        
        # Check if it's a voice message
        try:
            voice_icon = last_message.find_element(By.XPATH, ".//span[@data-icon='audio-play']")
            print("Found voice message")
        except:
            print("Most recent message is not a voice message")
            # Close chat before returning
            try:
                header_menu = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@id='main']//header//button[@data-tab='6' and @aria-label='Menu']"))
                )
                header_menu.click()
                print("Clicked header menu")
                time.sleep(1)
                
                close_chat = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Close chat']"))
                )
                close_chat.click()
                print("Closed chat")
            except Exception as e:
                print(f"Error closing chat: {e}")
            return False
        
        # Move to the message and click the three dots menu
        actions = ActionChains(driver)
        actions.move_to_element(last_message).perform()
        time.sleep(1)
        
        # Find and click the three dots menu
        try:
            context_menu = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, ".//div[@role='button' and @aria-label='Context menu']"))
            )
            context_menu.click()
            print("Clicked context menu")
            time.sleep(1)
        except Exception as e:
            print(f"Error clicking context menu: {e}")
            # Close chat before returning
            try:
                header_menu = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@id='main']//header//button[@data-tab='6' and @aria-label='Menu']"))
                )
                header_menu.click()
                print("Clicked header menu")
                time.sleep(1)
                
                close_chat = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Close chat']"))
                )
                close_chat.click()
                print("Closed chat")
            except Exception as e:
                print(f"Error closing chat: {e}")
            return False
        
        # Find and click the download option
        try:
            download_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Download']"))
            )
            download_button.click()
            print("Clicked download button")
            
            # Wait for download to start
            time.sleep(2)
            print("Voice message download initiated")
        except Exception as e:
            print(f"Error downloading voice message: {e}")
            # Close chat before returning
            try:
                header_menu = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@id='main']//header//button[@data-tab='6' and @aria-label='Menu']"))
                )
                header_menu.click()
                print("Clicked header menu")
                time.sleep(1)
                
                close_chat = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Close chat']"))
                )
                close_chat.click()
                print("Closed chat")
            except Exception as e:
                print(f"Error closing chat: {e}")
            return False
        
        # Click the three dots menu in the right column header
        try:
            header_menu = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@id='main']//header//button[@data-tab='6' and @aria-label='Menu']"))
            )
            header_menu.click()
            print("Clicked header menu")
            time.sleep(1)
            
            # Click Close chat option
            close_chat = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Close chat']"))
            )
            close_chat.click()
            print("Closed chat")
            time.sleep(1)
            
            return True
        except Exception as e:
            print(f"Error closing chat: {e}")
            return False
        
    except Exception as e:
        print(f"Error downloading voice message: {e}")
        # Try to close chat in case of any error
        try:
            header_menu = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@id='main']//header//button[@data-tab='6' and @aria-label='Menu']"))
            )
            header_menu.click()
            print("Clicked header menu")
            time.sleep(1)
            
            close_chat = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Close chat']"))
            )
            close_chat.click()
            print("Closed chat")
        except Exception as e:
            print(f"Error closing chat: {e}")
        return False
