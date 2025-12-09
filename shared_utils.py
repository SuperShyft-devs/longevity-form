# shared_utils.py - Shared utility functions

from flask import session, redirect, url_for, request
from functools import wraps


def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def validate_booking_data(data):
    """Validate booking form data"""
    required_fields = ['first_name', 'last_name', 'phone', 'email', 'age', 'gender']
    
    errors = []
    
    # Check required fields
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field.replace('_', ' ').title()} is required")
    
    # Validate email format
    email = data.get('email', '')
    if email and '@' not in email:
        errors.append("Invalid email format")
    
    # Validate age
    try:
        age = int(data.get('age', 0))
        if age < 1 or age > 120:
            errors.append("Age must be between 1 and 120")
    except (ValueError, TypeError):
        errors.append("Age must be a valid number")
    
    # Validate phone
    phone = data.get('phone', '')
    if phone and len(phone) < 10:
        errors.append("Phone number must be at least 10 digits")
    
    return len(errors) == 0, errors
