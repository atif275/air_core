import json
import os
from typing import Dict, Optional, List
from datetime import datetime

class ConnectionConfig:
    def __init__(self):
        self.config_file = 'connection_config.json'
        self.default_config = {
            'current_connection': {
                'hostname': '',
                'port': '',
                'username': '',
                'password': ''
            },
            'connection_history': []
        }
        self._ensure_config_file()

    def _ensure_config_file(self):
        """Ensure the config file exists with default values"""
        if not os.path.exists(self.config_file):
            self.save_config(self.default_config)

    def save_config(self, config: Dict[str, str]) -> None:
        """Save connection configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {str(e)}")

    def load_config(self) -> Dict[str, str]:
        """Load connection configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                # Ensure all required fields exist
                if 'current_connection' not in config:
                    config['current_connection'] = self.default_config['current_connection']
                if 'connection_history' not in config:
                    config['connection_history'] = []
                return config
        except (FileNotFoundError, json.JSONDecodeError):
            return self.default_config

    def update_config(self, new_config: Dict[str, str]) -> None:
        """Update configuration with new values and maintain history"""
        try:
            current_config = self.load_config()
            
            # Add current connection to history before updating
            if current_config['current_connection']['hostname']:  # Only add if not empty
                history_entry = {
                    **current_config['current_connection'],
                    'timestamp': datetime.now().isoformat()
                }
                current_config['connection_history'].append(history_entry)
                
                # Keep only last 10 connections in history
                if len(current_config['connection_history']) > 10:
                    current_config['connection_history'] = current_config['connection_history'][-10:]
            
            # Update current connection
            current_config['current_connection'].update(new_config)
            
            self.save_config(current_config)
            print(f"Config updated. Current connection: {current_config['current_connection']}")
            print(f"History length: {len(current_config['connection_history'])}")
        except Exception as e:
            print(f"Error updating config: {str(e)}")

    def get_current_connection(self) -> Dict[str, str]:
        """Get current connection details"""
        config = self.load_config()
        return config['current_connection']

    def get_connection_history(self) -> List[Dict[str, str]]:
        """Get connection history"""
        config = self.load_config()
        return config['connection_history']

# Create a singleton instance
connection_config = ConnectionConfig()