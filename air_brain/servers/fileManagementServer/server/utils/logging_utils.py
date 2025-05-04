import logging
from pathlib import Path

# Create logs directory if it doesn't exist
log_dir = Path("../logs")
log_dir.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "remote_agent.log"),
        logging.StreamHandler()
    ]
)

# Create a logger for agent-specific operations
agent_logger = logging.getLogger('agent')
agent_logger.setLevel(logging.INFO)

# Create a logger for connection operations
connection_logger = logging.getLogger('connection')
connection_logger.setLevel(logging.INFO)

# Create a logger for file operations
file_logger = logging.getLogger('file')
file_logger.setLevel(logging.INFO)

def log_agent_operation(operation: str, details: str):
    """Log agent-specific operations with clear formatting"""
    agent_logger.info(f"\n{'='*50}\nAGENT OPERATION: {operation}\n{'='*50}\n{details}\n")

def log_connection_operation(operation: str, details: str):
    """Log connection operations with clear formatting"""
    connection_logger.info(f"\n{'='*50}\nCONNECTION OPERATION: {operation}\n{'='*50}\n{details}\n")

def log_file_operation(operation: str, details: str):
    """Log file operations with clear formatting"""
    file_logger.info(f"\n{'='*50}\nFILE OPERATION: {operation}\n{'='*50}\n{details}\n") 