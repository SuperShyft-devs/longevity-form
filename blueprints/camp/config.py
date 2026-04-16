# config.py - Configuration settings for the booking system with date-specific cabin support

import json
import os
from typing import List, Dict, Any

# Flask Configuration
SECRET_KEY = 'your-secret-key-change-this'  # Change this in production
ADMIN_PASSWORD = '4*U8.@N|b$c3HCeq'  # Change this to your desired password

# Configuration file path
CONFIG_FILE = 'config_camp.json'

# Default configuration values with date-specific cabin configuration
DEFAULT_CONFIG = {
    'api_enabled': False,
    'metsights_api_key_male': '01993398a5aadb4a2798b6e98c2e08ee',
    'metsights_api_key_female': '01993398a5aadb4a2798b6e98c2e08ee',
    'engagement_id_male': '',
    'engagement_id_female': '',
    'database_name': 'bookings_camp.db',
    'slot_start_time': '06:00',
    'slot_end_time': '13:00',
    'slot_duration': 60,
    'max_people_per_slot': 2,
    'minimum_days_ahead': 2,
    # Email configuration
    'email_enabled': True,
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'pratheek.codimai@gmail.com',
    'sender_password': 'pabw pqcj tbee tnpf',  # Will need to be set in admin config
    'recipient_emails': ['amangupta73402@gmail.com']  # Multiple emails as array
}

# Database Configuration
DATABASE_NAME = 'bookings_camp.db'


class ConfigManager:
    """Manages dynamic configuration with file persistence and date-specific cabin support"""
    
    def __init__(self, config_file: str = CONFIG_FILE):
        self.config_file = config_file
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create with defaults"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Ensure all default keys exist
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
            except (json.JSONDecodeError, IOError):
                # If file is corrupted, use defaults
                return DEFAULT_CONFIG.copy()
        else:
            # Create file with defaults
            self._save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except IOError as e:
            print(f"Error saving configuration: {e}")
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value and save to file"""
        self._config[key] = value
        self._save_config(self._config)
    
    def update_multiple(self, updates: Dict[str, Any]) -> None:
        """Update multiple configuration values at once"""
        self._config.update(updates)
        self._save_config(self._config)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        return self._config.copy()
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values"""
        self._config = DEFAULT_CONFIG.copy()
        self._save_config(self._config)
    
    def get_cabin_config_for_date(self, date: str) -> Dict[str, Any]:
        """
        Get cabin configuration for a specific date
        
        Returns:
            Dict with keys: cabins_count, cabin_configs (or legacy format)
        """
        date_specific_cabins = self._config.get('date_specific_cabins', {})
        
        if date in date_specific_cabins:
            return date_specific_cabins[date]
    


# Global configuration manager instance
config_manager = ConfigManager()

# Export configuration values (for backward compatibility)



def reload_config():
    """Reload configuration from file - call this after updates"""
    config_manager._config = config_manager._load_config()
