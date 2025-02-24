from src.database.db_setup import ensure_database

# Ensure database is set up before anything else
ensure_database()

import threading
import signal
import sys
import time
from src.vision.camera_feed import process_camera_feed

# Event to control threads
stop_event = threading.Event()

# Shared data dictionary and lock
shared_data = {"active_person_id": None}
lock = threading.Lock()

def handle_exit(signal_received, frame):
    """
    Handles graceful exit on Ctrl+C or termination signal.
    """
    print("\n[INFO] Interrupt received. Cleaning up...")
    stop_event.set()

    # Wait for threads to stop
    camera_thread.join()

    print("[INFO] All processes stopped successfully.")
    sys.exit(0)

# Register signal handler for graceful shutdown
signal.signal(signal.SIGINT, handle_exit)

# Start threads with the stop_event passed for proper shutdown handling
camera_thread = threading.Thread(target=process_camera_feed, args=(stop_event, shared_data, lock), daemon=True)

print("Starting the AIR system... (Press Ctrl+C to stop)")
camera_thread.start()

# Allow background processes to initialize
time.sleep(5)
print("All processes are running!")

# Keep the main thread alive to listen for Ctrl+C
try:
    while not stop_event.is_set():
        time.sleep(1)  # Keep main thread alive without consuming CPU
except KeyboardInterrupt:
    handle_exit(signal.SIGINT, None)
