"""Shared configuration settings."""
import os
import sys

# Get the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Database path - use the main database in the root data folder
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'database.db')

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) 