"""
WhatsApp Server - Flask-based server for WhatsApp integration
Runs on port 8767 and accessible both locally and on host IP
"""

from flask import Flask, jsonify, request
import socket
import threading
import os
from datetime import datetime
import logging
import time
import platform
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import concurrent.futures
import signal
import sys
import uuid
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Server configuration
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 8767

# WhatsApp Web configuration
ui_mode = True  # Set to True for visible mode, False for headless/background mode
driver = None

# Global login status
is_logged_in = False
login_monitoring_paused = False  # Flag to pause login monitoring

class WhatsAppServer:
    def __init__(self):
        self.app = app
        self.host = HOST
        self.port = PORT
        self.server_thread = None
        self.is_running = False
        self.driver = None
        
    def check_current_page_state(self):
        """Check and log the current page state of WhatsApp Web"""
        try:
            if not self.driver:
                logger.info("No driver available to check page state")
                return "no_driver"
            
            current_url = self.driver.current_url
            page_title = self.driver.title
            
            logger.info(f"Current URL: {current_url}")
            logger.info(f"Page Title: {page_title}")
            
            # Check for specific page indicators
            if "web.whatsapp.com" not in current_url:
                return "not_whatsapp"
            elif "chats" in current_url.lower() or "chat" in current_url.lower():
                return "chats_page"
            elif "login" in current_url.lower() or "auth" in current_url.lower():
                return "login_page"
            elif "qr" in current_url.lower():
                return "qr_page"
            else:
                return "unknown_page"
                
        except Exception as e:
            logger.error(f"Error checking page state: {e}")
            return "error"
    
    def check_existing_chrome_session(self):
        """Check if there's an existing Chrome session we can connect to"""
        try:
            # Try to connect to existing Chrome instance with timeout
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            
            # Try to create driver with existing session
            self.driver = webdriver.Chrome(options=chrome_options)
            
            logger.info("Successfully connected to existing Chrome session")
            
            # Check if we're already on WhatsApp Web
            current_url = self.driver.current_url
            if "web.whatsapp.com" in current_url:
                logger.info("Already on WhatsApp Web page")
                return True
            else:
                logger.info(f"Current page: {current_url}, navigating to WhatsApp Web...")
                self.driver.get("https://web.whatsapp.com")
                time.sleep(5)
                return True
                
        except Exception as e:
            logger.info(f"Could not connect to existing Chrome session: {e}")
            return False
    
    def get_chrome_profile_path(self):
        """Get the Chrome user data directory path based on OS"""
        logger.info("Setting up Chrome profile path...")
        system = platform.system()
        
        if system == "Windows":
            logger.info("Detected Windows OS")
            base_path = r"C:\Users\maaza\AppData\Local\Google\Chrome\User Data"
        elif system == "Darwin":  # macOS
            logger.info("Detected macOS")
            base_path = r"/Users/ATIFHANIF/Library/Application Support/Google/Chrome"
        elif system == "Linux":
            logger.info("Detected Linux OS")
            base_path = r"/home/yourusername/.config/google-chrome"
        else:
            raise ValueError("Unsupported operating system.")
        
        # Use a consistent profile directory for WhatsApp Bot
        profile_path = f"{base_path}/WhatsAppBot"
        logger.info(f"Using consistent Chrome profile: {profile_path}")
        
        return profile_path
    
    def initialize_whatsapp_web(self):
        """Initialize WhatsApp Web with Selenium"""
        logger.info("Initializing WhatsApp Web...")
        
        # First, try to connect to existing Chrome session with timeout
        try:
            import threading
            import queue
            
            # Create a queue to get the result
            result_queue = queue.Queue()
            
            def check_session():
                try:
                    result = self.check_existing_chrome_session()
                    result_queue.put(("success", result))
                except Exception as e:
                    result_queue.put(("error", str(e)))
            
            # Start the check in a separate thread with timeout
            check_thread = threading.Thread(target=check_session)
            check_thread.daemon = True
            check_thread.start()
            
            # Wait for result with timeout
            try:
                result_type, result = result_queue.get(timeout=5)  # 5 second timeout
                if result_type == "success" and result:
                    logger.info("Successfully connected to existing Chrome session")
                    # Start independent login monitoring immediately
                    self.start_independent_login_monitoring()
                    return True
                else:
                    logger.info("No existing Chrome session found or connection failed")
            except queue.Empty:
                logger.info("Timeout while checking for existing Chrome session")
                # Clean up any partial driver
                if hasattr(self, 'driver') and self.driver:
                    try:
                        self.driver.quit()
                        self.driver = None
                    except:
                        pass
                        
        except Exception as e:
            logger.info(f"Error checking existing session: {e}")
        
        # If no existing session, create a new one
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Creating new Chrome session... (Attempt {retry_count + 1}/{max_retries})")
                
                # Get Chrome profile path
                chrome_profile_path = self.get_chrome_profile_path()
                
                # Set up WebDriver options
                chrome_options = Options()
                chrome_options.add_argument(f"user-data-dir={chrome_profile_path}")
                chrome_options.add_argument("--no-first-run")
                chrome_options.add_argument("--no-default-browser-check")
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_argument("--remote-debugging-port=9222")  # Enable remote debugging
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                if not ui_mode:
                    logger.info("Running WhatsApp Web in headless (background) mode")
                    chrome_options.add_argument("--headless")
                    chrome_options.add_argument("--no-sandbox")
                    chrome_options.add_argument("--disable-dev-shm-usage")
                else:
                    logger.info("Running WhatsApp Web in UI (visible) mode")
                
                # Initialize the WebDriver
                self.driver = webdriver.Chrome(options=chrome_options)
                logger.info("WebDriver initialized successfully with the specified user profile.")
                
                # Navigate to WhatsApp Web
                self.driver.get("https://web.whatsapp.com")
                logger.info("Navigated to WhatsApp Web")
                
                # Wait for WhatsApp Web to load
                time.sleep(8)
                logger.info("WhatsApp Web loaded successfully")
                
                # Start independent login monitoring immediately
                self.start_independent_login_monitoring()
                
                return True
                
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                logger.error(f"Error initializing WhatsApp Web (Attempt {retry_count}/{max_retries}): {error_msg}")
                
                # Check if it's a profile in use error
                if "user data directory is already in use" in error_msg.lower():
                    logger.warning("Chrome profile is already in use. This might be a previous session.")
                    logger.info("Waiting 5 seconds for the previous session to close...")
                    time.sleep(5)
                elif "session not created" in error_msg.lower():
                    logger.warning("Session creation failed. This might be due to an existing Chrome instance.")
                    logger.info("Waiting 3 seconds before retry...")
                    time.sleep(3)
                
                # Clean up driver if it was created
                if hasattr(self, 'driver') and self.driver:
                    try:
                        self.driver.quit()
                        self.driver = None
                    except:
                        pass
                
                if retry_count < max_retries:
                    logger.info(f"Retrying in 3 seconds...")
                    time.sleep(3)
                else:
                    logger.error(f"Failed to initialize WhatsApp Web after {max_retries} attempts")
                    return False
        
        return False
    
    def start_independent_login_monitoring(self):
        """Start completely independent login monitoring that runs regardless of Flask server"""
        def independent_monitor():
            global is_logged_in, login_monitoring_paused
            print("🚀 INDEPENDENT WhatsApp login monitoring started!")
            logger.info("🚀 INDEPENDENT WhatsApp login monitoring started!")
            check_count = 0
            
            while True:  # Run forever
                try:
                    # Check if monitoring is paused
                    if login_monitoring_paused:
                        print("⏸️ Login monitoring is paused, waiting...")
                        logger.info("⏸️ Login monitoring is paused, waiting...")
                        time.sleep(1)  # Short wait when paused
                        continue
                    
                    check_count += 1
                    print(f"🔍 INDEPENDENT Login check #{check_count} - Checking for Chats button...")
                    logger.info(f"🔍 INDEPENDENT Login check #{check_count} - Checking for Chats button...")
                    
                    # Only check if driver exists
                    if not self.driver:
                        print("❌ No driver available, waiting 5 seconds...")
                        logger.info("❌ No driver available, waiting 5 seconds...")
                        time.sleep(5)
                        continue
                    
                    # Check for the Chats button to determine login status
                    chats_button = self.driver.find_elements(
                        By.XPATH, 
                        "//button[@aria-label='Chats' and @data-navbar-item='true']"
                    )
                    
                    if chats_button:
                        if not is_logged_in:
                            is_logged_in = True
                            print("✅ INDEPENDENT: LOGIN SUCCESSFUL - Chats button found! User is now logged in.")
                            logger.info("✅ INDEPENDENT: LOGIN SUCCESSFUL - Chats button found! User is now logged in.")
                        else:
                            print("✅ INDEPENDENT: User is logged in - Chats button found")
                            logger.info("✅ INDEPENDENT: User is logged in - Chats button found")
                    else:
                        if is_logged_in:
                            is_logged_in = False
                            print("❌ INDEPENDENT: LOGIN LOST - Chats button not found! User is no longer logged in.")
                            logger.info("❌ INDEPENDENT: LOGIN LOST - Chats button not found! User is no longer logged in.")
                        else:
                            print("❌ INDEPENDENT: Not logged in - Chats button not found")
                            logger.info("❌ INDEPENDENT: Not logged in - Chats button not found")
                    
                    print(f"⏰ INDEPENDENT: Waiting 2 seconds before next check... (Check #{check_count} completed)")
                    logger.info(f"⏰ INDEPENDENT: Waiting 2 seconds before next check... (Check #{check_count} completed)")
                    # Wait 2 seconds before next check
                    time.sleep(10)
                    
                except Exception as e:
                    print(f"🚨 INDEPENDENT: Error in login monitoring: {e}")
                    logger.error(f"🚨 INDEPENDENT: Error in login monitoring: {e}")
                    time.sleep(5)  # Wait longer if there's an error
        
        # Start the independent monitoring in a separate thread
        independent_thread = threading.Thread(target=independent_monitor, daemon=True, name="IndependentLoginMonitor")
        independent_thread.start()
        print("✅ INDEPENDENT WhatsApp login monitoring thread created and started")
        logger.info("✅ INDEPENDENT WhatsApp login monitoring thread created and started")
        
        # Verify thread is running
        if independent_thread.is_alive():
            print("✅ INDEPENDENT Login monitoring thread is alive and running")
            logger.info("✅ INDEPENDENT Login monitoring thread is alive and running")
        else:
            print("❌ INDEPENDENT Login monitoring thread failed to start")
            logger.error("❌ INDEPENDENT Login monitoring thread failed to start")
    
    def start_whatsapp_background_agent(self):
        """Start WhatsApp background agent to keep the session alive"""
        def whatsapp_agent():
            logger.info("Starting WhatsApp background agent...")
            while self.is_running and self.driver:
                try:
                    # Keep the WhatsApp Web session alive
                    # You can add periodic checks here if needed
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    logger.error(f"Error in WhatsApp background agent: {e}")
                    time.sleep(60)  # Wait longer if there's an error
        
        # Start the background agent in a separate thread
        whatsapp_thread = threading.Thread(target=whatsapp_agent, daemon=True)
        whatsapp_thread.start()
        logger.info("WhatsApp background agent started")
    
    def start_login_monitoring(self):
        """Start login monitoring to check if user is successfully logged in"""
        def login_monitor():
            global is_logged_in
            print("🚀 WhatsApp login monitoring thread started and running...")
            logger.info("🚀 WhatsApp login monitoring thread started and running...")
            check_count = 0
            
            while True:  # Run forever
                try:
                    check_count += 1
                    print(f"🔍 Login check #{check_count} - Checking for Chats button...")
                    logger.info(f"🔍 Login check #{check_count} - Checking for Chats button...")
                    
                    # Only check if driver exists
                    if not self.driver:
                        print("❌ No driver available, waiting 5 seconds...")
                        logger.info("❌ No driver available, waiting 5 seconds...")
                        time.sleep(5)
                        continue
                    
                    # Check for the Chats button to determine login status
                    chats_button = self.driver.find_elements(
                        By.XPATH, 
                        "//button[@aria-label='Chats' and @data-navbar-item='true']"
                    )
                    
                    if chats_button:
                        if not is_logged_in:
                            is_logged_in = True
                            print("✅ LOGIN SUCCESSFUL - Chats button found! User is now logged in.")
                            logger.info("✅ LOGIN SUCCESSFUL - Chats button found! User is now logged in.")
                        else:
                            print("✅ User is logged in - Chats button found")
                            logger.info("✅ User is logged in - Chats button found")
                    else:
                        if is_logged_in:
                            is_logged_in = False
                            print("❌ LOGIN LOST - Chats button not found! User is no longer logged in.")
                            logger.info("❌ LOGIN LOST - Chats button not found! User is no longer logged in.")
                        else:
                            print("❌ Not logged in - Chats button not found")
                            logger.info("❌ Not logged in - Chats button not found")
                    
                    print(f"⏰ Waiting 2 seconds before next check... (Check #{check_count} completed)")
                    logger.info(f"⏰ Waiting 2 seconds before next check... (Check #{check_count} completed)")
                    # Wait 2 seconds before next check
                    time.sleep(10)
                    
                except Exception as e:
                    print(f"🚨 Error in login monitoring: {e}")
                    logger.error(f"🚨 Error in login monitoring: {e}")
                    time.sleep(5)  # Wait longer if there's an error
            
            print("🛑 Login monitoring thread stopped")
            logger.info("🛑 Login monitoring thread stopped")
        
        # Start the login monitoring in a separate thread
        login_thread = threading.Thread(target=login_monitor, daemon=True, name="LoginMonitor")
        login_thread.start()
        print("✅ WhatsApp login monitoring thread created and started")
        logger.info("✅ WhatsApp login monitoring thread created and started")
        
        # Verify thread is running
        if login_thread.is_alive():
            print("✅ Login monitoring thread is alive and running")
            logger.info("✅ Login monitoring thread is alive and running")
        else:
            print("❌ Login monitoring thread failed to start")
            logger.error("❌ Login monitoring thread failed to start")
    
    def get_login_status(self):
        """Get current login status"""
        global is_logged_in
        return is_logged_in
    
    def update_login_status(self, status):
        """Update the global login status"""
        global is_logged_in
        is_logged_in = status
        logger.info(f"🔄 Login status updated to: {status}")
    
    def pause_login_monitoring(self):
        """Pause the login monitoring thread"""
        global login_monitoring_paused
        login_monitoring_paused = True
        print("⏸️ Login monitoring paused")
        logger.info("⏸️ Login monitoring paused")
    
    def resume_login_monitoring(self):
        """Resume the login monitoring thread"""
        global login_monitoring_paused
        login_monitoring_paused = False
        print("▶️ Login monitoring resumed")
        logger.info("▶️ Login monitoring resumed")
    
    def check_login_status_manually(self):
        """Manually check login status and update global variable"""
        global is_logged_in
        try:
            if not self.driver:
                return False
            
            # Check for the Chats button
            chats_button = self.driver.find_elements(
                By.XPATH, 
                "//button[@aria-label='Chats' and @data-navbar-item='true']"
            )
            
            new_status = len(chats_button) > 0
            
            # Update global status if it changed
            if new_status != is_logged_in:
                is_logged_in = new_status
                logger.info(f"🔄 Login status changed to: {new_status}")
            
            return new_status
            
        except Exception as e:
            logger.error(f"🚨 Error in manual login check: {e}")
            return False
    
    def get_local_ip(self):
        """Get the local IP address of the machine"""
        try:
            # Create a socket to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            logger.error(f"Error getting local IP: {e}")
            return "127.0.0.1"
    
    def start_server(self):
        """Start the Flask server in a separate thread"""
        if self.is_running:
            logger.warning("Server is already running")
            return
            
        try:
            # Initialize WhatsApp Web first
            if not self.initialize_whatsapp_web():
                logger.error("Failed to initialize WhatsApp Web. Server will start without WhatsApp integration.")
            else:
                # Start WhatsApp background agent
                self.start_whatsapp_background_agent()
                # Note: Login monitoring is now started independently when driver is initialized
            
            # Start Flask server
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True
            )
            self.server_thread.start()
            self.is_running = True
            
            local_ip = self.get_local_ip()
            logger.info(f"WhatsApp Server started successfully!")
            logger.info(f"Local access: http://127.0.0.1:{PORT}")
            logger.info(f"Network access: http://{local_ip}:{PORT}")
            logger.info(f"Server running on port {PORT}")
            if self.driver:
                logger.info("WhatsApp Web is running in background")
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self.is_running = False
    
    def _run_server(self):
        """Internal method to run the Flask server"""
        try:
            self.app.run(
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            logger.error(f"Server error: {e}")
            self.is_running = False
    
    def stop_server(self):
        """Stop the Flask server and WhatsApp Web"""
        if self.is_running:
            logger.info("Stopping WhatsApp Server...")
            self.is_running = False
            
            # Close WhatsApp Web driver
            if self.driver:
                try:
                    logger.info("Closing WhatsApp Web...")
                    self.driver.quit()
                    logger.info("WhatsApp Web closed successfully")
                except Exception as e:
                    logger.error(f"Error closing WhatsApp Web: {e}")
            
            logger.info("Server stopped")

# Create server instance
whatsapp_server = WhatsAppServer()

# Flask Routes
@app.route('/', methods=['GET'])
def welcome():
    """Welcome route for the WhatsApp server"""
    whatsapp_status = "running" if whatsapp_server.driver else "not available"
    login_status = "logged_in" if whatsapp_server.get_login_status() else "not_logged_in"
    return jsonify({
        'message': 'Welcome to WhatsApp Server',
        'status': 'running',
        'whatsapp_web': whatsapp_status,
        'login_status': login_status,
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'welcome': '/',
            'health': '/health',
            'status': '/status',
            'register': '/register',
            'login_status': '/login-status',
            'test_login_check': '/test-login-check',
            'force_update_login_status': '/force-update-login-status'
        }
    })

