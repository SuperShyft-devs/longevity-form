# config_validator.py - Utility to validate configuration changes for Firozpur camp

from datetime import datetime
from typing import Dict, List, Tuple, Any


class ConfigValidator:
    """Validates configuration changes before applying them"""
    
    @staticmethod
    def validate_time_format(time_str: str) -> bool:
        """Validate time format (HH:MM)"""
        try:
            datetime.strptime(time_str, '%H:%M')
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_date_format(date_str: str) -> bool:
        """Validate date format (YYYY-MM-DD)"""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_time_range(start_time: str, end_time: str) -> bool:
        """Validate that start time is before end time"""
        try:
            start = datetime.strptime(start_time, '%H:%M')
            end = datetime.strptime(end_time, '%H:%M')
            return start < end
        except ValueError:
            return False
    
    @staticmethod
    def validate_positive_integer(value: Any, min_val: int = 1, max_val: int = None) -> bool:
        """Validate positive integer within range"""
        try:
            int_val = int(value)
            if int_val < min_val:
                return False
            if max_val and int_val > max_val:
                return False
            return True
        except (ValueError, TypeError):
            return False
    
    
    @staticmethod
    def validate_dates_list(dates: List[str]) -> Tuple[bool, str]:
        """Validate dates list"""
        if not dates:
            return False, "At least one date is required"
        
        # Check for duplicates
        if len(dates) != len(set(dates)):
            return False, "Duplicate dates are not allowed"
        
        # Validate date formats
        for date_str in dates:
            if not ConfigValidator.validate_date_format(date_str):
                return False, f"Invalid date format: {date_str}"
        
        return True, ""
    
    @staticmethod
    def validate_date_specific_cabins(date_specific_cabins: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate date-specific cabin configurations with cabin-specific capacity support"""
        if not isinstance(date_specific_cabins, dict):
            return False, "Date-specific cabins must be a dictionary"
        
        for date_str, cabin_config in date_specific_cabins.items():
            # Validate date format
            if not ConfigValidator.validate_date_format(date_str):
                return False, f"Invalid date format in date-specific cabins: {date_str}"
            
            # Validate cabin config structure
            if not isinstance(cabin_config, dict):
                return False, f"Cabin configuration for {date_str} must be a dictionary"
            
            required_keys = ['cabins_count']
            for key in required_keys:
                if key not in cabin_config:
                    return False, f"Missing '{key}' in cabin configuration for {date_str}"
            
            # Validate cabins_count
            if not ConfigValidator.validate_positive_integer(cabin_config['cabins_count'], 1, 20):
                return False, f"Invalid cabins_count for {date_str}: must be between 1-20"
            
            # Check if using new cabin_configs format or legacy format
            if 'cabin_configs' in cabin_config:
                # New format validation with individual cabin configs
                cabin_configs = cabin_config['cabin_configs']
                if not isinstance(cabin_configs, list):
                    return False, f"cabin_configs for {date_str} must be a list"
                
                if len(cabin_configs) != cabin_config['cabins_count']:
                    return False, f"Number of cabin_configs ({len(cabin_configs)}) doesn't match cabins_count ({cabin_config['cabins_count']}) for {date_str}"
                
                # Validate each cabin config
                cabin_names = []
                for i, cabin_cfg in enumerate(cabin_configs):
                    if not isinstance(cabin_cfg, dict):
                        return False, f"Cabin config {i+1} for {date_str} must be a dictionary"
                    
                    # Check required keys for each cabin
                    if 'name' not in cabin_cfg or 'people_per_cabin' not in cabin_cfg:
                        return False, f"Cabin config {i+1} for {date_str} must have 'name' and 'people_per_cabin'"
                    
                    # Validate cabin name
                    if not cabin_cfg['name'] or not cabin_cfg['name'].strip():
                        return False, f"Empty cabin name for cabin {i+1} on {date_str}"
                    
                    cabin_names.append(cabin_cfg['name'].strip())
                    
                    # Validate people_per_cabin for this specific cabin
                    if not ConfigValidator.validate_positive_integer(cabin_cfg['people_per_cabin'], 1, 10):
                        return False, f"Invalid people_per_cabin for cabin {i+1} on {date_str}: must be between 1-10"
                
                # Check for duplicate cabin names within the same date
                if len(cabin_names) != len(set(cabin_names)):
                    return False, f"Duplicate cabin names found for {date_str}"
                
            else:
                # Legacy format validation (for backward compatibility)
                if 'cabin_names' in cabin_config:
                    cabin_names = cabin_config['cabin_names']
                    if not isinstance(cabin_names, list):
                        return False, f"Cabin names for {date_str} must be a list"
                    
                    if len(cabin_names) != cabin_config['cabins_count']:
                        return False, f"Number of cabin names ({len(cabin_names)}) doesn't match cabins_count ({cabin_config['cabins_count']}) for {date_str}"
                    
                    # Check for duplicate cabin names within the same date
                    if len(cabin_names) != len(set(cabin_names)):
                        return False, f"Duplicate cabin names found for {date_str}"
                    
                    # Validate each cabin name is not empty
                    for i, name in enumerate(cabin_names):
                        if not name or not name.strip():
                            return False, f"Empty cabin name at position {i+1} for {date_str}"
                
                # Validate people_per_cabin (legacy single value)
                if 'people_per_cabin' in cabin_config:
                    if not ConfigValidator.validate_positive_integer(cabin_config['people_per_cabin'], 1, 10):
                        return False, f"Invalid people_per_cabin for {date_str}: must be between 1-10"
        
        return True, ""
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate entire configuration
        
        Returns:
            tuple: (is_valid: bool, errors: List[str])
        """
        errors = []
        
        
        
        
        return len(errors) == 0, errors
