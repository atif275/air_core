import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Function to forward recent message from one contact to another
def forward_recent_message_to(driver, from_contact, to_contact):
    try:
        print(f"Attempting to forward message from {from_contact} to {to_contact}")
        
        # Click on the chat to open it
        chat_element = driver.find_element(By.XPATH, f"//span[@title='{from_contact}']")
        chat_element.click()
        print(f"Opened chat with {from_contact}")
        time.sleep(3)  # Wait for chat to load
        
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
        
        # Get the message content
        try:
            message_content = last_message.find_element(By.XPATH, ".//span[@dir='ltr']").text
            print(f"Latest message content: {message_content}")
            
            # Check if it's a small text message (less than 40 characters)
            if len(message_content.strip()) < 40:
                print("Small text message detected - cannot forward (WhatsApp limitation)")
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
                
        except:
            print("Could not extract message content (might be a media message)")
        
        print("Found most recent message")
        
        # Move to the message and wait for context menu to appear
        actions = ActionChains(driver)
        actions.move_to_element(last_message).perform()
        time.sleep(1)  # Wait for hover effect
        
        # Try both XPath patterns for context menu
        try:
            # First try: Voice message context menu pattern
            context_menu = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'message-in')]//div[@role='button' and @aria-label='Context menu']"))
            )
        except:
            try:
                # Second try: Text message context menu pattern - using exact classes from the HTML
                context_menu = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'x10l6tqk') and contains(@class, 'x1jzctok') and contains(@class, 'xnx3k43')]//div[@data-js-context-icon='true' and @aria-label='Context menu']"))
                )
            except Exception as e:
                print(f"Error finding context menu: {e}")
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
        
        # Move to the context menu and click it
        actions.move_to_element(context_menu).perform()
        time.sleep(0.5)  # Small wait to ensure menu is stable
        context_menu.click()
        print("Clicked context menu")
        time.sleep(1)
        
        # Find and click the Forward option
        forward_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Forward']"))
        )
        forward_button.click()
        print("Clicked Forward button")
        time.sleep(1)
        
        # Click the forward button in the footer
        footer_forward_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-tab='10' and @title='Forward']"))
        )
        footer_forward_button.click()
        print("Clicked footer Forward button")
        time.sleep(2)  # Wait for the search box to appear
        
        # Find the search box and type the recipient's name
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"))
        )
        search_box.clear()
        search_box.send_keys(to_contact)
        print(f"Typed recipient name: {to_contact}")
        time.sleep(1)
        
        # Press Enter to select the contact
        search_box.send_keys(Keys.ENTER)
        print("Selected recipient")
        time.sleep(2)  # Wait for selection to be confirmed
        
        # Verify the selected contact name
        try:
            selected_contact = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//span[@dir='auto' and contains(@class, 'x1rg5ohu')]"))
            )
            selected_name = selected_contact.text
            
            # Normalize both names for comparison (lowercase and remove extra spaces)
            normalized_to_contact = ' '.join(to_contact.lower().split())
            normalized_selected = ' '.join(selected_name.lower().split())
            
            print(f"Verifying contact: Expected '{normalized_to_contact}', Found '{normalized_selected}'")
            
            if normalized_to_contact == normalized_selected:
                # Click the send button
                send_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and .//span[@aria-label='Send']]"))
                )
                send_button.click()
                print("Message forwarded successfully")
                # Close chat after successful forward
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
                return True
            else:
                print(f"Contact name mismatch. Cannot forward to {to_contact}")
                # Click the close button to cancel forward
                close_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @aria-label='Close']"))
                )
                close_button.click()
                print("Closed forward interface")
                # Close chat after mismatch
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
                
        except Exception as e:
            print(f"Error verifying contact or sending message: {e}")
            # Try to close the forward interface if it's still open
            try:
                close_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @aria-label='Close']"))
                )
                close_button.click()
                print("Closed forward interface after error")
            except:
                pass
            # Close chat after error
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
        
    except Exception as e:
        print(f"Error forwarding message: {e}")
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
