# booking_service.py - Business logic for booking availability

from typing import Dict, List
from .database import get_db_connection
from .utils import generate_time_slots, is_valid_date
from .config import config_manager



class ConsultationService:
    """Service class for consultation booking operations with dynamic configuration support and sequential date logic"""
    
    @staticmethod
    def get_total_consultation_slots_count():
        """Get total number of consultation time slots available per day"""
        # Since consultation is now just yes/no, return a fixed number
        # This method is kept for backward compatibility but simplified
        return 1  # Only one "slot" since it's just yes/no
    
    @staticmethod
    def get_available_slots(date: str) -> List[str]:
        """Get available time slots for consultations on a given date"""
        # Since consultation is now just yes/no, return empty list
        # This method is kept for backward compatibility but simplified
        return []
    
    @staticmethod
    def get_sequential_date_availability() -> Dict:
        """
        Get consultation date availability - simplified since consultation is now just yes/no.
        """
        # Since consultation is now just yes/no, return empty dict
        # This method is kept for backward compatibility but simplified
        return {}
    
    @staticmethod
    def validate_date_sequential_availability(date: str) -> tuple:
        """
        Validate if a consultation date can be booked - simplified since consultation is now just yes/no.

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        # Since consultation is now just yes/no, always return valid
        # This method is kept for backward compatibility but simplified
        return True, None


class BookingManager:
    """Main booking management class"""
    
    def __init__(self):
        self.consultation_service = ConsultationService()
    
    def validate_slot_availability(self, booking_data):
        """
        Validate if the selected slots are still available - simplified since consultation is now just yes/no

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        # Since consultation is now just yes/no, no slot validation needed
        # This method is kept for backward compatibility but simplified
        return True, None
