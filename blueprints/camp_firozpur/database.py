# database.py - Database initialization and operations for Firozpur camp

import sqlite3
from .config import config_manager


def init_db():
    """Initialize the database with required tables"""
    database_name = config_manager.get('database_name', 'bookings_camp_firozpur.db')
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()
    
    # Create bookings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            doctor_consultation TEXT NOT NULL DEFAULT 'Yes',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Note: reference_options table removed as reference field is no longer used
    
    conn.commit()
    conn.close()


def get_db_connection():
    """Get database connection"""
    database_name = config_manager.get('database_name', 'bookings_camp_firozpur.db')
    return sqlite3.connect(database_name)


def save_booking(booking_data):
    """
    Save booking to database
    
    Args:
        booking_data (dict): Dictionary containing booking information
    
    Returns:
        int: Booking ID if successful
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO bookings (
            first_name, last_name, phone, email, age, gender, doctor_consultation
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        booking_data['first_name'], booking_data['last_name'], booking_data['phone'],
        booking_data['email'], booking_data['age'], booking_data['gender'],
        booking_data.get('doctor_consultation', 'Yes')
    ))

    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()

    return booking_id


def get_booking_by_id(booking_id):
    """Get booking details by ID"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,))
    row = cursor.fetchone()
    conn.close()
    
    # Convert Row object to dictionary
    return dict(row) if row else None


def get_all_bookings():
    """Get all bookings ordered by creation time"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, first_name, last_name, phone, email, age, gender, doctor_consultation, created_at
        FROM bookings
        ORDER BY created_at DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    # Convert Row objects to dictionaries
    bookings = [dict(row) for row in rows]
    return bookings


def delete_booking_by_id(booking_id):
    """
    Delete booking by ID

    Returns:
        tuple: (success: bool, booking_name: str or None)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # First, check if the booking exists
    cursor.execute('SELECT first_name, last_name FROM bookings WHERE id = ?', (booking_id,))
    booking = cursor.fetchone()

    if not booking:
        conn.close()
        return False, None

    # Delete the booking
    cursor.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
    conn.commit()
    success = cursor.rowcount > 0

    conn.close()
    return success, f"{booking[0]} {booking[1]}" if success else None


def get_booking_count():
    """Get total count of bookings"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM bookings')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0


# Reference options functions removed as reference field is no longer used
