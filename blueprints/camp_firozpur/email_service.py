"""
Email service for sending booking notifications for Firozpur camp
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from .config import config_manager


def send_booking_notification_email(booking_data):
    """
    Send booking notification email to admin
    
    Args:
        booking_data (dict): Booking information
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Check if email is enabled
        email_enabled = config_manager.get('email_enabled', False)
        if not email_enabled:
            print("Email notifications are disabled")
            return True  # Return True to not block the booking process
        
        # Get email configuration
        smtp_server = config_manager.get('smtp_server', 'smtp.gmail.com')
        smtp_port = config_manager.get('smtp_port', 587)
        sender_email = config_manager.get('sender_email', 'pratheek.codimai@gmail.com')
        sender_password = config_manager.get('sender_password', '')
        recipient_emails = config_manager.get('recipient_emails', ['pratheekbedrejun20@gmail.com'])
        
        # Convert single email string to list for backwards compatibility
        if isinstance(recipient_emails, str):
            recipient_emails = [email.strip() for email in recipient_emails.split(',') if email.strip()]
        
        if not sender_password:
            print("Email password not configured")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipient_emails)  # Multiple recipients
        msg['Subject'] = "New Health Camp Registration (Firozpur) - Fitnastic"
        
        # Create email body
        body = create_booking_email_body(booking_data)
        msg.attach(MIMEText(body, 'html'))
        
        # Send email to multiple recipients
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable encryption
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_emails, text)  # Send to multiple emails
        server.quit()
        
        print(f"Booking notification email sent successfully to {len(recipient_emails)} recipients: {', '.join(recipient_emails)}")
        return True
        
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False


def create_booking_email_body(booking_data):
    """
    Create HTML email body for booking notification
    
    Args:
        booking_data (dict): Booking information
        
    Returns:
        str: HTML email body
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Format appointment time for display
    try:
        appointment_time = datetime.strptime(booking_data.get('time_slot', ''), '%H:%M')
        formatted_time = appointment_time.strftime('%I:%M %p')
    except:
        formatted_time = booking_data.get('time_slot', 'N/A')
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
            .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
            .field {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #555; }}
            .value {{ color: #333; }}
            .footer {{ background-color: #333; color: white; padding: 15px; text-align: center; border-radius: 0 0 5px 5px; }}
            .highlight {{ background-color: #e8f5e8; padding: 10px; border-radius: 5px; margin: 15px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🎉 New Health Camp Registration (Firozpur)</h2>
                <p>Fitnastic Health Camp - Firozpur</p>
            </div>
            
            <div class="content">
                <div class="highlight">
                    <strong>📅 New registration received at:</strong> {current_time}
                </div>
                
                <h3>👤 Personal Information</h3>
                <div class="field">
                    <span class="label">Name:</span> 
                    <span class="value">{booking_data.get('first_name', '')} {booking_data.get('last_name', '')}</span>
                </div>
                <div class="field">
                    <span class="label">Email:</span> 
                    <span class="value">{booking_data.get('email', 'N/A')}</span>
                </div>
                <div class="field">
                    <span class="label">Phone:</span> 
                    <span class="value">{booking_data.get('phone', 'N/A')}</span>
                </div>
                <div class="field">
                    <span class="label">Age:</span> 
                    <span class="value">{booking_data.get('age', 'N/A')}</span>
                </div>
                <div class="field">
                    <span class="label">Gender:</span> 
                    <span class="value">{'Male' if booking_data.get('gender') == 'M' else 'Female' if booking_data.get('gender') == 'F' else booking_data.get('gender', 'N/A')}</span>
                </div>
                <div class="field">
                    <span class="label">Address:</span> 
                    <span class="value">{booking_data.get('address', 'Not provided')}</span>
                </div>
                <div class="field">
                    <span class="label">Pincode:</span> 
                    <span class="value">{booking_data.get('pin_code') or 'Not provided'}</span>
                </div>
                <div class="field">
                    <span class="label">Reference:</span> 
                    <span class="value">{booking_data.get('reference', 'Not provided')}</span>
                </div>
                
                <h3>📅 Appointment Details</h3>
                <div class="field">
                    <span class="label">Date:</span> 
                    <span class="value">{booking_data.get('appointment_date', 'N/A')}</span>
                </div>
                <div class="field">
                    <span class="label">Time:</span> 
                    <span class="value">{formatted_time}</span>
                </div>
                
                <div class="highlight">
                    <strong>💡 Next Steps:</strong>
                    <ul>
                        <li>Review the registration details</li>
                        <li>Confirm the appointment if needed</li>
                        <li>Access the admin panel for more details</li>
                    </ul>
                </div>
            </div>
            
            <div class="footer">
                <p>This is an automated notification from Fitnastic Health Camp Registration System (Firozpur)</p>
                <p>Please do not reply to this email</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_body


def test_email_configuration():
    """
    Test email configuration by sending a test email
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Test data
        test_booking = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'phone': '1234567890',
            'age': '25',
            'gender': 'M',
            'address': 'Test Address',
            'pin_code': '400066',
            'reference': 'Test Reference',
            'appointment_date': '2024-12-01',
            'time_slot': '09:00'
        }
        
        success = send_booking_notification_email(test_booking)
        
        if success:
            return True, "Test email sent successfully!"
        else:
            return False, "Failed to send test email. Check configuration and logs."
            
    except Exception as e:
        return False, f"Error testing email: {str(e)}"
