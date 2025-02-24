from dotenv import load_dotenv
import os
from typing import Optional

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
DATABASE_PATH = os.path.join(DATA_DIR, 'database.db')

# Create necessary directories
os.makedirs(DATA_DIR, exist_ok=True)

def load_env_variable(key: str, error_message: str) -> str:
    """
    Load and validate environment variable.
    
    Args:
        key: The environment variable key
        error_message: Error message if key is not found
    
    Returns:
        str: The environment variable value
    
    Raises:
        ValueError: If environment variable is not set
    """
    value = os.getenv(key)
    if not value:
        raise ValueError(error_message)
    return value

def load_api_key() -> str:
    """
    Load the OpenAI API key from environment variables.
    
    Returns:
        str: The OpenAI API key
    
    Raises:
        ValueError: If API key is not set
    """
    return load_env_variable("OPENAI_API_KEY", "Error: OpenAI API key is not set.")

def load_porcupine_api_key() -> str:
    """
    Load the Porcupine API key from environment variables.
    
    Returns:
        str: The Porcupine API key
    
    Raises:
        ValueError: If API key is not set
    """
    return load_env_variable("PORCUPINE_API_KEY", "Error: Porcupine API key is not set.")
