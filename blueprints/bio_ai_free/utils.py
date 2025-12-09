# utils.py - Utility functions for date and time operations

import re
import math
from datetime import datetime, timedelta, date
from typing import List
from functools import wraps
from flask import session, redirect, url_for
from .config import config_manager


def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def is_valid_date(date_string: str) -> bool:
    """Check if the date string is valid and not in the past"""
    try:
        input_date = datetime.strptime(date_string, '%Y-%m-%d').date()
        today = date.today()
        return input_date >= today
    except ValueError:
        return False


def is_weekend(date_string: str) -> bool:
    """Check if the date falls on a weekend"""
    try:
        input_date = datetime.strptime(date_string, '%Y-%m-%d').date()
        return input_date.weekday() >= 5  # Saturday = 5, Sunday = 6
    except ValueError:
        return True  # If invalid date, treat as weekend (not available)


def generate_time_slots(start_time: str, end_time: str, duration: int) -> List[str]:
    """Generate time slots between start and end time with given duration"""
    slots = []
    start = datetime.strptime(start_time, '%H:%M')
    end = datetime.strptime(end_time, '%H:%M')
    
    current = start
    while current + timedelta(minutes=duration) <= end:
        slots.append(current.strftime('%H:%M'))
        current += timedelta(minutes=duration)
    
    return slots


def validate_booking_data(form_data):
    """
    Validate booking form data

    Returns:
        tuple: (is_valid: bool, error_message: str or None, processed_data: dict)
    """
    try:
        # Extract required fields
        first_name = form_data.get('first_name', '').strip()
        last_name = form_data.get('last_name', '').strip()
        phone = form_data.get('phone', '').strip().replace(' ', '')  # Remove spaces
        email = form_data.get('email', '').strip()
        age_str = form_data.get('age', '').strip()
        gender = form_data.get('gender', '').strip()
        appointment_date = form_data.get('appointment_date', '').strip()
        time_slot = form_data.get('time_slot', '').strip()

        # Optional fields
        address = form_data.get('address', '').strip()
        pin_code = form_data.get('pin_code', '').strip()

        print(f"Debug: first_name='{first_name}', last_name='{last_name}', phone='{phone}', email='{email}', age_str='{age_str}', gender='{gender}', appointment_date='{appointment_date}', time_slot='{time_slot}'")

        # Validate required fields presence
        if not all([first_name, last_name, email, age_str, gender, phone, appointment_date, time_slot]):
            print("Debug: Missing required fields")
            return False, 'Please fill in all required fields', None

        # Validate first_name: letters, spaces, apostrophe, hyphen
        if not re.match(r"^[a-zA-Z\s'-]+$", first_name):
            print(f"Debug: First name invalid: '{first_name}'")
            return False, 'First name contains invalid characters', None

        # Validate last_name: same as first_name
        if not re.match(r"^[a-zA-Z\s'-]+$", last_name):
            print(f"Debug: Last name invalid: '{last_name}'")
            return False, 'Last name contains invalid characters', None

        # Validate phone
        if phone.startswith('+'):
            # International: +code-number, code 1-3 digits
            if not re.match(r"^\+\d{1,3}-\d+$", phone):
                print(f"Debug: Phone intl invalid: '{phone}'")
                return False, 'Invalid international phone format. Use +code-number (e.g., +1-123456789)', None
        else:
            # India: 10 digits, no leading 0
            if not re.match(r"^[1-9]\d{9}$", phone):
                print(f"Debug: Phone India invalid: '{phone}'")
                return False, 'Invalid Indian phone number. Must be 10 digits starting with 1-9', None

        # Validate email
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            print(f"Debug: Email invalid: '{email}'")
            return False, 'Invalid email address', None

        # Validate gender: only M or F
        if gender not in ['M', 'F']:
            print(f"Debug: Gender invalid: '{gender}'")
            return False, 'Gender must be M or F', None

        # Validate age: positive integer
        if not re.match(r"^\d+$", age_str):
            print(f"Debug: Age not integer: '{age_str}'")
            return False, 'Age must be a positive integer', None
        age = int(age_str)
        if age <= 0:
            print(f"Debug: Age not positive: {age}")
            return False, 'Age must be a positive integer', None
        print(f"Debug: Age processed: {age}")

        # Validate appointment date
        if not is_valid_date(appointment_date):
            print(f"Debug: Appointment date invalid: '{appointment_date}'")
            return False, 'Appointment date must be a valid future date', None

        # Validate time slot format (HH:MM)
        if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', time_slot):
            print(f"Debug: Time slot invalid: '{time_slot}'")
            return False, 'Invalid time slot format', None

        # Validate Pincode (if provided, must be 6 digits)
        if pin_code and not re.match(r'^[0-9]{6}$', pin_code):
            print(f"Debug: Pincode invalid: '{pin_code}'")
            return False, 'Pincode must be exactly 6 digits', None

        # Prepare processed data
        processed_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'age': age,
            'gender': gender,
            'phone': phone,
            'address': address if address else None,
            'pin_code': pin_code if pin_code else None,
            'appointment_date': appointment_date,
            'time_slot': time_slot,
        }

        print("Debug: Validation passed")
        return True, None, processed_data

    except Exception as e:
        print(f"Debug: Exception: {str(e)}")
        return False, f'Error validating data: {str(e)}', None


