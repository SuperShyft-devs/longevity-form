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
            reference TEXT,
            appointment_date DATE NOT NULL,
            time_slot TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create reference_options table for dropdown values
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reference_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            value TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default reference options if table is empty
    cursor.execute('SELECT COUNT(*) FROM reference_options')
    if cursor.fetchone()[0] == 0:
        default_options = ['A', 'B', 'C', 'D']
        for option in default_options:
            cursor.execute('INSERT INTO reference_options (value) VALUES (?)', (option,))
    
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
            first_name, last_name, phone, email, age, gender, address, pin_code, reference, appointment_date, time_slot
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        booking_data['first_name'], booking_data['last_name'], booking_data['phone'],
        booking_data['email'], booking_data['age'], booking_data['gender'], 
        booking_data.get('address'), booking_data.get('pin_code'),
        booking_data.get('reference'), booking_data['appointment_date'], booking_data['time_slot']
    ))
    
    conn.commit()
    # booking_id = cursor.lastrowid
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
        SELECT id, first_name, last_name, phone, email, age, gender, address, pin_code, reference, appointment_date, time_slot,
                created_at
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


def get_reference_options():
    """Get all reference options for dropdown"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT value FROM reference_options ORDER BY value')
    options = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return options


def add_reference_option(value):
    """Add a new reference option"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT INTO reference_options (value) VALUES (?)', (value,))
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error adding reference option: {e}")
        success = False
    finally:
        conn.close()
    
    return success


def update_reference_option(old_value, new_value):
    """Update an existing reference option"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE reference_options SET value = ? WHERE value = ?', (new_value, old_value))
        conn.commit()
        success = cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating reference option: {e}")
        success = False
    finally:
        conn.close()
    
    return success


def delete_reference_option(value):
    """Delete a reference option"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM reference_options WHERE value = ?', (value,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    
    return success


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
