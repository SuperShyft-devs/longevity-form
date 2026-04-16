# shared_config.py - Shared configuration across all forms

import os

# Flask Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '4*U8.@N|b$c3HCeq')  # Change this in production

# Form identifiers
FORMS = {
    'bio_ai': {
        'name': 'Longevity Bio AI',
        'description': 'Premium longevity assessment with time slots',
        'database': 'bookings_bio_ai.db',
        'config_file': 'config_bio_ai.json'
    },
    'bio_ai_free': {
        'name': 'Longevity Bio AI Free',
        'description': 'Free longevity assessment with time slots',
        'database': 'bookings_bio_ai_free.db',
        'config_file': 'config_bio_ai_free.json'
    },
    'camp': {
        'name': 'Longevity Camp',
        'description': 'Longevity camp registration',
        'database': 'bookings_camp.db',
        'config_file': 'config_camp.json'
    },
    'camp_delhi': {
        'name': 'Longevity Camp - Delhi',
        'description': 'Longevity camp registration for Delhi',
        'database': 'bookings_camp_delhi.db',
        'config_file': 'config_camp_delhi.json'
    },
    'camp_firozpur': {
        'name': 'Longevity Camp - Firozpur',
        'description': 'Longevity camp registration for Firozpur',
        'database': 'bookings_camp_firozpur.db',
        'config_file': 'config_camp_firozpur.json'
    }
}
