# whatsapp_integration.py - WhatsApp integration for Delhi camp

import requests
from .config import config_manager


def send_msg(phone_number: str, message: str) -> bool:
    """
    Send WhatsApp message to a phone number
    
    Args:
        phone_number (str): Phone number to send message to
        message (str): Message to send
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    try:
        # Get WhatsApp API configuration
        api_url = config_manager.get('whatsapp_api_url', '')
        api_key = config_manager.get('whatsapp_api_key', '')
        
        if not api_url or not api_key:
            print("WhatsApp API not configured")
            return False
        
        payload = {
            'phone': phone_number,
            'message': message
        }
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        
        if response.ok:
            print(f"WhatsApp message sent successfully to {phone_number}")
            return True
        else:
            print(f"Failed to send WhatsApp message: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")
        return False