@app.route('/register', methods=['POST'])
def register():
    """Register endpoint for user registration with country and phone number"""
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'No data provided',
                'message': 'Please provide country and phone_number in JSON format'
            }), 400
        
        # Extract country and phone_number
        country = data.get('country')
        phone_number = data.get('phone_number')
        
        # Validate required fields
        if not country:
            return jsonify({
                'error': 'Missing country',
                'message': 'country field is required'
            }), 400
            
        if not phone_number:
            return jsonify({
                'error': 'Missing phone_number',
                'message': 'phone_number field is required'
            }), 400
        
        # Print incoming data
        print("=" * 50)
        print("REGISTRATION REQUEST RECEIVED")
        print("=" * 50)
        print(f"Country: {country}")
        print(f"Phone Number: {phone_number}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 50)
        
        # Log the registration attempt
        logger.info(f"Registration attempt - Country: {country}, Phone: {phone_number}")
        
        # Check if user is already logged in
        if whatsapp_server.get_login_status():
            logger.info("User is already logged in - skipping login process")
            return jsonify({
                'message': 'Already connected',
                'data': {
                    'country': country,
                    'phone_number': phone_number
                },
                'whatsapp_web': {
                    'status': 'available' if whatsapp_server.driver else 'not available',
                    'login_status': 'already_logged_in',
                    'phone_login_clicked': False,
                    'country_selected': False,
                    'phone_number_filled': False,
                    'next_button_clicked': False,
                    'verification_code': None
                },
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }), 200
        
        # Pause login monitoring during registration process
        whatsapp_server.pause_login_monitoring()
        logger.info("Paused login monitoring for registration process")
        
        try:
            # Click "Log in with phone number instead" button if WhatsApp Web is available
            phone_login_success = False
            country_selection_success = False
            phone_fill_success = False
            next_button_success = False
            whatsapp_code = None
            if whatsapp_server.driver:
                # Check current page state first
                page_state = whatsapp_server.check_current_page_state()
                logger.info(f"Current page state: {page_state}")
                
                # If already on chats page, user is logged in
                if page_state == "chats_page":
                    logger.info("User is already on chats page - already logged in")
                    whatsapp_server.resume_login_monitoring()
                    return jsonify({
                        'message': 'Already connected',
                        'data': {
                            'country': country,
                            'phone_number': phone_number
                        },
                        'whatsapp_web': {
                            'status': 'available',
                            'page_state': page_state,
                            'login_status': 'already_logged_in',
                            'phone_login_clicked': False,
                            'country_selected': False,
                            'phone_number_filled': False,
                            'next_button_clicked': False,
                            'verification_code': None
                        },
                        'timestamp': datetime.now().isoformat(),
                        'status': 'success'
                    }), 200
                
                # If not on login page, try to navigate to WhatsApp Web
                if page_state not in ["login_page", "qr_page"]:
                    logger.info("Not on login page, navigating to WhatsApp Web...")
                    whatsapp_server.driver.get("https://web.whatsapp.com")
                    time.sleep(5)
                    page_state = whatsapp_server.check_current_page_state()
                    logger.info(f"Page state after navigation: {page_state}")
                
                try:
                    logger.info("Attempting to click 'Log in with phone number instead' button...")
                    
                    # Wait for the button to be present and clickable
                    # Try multiple XPath strategies to find the phone login button
                    phone_login_button = None
                    xpath_strategies = [
                        "//div[contains(text(), 'Log in with phone number')]",  # Direct text match
                        "//div[@role='button']//div[contains(text(), 'Log in with phone number')]",  # With role attribute
                        "//div[contains(@class, 'x1c4vz4f')]//div[contains(text(), 'Log in with phone number')]",  # With class
                        "//div[contains(text(), 'Log in with phone number instead')]",  # Original fallback
                        "//div[@role='button' and contains(., 'Log in with phone number')]"  # Role + contains
                    ]
                    
                    for i, xpath in enumerate(xpath_strategies):
                        try:
                            logger.info(f"Trying phone login button XPath strategy {i+1}: {xpath}")
                            phone_login_button = WebDriverWait(whatsapp_server.driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, xpath))
                            )
                            logger.info(f"Found phone login button using strategy {i+1}")
                            break
                        except TimeoutException:
                            logger.info(f"Strategy {i+1} failed, trying next...")
                            continue
                    
                    if phone_login_button:
                        # Click the button
                        phone_login_button.click()
                        logger.info("Successfully clicked 'Log in with phone number instead' button")
                        phone_login_success = True
                        
                        # Wait a moment for the page to transition
                        time.sleep(2)
                    else:
                        logger.warning("Phone login button not found with any XPath strategy")
                        phone_login_success = False
                        # Resume login monitoring if button not found
                        whatsapp_server.resume_login_monitoring()
                        raise TimeoutException("Phone login button not found")
                    
                    # Now select the country
                    try:
                        logger.info(f"Attempting to select country: {country}")
                        
                        # Click the country dropdown button
                        country_button = WebDriverWait(whatsapp_server.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., '🇵🇰') or contains(., 'Pakistan')]"))
                        )
                        country_button.click()
                        logger.info("Clicked country dropdown button")
                        time.sleep(1)
                        
                        # Wait for the search input to be present and type the country name
                        search_input = WebDriverWait(whatsapp_server.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true' and @role='textbox']"))
                        )
                        
                        # Clear and type the country name
                        search_input.clear()
                        search_input.send_keys(country)
                        logger.info(f"Typed country name: {country}")
                        time.sleep(1)
                        
                        # Press Enter to search
                        search_input.send_keys(Keys.ENTER)
                        logger.info("Pressed Enter to search")
                        time.sleep(1)
                        
                        # Click the first country result
                        first_country_result = WebDriverWait(whatsapp_server.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[@role='listitem']"))
                        )
                        first_country_result.click()
                        logger.info("Clicked first country result")
                        country_selection_success = True
                        
                        # Wait a moment for the country selection to complete
                        time.sleep(1)
                        
                    except TimeoutException:
                        logger.warning("Country selection elements not found - may already be on correct country")
                        country_selection_success = False
                    except Exception as e:
                        logger.error(f"Error selecting country: {e}")
                        country_selection_success = False
                    
                    # Now fill the phone number input field
                    try:
                        logger.info(f"Attempting to fill phone number: {phone_number}")
                        
                        # Wait for the phone input field to be present
                        phone_input = WebDriverWait(whatsapp_server.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, "//input[@aria-label='Type your phone number.']"))
                        )
                        
                        # Clear the existing value and fill with the phone number
                        phone_input.clear()
                        phone_input.send_keys(phone_number)
                        logger.info(f"Successfully filled phone number: {phone_number}")
                        phone_fill_success = True
                        
                        # Wait a moment for the input to be processed
                        time.sleep(1)
                        
                    except TimeoutException:
                        logger.warning("Phone input field not found - form may not have loaded yet")
                        phone_fill_success = False
                    except Exception as e:
                        logger.error(f"Error filling phone number: {e}")
                        phone_fill_success = False
                    
                    # Now click the Next button
                    try:
                        logger.info("Attempting to click Next button...")
                        
                        # Wait for the Next button to be present and clickable
                        # Try multiple XPath strategies to find the Next button
                        next_button = None
                        xpath_strategies = [
                            "//button[.//div[contains(text(), 'Next')]]",  # Strategy 2 (working) moved to first
                            "//button[contains(text(), 'Next')]",          # Strategy 1 moved to second
                            "//div[contains(@class, 'x1hq5gj4')]//button",
                            "//button[@class and contains(@class, 'x889kno') and contains(@class, 'x1rl75mt')]"
                        ]
                        
                        for i, xpath in enumerate(xpath_strategies):
                            try:
                                logger.info(f"Trying Next button XPath strategy {i+1}: {xpath}")
                                next_button = WebDriverWait(whatsapp_server.driver, 5).until(
                                    EC.element_to_be_clickable((By.XPATH, xpath))
                                )
                                logger.info(f"Found Next button using strategy {i+1}")
                                break
                            except TimeoutException:
                                logger.info(f"Strategy {i+1} failed, trying next...")
                                continue
                        
                        if next_button:
                            # Check if button is enabled
                            if next_button.is_enabled():
                                # Click the Next button
                                next_button.click()
                                logger.info("Successfully clicked Next button")
                                next_button_success = True
                                
                                # Resume login monitoring after Next button is clicked
                                whatsapp_server.resume_login_monitoring()
                                logger.info("Resumed login monitoring after Next button click")
                                
                                # Wait 1 second for the verification screen to load
                                time.sleep(1)
                                
                                # Extract the verification code
                                try:
                                    logger.info("Attempting to extract verification code...")
                                    
                                    # Wait for the verification code screen to be present
                                    verification_screen = WebDriverWait(whatsapp_server.driver, 10).until(
                                        EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Enter code on phone:']"))
                                    )
                                    
                                    # Extract all code characters
                                    code_elements = whatsapp_server.driver.find_elements(
                                        By.XPATH, 
                                        "//div[@aria-label='Enter code on phone:']//span[@class='x2b8uid xk50ysn x1aueamr x1jzgpr8 xzwifym']"
                                    )
                                    
                                    if code_elements:
                                        # Extract the verification code
                                        verification_code = ''.join([element.text for element in code_elements])
                                        logger.info(f"Successfully extracted verification code: {verification_code}")
                                        
                                        # Store the verification code for response
                                        whatsapp_code = verification_code
                                    else:
                                        logger.warning("No verification code elements found")
                                        whatsapp_code = None
                                        
                                except TimeoutException:
                                    logger.warning("Verification screen not found - may not have loaded yet")
                                    whatsapp_code = None
                                except Exception as e:
                                    logger.error(f"Error extracting verification code: {e}")
                                    whatsapp_code = None
                            else:
                                logger.warning("Next button found but is disabled - may need to wait for validation")
                                next_button_success = False
                                whatsapp_code = None
                                # Resume login monitoring even if button is disabled
                                whatsapp_server.resume_login_monitoring()
                        else:
                            logger.warning("Next button not found with any XPath strategy")
                            next_button_success = False
                            whatsapp_code = None
                            # Resume login monitoring if button not found
                            whatsapp_server.resume_login_monitoring()
                        
                        # Wait a moment for the page to transition to the next step
                        time.sleep(2)
                        
                    except TimeoutException:
                        logger.warning("Next button not found or not clickable - may be disabled due to validation")
                        next_button_success = False
                        # Resume login monitoring on timeout
                        whatsapp_server.resume_login_monitoring()
                    except Exception as e:
                        logger.error(f"Error clicking Next button: {e}")
                        next_button_success = False
                        # Resume login monitoring on error
                        whatsapp_server.resume_login_monitoring()
                    
                except TimeoutException:
                    logger.warning("Phone login button not found or not clickable - WhatsApp Web may not be on login page")
                    phone_login_success = False
                    # Resume login monitoring on timeout
                    whatsapp_server.resume_login_monitoring()
                except Exception as e:
                    logger.error(f"Error clicking phone login button: {e}")
                    phone_login_success = False
                    # Resume login monitoring on error
                    whatsapp_server.resume_login_monitoring()
            else:
                logger.warning("WhatsApp Web driver not available - skipping phone login button click")
                phone_login_success = False
                # Resume login monitoring if no driver
                whatsapp_server.resume_login_monitoring()
                
        except Exception as e:
            logger.error(f"Unexpected error during registration: {e}")
            # Resume login monitoring on any unexpected error
            whatsapp_server.resume_login_monitoring()
            raise e
        
        # Return success response with phone login, country selection, phone fill, and next button status
        return jsonify({
            'message': 'Registration data received successfully',
            'data': {
                'country': country,
                'phone_number': phone_number
            },
            'whatsapp_web': {
                'status': 'available' if whatsapp_server.driver else 'not available',
                'phone_login_clicked': phone_login_success,
                'country_selected': country_selection_success,
                'phone_number_filled': phone_fill_success,
                'next_button_clicked': next_button_success,
                'verification_code': whatsapp_code
            },
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in registration: {str(e)}")
        return jsonify({
            'error': 'Registration failed',
            'message': 'An error occurred while processing registration',
            'details': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    whatsapp_status = "connected" if whatsapp_server.driver else "disconnected"
    return jsonify({
        'status': 'healthy',
        'server': 'whatsapp_server',
        'whatsapp_web': whatsapp_status,
        'timestamp': datetime.now().isoformat(),
        'uptime': 'running'
    })

@app.route('/status', methods=['GET'])
def server_status():
    """Server status endpoint"""
    local_ip = whatsapp_server.get_local_ip()
    whatsapp_status = "running" if whatsapp_server.driver else "not available"
    return jsonify({
        'server_name': 'WhatsApp Server',
        'version': '1.0.0',
        'status': 'running' if whatsapp_server.is_running else 'stopped',
        'whatsapp_web': whatsapp_status,
        'host': HOST,
        'port': PORT,
        'local_url': f'http://127.0.0.1:{PORT}',
        'network_url': f'http://{local_ip}:{PORT}',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/login-status', methods=['GET'])
def login_status():
    """Check WhatsApp Web login status"""
    try:
        current_login_status = whatsapp_server.get_login_status()
        return jsonify({
            'login_status': 'logged_in' if current_login_status else 'not_logged_in',
            'is_logged_in': current_login_status,
            'whatsapp_web': 'available' if whatsapp_server.driver else 'not_available',
            'timestamp': datetime.now().isoformat(),
            'message': 'User is logged in to WhatsApp Web' if current_login_status else 'User is not logged in to WhatsApp Web'
        }), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to check login status',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/test-login-check', methods=['GET'])
def test_login_check():
    """Manually test login check to verify monitoring is working"""
    try:
        if not whatsapp_server.driver:
            return jsonify({
                'error': 'WhatsApp Web driver not available',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        # Use the new manual check function that updates global status
        current_login_status = whatsapp_server.check_login_status_manually()
        
        # Also get the raw button count for debugging
        chats_button = whatsapp_server.driver.find_elements(
            By.XPATH, 
            "//button[@aria-label='Chats' and @data-navbar-item='true']"
        )
        
        return jsonify({
            'manual_check': 'success',
            'chats_button_found': len(chats_button) > 0,
            'chats_button_count': len(chats_button),
            'current_login_status': current_login_status,
            'global_login_status': whatsapp_server.get_login_status(),
            'timestamp': datetime.now().isoformat(),
            'message': f'Manual login check completed. Chats button found: {len(chats_button) > 0}, Login status: {current_login_status}'
        }), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to perform manual login check',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/force-update-login-status', methods=['POST'])
def force_update_login_status():
    """Force update the login status and restart monitoring if needed"""
    try:
        if not whatsapp_server.driver:
            return jsonify({
                'error': 'WhatsApp Web driver not available',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        # Force check and update login status
        new_status = whatsapp_server.check_login_status_manually()
        
        return jsonify({
            'force_update': 'success',
            'new_login_status': new_status,
            'global_login_status': whatsapp_server.get_login_status(),
            'timestamp': datetime.now().isoformat(),
            'message': f'Login status force updated to: {new_status}'
        }), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to force update login status',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested endpoint does not exist',
        'available_endpoints': ['/', '/health', '/status', '/register']
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'error': 'Internal server error',
        'message': 'Something went wrong on the server'
    }), 500

def shutdown_handler(signal, frame):
    """Handle graceful shutdown"""
    print("\nShutting down gracefully...")
    whatsapp_server.stop_server()
    sys.exit(0)

def main():
    """Main function to run the server"""
    print("=" * 50)
    print("WhatsApp Server with WhatsApp Web Integration")
    print("=" * 50)
    print(f"Starting server on port {PORT}...")
    
    # Register shutdown handler
    signal.signal(signal.SIGINT, shutdown_handler)
    
    # Start the server
    whatsapp_server.start_server()
    
    try:
        # Keep the main thread alive
        while whatsapp_server.is_running:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        whatsapp_server.stop_server()
        print("Server stopped.")

if __name__ == '__main__':
    main() 