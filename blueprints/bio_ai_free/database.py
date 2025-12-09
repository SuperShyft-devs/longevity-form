# database.py - Database initialization and operations

import sqlite3
from .config import config_manager


def init_db():
    """Initialize the database with required tables"""
    database_name = config_manager.get('database_name', 'bookings.db')
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
            address TEXT,
            pin_code TEXT,
            appointment_date DATE NOT NULL,
            time_slot TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    
    conn.commit()
    conn.close()


def get_db_connection():
    """Get database connection"""
    database_name = config_manager.get('database_name', 'bookings.db')
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

    # 🔹 Get the highest id and add 1
    cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM bookings")
    booking_id = cursor.fetchone()[0]

    
    cursor.execute('''
        INSERT INTO bookings (
            first_name, last_name, phone, email, age, gender, address, pin_code, appointment_date, time_slot
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        booking_data['first_name'], booking_data['last_name'], booking_data['phone'],
        booking_data['email'], booking_data['age'], booking_data['gender'], 
        booking_data.get('address'), booking_data.get('pin_code'),
        booking_data['appointment_date'], booking_data['time_slot']
    ))
    
    conn.commit()
    # booking_id = cursor.lastrowid
    conn.close()
    
    return booking_id


def get_booking_by_id(booking_id):
    """Get booking details by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,))
    booking = cursor.fetchone()
    conn.close()
    
    return booking


def get_all_bookings():
    """Get all bookings ordered by creation time"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, first_name, last_name, phone, email, age, gender, address, pin_code, appointment_date, time_slot,
                created_at
        FROM bookings
        ORDER BY created_at DESC
    ''')
    bookings = cursor.fetchall()
    conn.close()
    
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
