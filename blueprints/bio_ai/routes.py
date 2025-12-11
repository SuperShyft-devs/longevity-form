# routes.py - Bio AI Blueprint Routes (Premium with time slots and reference API)

from flask import render_template, request, jsonify, redirect, url_for, session
from datetime import datetime, timedelta
import requests
import threading

from . import bio_ai_bp
from .config import config_manager, reload_config, ADMIN_PASSWORD
from .whatsapp_integration import send_msg
from .database import (
    save_booking,
    get_booking_by_id,
    get_all_bookings,
    delete_booking_by_id,
    get_db_connection,
    get_reference_options,
    get_reference_options_with_links,
    get_payment_link_for_reference,
    add_reference_option,
    update_reference_option,
    update_reference_payment_link,
    delete_reference_option,
)
from shared_utils import admin_required
from .utils import validate_booking_data
from .booking_service import BookingManager
from .config_validator import ConfigValidator
from .email_service import send_booking_notification_email, test_email_configuration

# Initialize booking manager
booking_manager = BookingManager()


def send_to_api(booking_data, api_type='original'):
    print(f"[BIO-AI] Sending to API ({api_type}): {booking_data}")
    try:
        gender_map = {"male": 1, "female": 2, "Male": 1, "Female": 2}
        payload = {
            "first_name": booking_data["first_name"],
            "last_name": booking_data["last_name"],
            "phone": booking_data["phone"],
            "email": booking_data["email"],
            "age": int(booking_data["age"]),
            "gender": gender_map.get(booking_data["gender"], 1),
        }

        if api_type == 'reference':
            if payload["gender"] == 1:
                METSIGHTS_API_KEY = config_manager.get("reference_metsights_api_key_male", "")
                ENGAGEMENT_ID = config_manager.get("reference_engagement_id_male", "")
            elif payload["gender"] == 2:
                METSIGHTS_API_KEY = config_manager.get("reference_metsights_api_key_female", "")
                ENGAGEMENT_ID = config_manager.get("reference_engagement_id_female", "")
        else:
            if payload["gender"] == 1:
                METSIGHTS_API_KEY = config_manager.get("metsights_api_key_male", "")
                ENGAGEMENT_ID = config_manager.get("engagement_id_male", "")
            elif payload["gender"] == 2:
                METSIGHTS_API_KEY = config_manager.get("metsights_api_key_female", "")
                ENGAGEMENT_ID = config_manager.get("engagement_id_female", "")

        url = f"https://api.metsights.com/engagements/{ENGAGEMENT_ID}/register/"
        headers = {"X-API-KEY": METSIGHTS_API_KEY, "Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.ok:
            print(f"[BIO-AI] API Success ({api_type}): {response.json()}")
            return True
        else:
            print(f"[BIO-AI] API Error ({api_type}): {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[BIO-AI] API Exception ({api_type}): {str(e)}")
        return False


def send_email_async(booking_data):
    try:
        email_success = send_booking_notification_email(booking_data)
        if email_success:
            print("[BIO-AI] Booking notification email sent successfully (async)")
        else:
            print("[BIO-AI] Failed to send booking notification email (async)")
    except Exception as e:
        print(f"[BIO-AI] Exception in async email sending: {str(e)}")


# Main Routes
@bio_ai_bp.route("/")
def index():
    """Main registration form"""
    reference_options = get_reference_options()
    return render_template("bio_ai/index.html", reference_options=reference_options)


@bio_ai_bp.route("/api/config/minimum_days_ahead")
def get_minimum_days_ahead():
    """API endpoint to get minimum days ahead configuration"""
    minimum_days_ahead = int(config_manager.get("minimum_days_ahead", 2))
    return jsonify({"minimum_days_ahead": minimum_days_ahead})


@bio_ai_bp.route("/api/time_slots")
def get_time_slots():
    """API endpoint to get available time slots for a date"""
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"success": False, "error": "Date parameter required"})

    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_time = config_manager.get("slot_start_time", "06:00")
        end_time = config_manager.get("slot_end_time", "13:00")
        duration = int(config_manager.get("slot_duration", 60))
        max_people = int(config_manager.get("max_people_per_slot", 2))

        time_slots = []
        current_time = datetime.strptime(start_time, "%H:%M").time()

        while current_time < datetime.strptime(end_time, "%H:%M").time():
            current_datetime = datetime.combine(selected_date, current_time)
            end_datetime = current_datetime + timedelta(minutes=duration)
            end_time_slot = end_datetime.time()
            display_time = f"{current_time.strftime('%I:%M %p')} - {end_time_slot.strftime('%I:%M %p')}"

            available_spots = max_people
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM bookings WHERE appointment_date = ? AND time_slot = ?",
                    (date_str, current_time.strftime("%H:%M")),
                )
                existing_bookings = cursor.fetchone()[0]
                available_spots = max(0, max_people - existing_bookings)
                conn.close()
            except Exception as e:
                print(f"[BIO-AI] Error checking availability: {e}")

            time_slots.append({
                "time": current_time.strftime("%H:%M"),
                "display_time": display_time,
                "available": available_spots > 0,
                "available_spots": available_spots,
            })

            current_datetime = end_datetime
            current_time = current_datetime.time()

        return jsonify({"success": True, "time_slots": time_slots})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@bio_ai_bp.route("/booking_success/<int:booking_id>")
def booking_success(booking_id):
    """Display booking confirmation"""
    booking = get_booking_by_id(booking_id)
    if not booking:
        return redirect(url_for('bio_ai.index'))
    return render_template("bio_ai/success.html", booking=booking)


@bio_ai_bp.route("/submit_booking", methods=["POST"])
def submit_booking():
    try:
        is_valid, error_message, booking_data = validate_booking_data(request.form)
        if not is_valid:
            return render_template("bio_ai/error.html", message=error_message)

        # Send to API if enabled
        api_enabled = config_manager.get("api_enabled", True)
        if api_enabled:
            if not send_to_api(booking_data):
                return render_template("bio_ai/error.html", message="Failed to send to API")

        # Send to reference API if conditions met
        reference_api_enabled = config_manager.get("reference_api_enabled", False)
        reference_api_trigger_options = config_manager.get("reference_api_trigger_options", [])
        if reference_api_enabled and booking_data.get("reference") in reference_api_trigger_options:
            if not send_to_api(booking_data, api_type='reference'):
                print("[BIO-AI] Warning: Failed to send to reference API")

        # Save booking
        booking_id = save_booking(booking_data)

        # Send email notification asynchronously
        threading.Thread(target=send_email_async, args=(booking_data,)).start()

        # Send WhatsApp messages
        send_msg(
            CAMPAIGN_NAME="longevity-welcome",
            destination_phone=booking_data["phone"],
            templateParams=[booking_data["first_name"] + " " + booking_data["last_name"]],
        )
        send_msg(
            CAMPAIGN_NAME="longevity-registering",
            destination_phone=booking_data["phone"],
            templateParams=[
                booking_data["first_name"],
                booking_data["appointment_date"],
                booking_data["time_slot"],
                "-",
            ],
        )

        # Admin notifications
        phone_numbers = ["+918424029541", "+919602763481", "+917206239498"]
        for phone_number in phone_numbers:
            send_msg(
                CAMPAIGN_NAME="longevity_new_booking_submission_notification",
                destination_phone=phone_number,
                templateParams=[
                    booking_data["first_name"],
                    booking_data["last_name"],
                    booking_data["phone"],
                    booking_data["email"],
                    booking_data["age"],
                    booking_data["gender"],
                    booking_data["address"],
                    booking_data["pin_code"],
                    booking_data["reference"],
                    booking_data["appointment_date"],
                    booking_data["time_slot"],
                ],
            )

        # Get payment link based on reference option
        payment_link = get_payment_link_for_reference(booking_data.get("reference"))
        if payment_link:
            return redirect(payment_link)
        else:
            # Default payment link if no specific link is configured
            default_link = config_manager.get('default_payment_link', 'https://razorpay.me/@fitnastic')
            return redirect(default_link)
    except Exception as e:
        return render_template("bio_ai/error.html", message=f"Unexpected error: {str(e)}")


# Admin Routes
@bio_ai_bp.route("/admin")
@admin_required
def admin():
    """Admin dashboard for bio_ai"""
    bookings = get_all_bookings()
    return render_template("bio_ai/admin.html", bookings=bookings)


@bio_ai_bp.route("/admin/delete_booking/<int:booking_id>", methods=["POST"])
@admin_required
def admin_delete_booking(booking_id):
    """Delete a booking"""
    try:
        delete_booking_by_id(booking_id)
        return jsonify({"success": True, "message": "Booking deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@bio_ai_bp.route("/admin/delete_records")
@admin_required
def admin_delete_records():
    """Delete records page"""
    return render_template("bio_ai/delete_records.html")


@bio_ai_bp.route("/admin/config", methods=["GET", "POST"])
@admin_required
def admin_config():
    """Configuration management"""
    if request.method == "POST":
        try:
            config_data = {
                "metsights_api_key_male": request.form.get("metsights_api_key_male", ""),
                "metsights_api_key_female": request.form.get("metsights_api_key_female", ""),
                "engagement_id_male": request.form.get("engagement_id_male", ""),
                "engagement_id_female": request.form.get("engagement_id_female", ""),
                "reference_metsights_api_key_male": request.form.get("reference_metsights_api_key_male", ""),
                "reference_metsights_api_key_female": request.form.get("reference_metsights_api_key_female", ""),
                "reference_engagement_id_male": request.form.get("reference_engagement_id_male", ""),
                "reference_engagement_id_female": request.form.get("reference_engagement_id_female", ""),
                "slot_start_time": request.form.get("slot_start_time", "06:00"),
                "slot_end_time": request.form.get("slot_end_time", "13:00"),
                "slot_duration": int(request.form.get("slot_duration", 60)),
                "max_people_per_slot": int(request.form.get("max_people_per_slot", 2)),
                "minimum_days_ahead": int(request.form.get("minimum_days_ahead", 2)),
                "default_payment_link": request.form.get("default_payment_link", "https://razorpay.me/@fitnastic"),
                "smtp_server": request.form.get("smtp_server", ""),
                "smtp_port": int(request.form.get("smtp_port", 587)),
                "sender_email": request.form.get("sender_email", ""),
                "sender_password": request.form.get("sender_password", ""),
            }
            
            config_data["api_enabled"] = request.form.get("api_enabled") == "true"
            config_data["reference_api_enabled"] = request.form.get("reference_api_enabled") == "true"
            config_data["email_enabled"] = request.form.get("email_enabled") == "true"
            
            trigger_options_str = request.form.get("reference_api_trigger_options", "")
            config_data["reference_api_trigger_options"] = [opt.strip() for opt in trigger_options_str.split(",") if opt.strip()]

            is_valid, errors = ConfigValidator.validate_config(config_data)
            if not is_valid:
                return render_template("bio_ai/admin_config_new.html", config=config_manager.get_all(), errors=errors)

            config_manager.update_multiple(config_data)
            return render_template("bio_ai/admin_config_new.html", config=config_manager.get_all(), success="Configuration updated successfully!")
        except Exception as e:
            return render_template("bio_ai/admin_config_new.html", config=config_manager.get_all(), errors=[f"Error: {str(e)}"])

    return render_template("bio_ai/admin_config_new.html", config=config_manager.get_all())


@bio_ai_bp.route("/admin/config/reference-management")
@admin_required
def admin_reference_management():
    """Reference options management page"""
    return render_template("bio_ai/admin_reference_management.html")


@bio_ai_bp.route("/admin/config/email-management")
@admin_required
def admin_email_management():
    """Email recipients management page"""
    return render_template("bio_ai/admin_email_management.html")


@bio_ai_bp.route("/admin/config/reset", methods=["POST"])
@admin_required
def reset_config():
    """Reset configuration to defaults"""
    try:
        config_manager.reset_to_defaults()
        return redirect(url_for("bio_ai.admin_config"))
    except Exception as e:
        return render_template("bio_ai/admin_config.html", config=config_manager.get_all(), errors=[f"Error: {str(e)}"])


@bio_ai_bp.route("/admin/config/reference", methods=["GET", "POST"])
@admin_required
def admin_reference_config():
    """Manage reference dropdown options"""
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "add":
            value = request.form.get("value", "").strip()
            payment_link = request.form.get("payment_link", "").strip()
            if value:
                if add_reference_option(value, payment_link if payment_link else None):
                    return jsonify({"success": True, "message": f"Reference option '{value}' added"})
                return jsonify({"success": False, "message": "Failed to add or already exists"})
            return jsonify({"success": False, "message": "Value cannot be empty"})
        
        elif action == "update":
            old_value = request.form.get("old_value", "").strip()
            new_value = request.form.get("new_value", "").strip()
            payment_link = request.form.get("payment_link", "").strip()
            if old_value and new_value:
                if update_reference_option(old_value, new_value, payment_link if payment_link else None):
                    return jsonify({"success": True, "message": f"Updated '{old_value}' to '{new_value}'"})
                return jsonify({"success": False, "message": "Failed to update"})
            return jsonify({"success": False, "message": "Both values required"})
        
        elif action == "update_payment_link":
            value = request.form.get("value", "").strip()
            payment_link = request.form.get("payment_link", "").strip()
            if value:
                if update_reference_payment_link(value, payment_link if payment_link else None):
                    return jsonify({"success": True, "message": f"Payment link updated for '{value}'"})
                return jsonify({"success": False, "message": "Failed to update payment link"})
            return jsonify({"success": False, "message": "Value required"})
        
        elif action == "delete":
            value = request.form.get("value", "").strip()
            if value:
                if delete_reference_option(value):
                    return jsonify({"success": True, "message": f"Reference option '{value}' deleted"})
                return jsonify({"success": False, "message": "Failed to delete"})
            return jsonify({"success": False, "message": "Value cannot be empty"})

    reference_options = get_reference_options_with_links()
    return jsonify({"success": True, "options": reference_options})


@bio_ai_bp.route("/admin/config/test-email", methods=["POST"])
@admin_required
def test_email():
    """Test email configuration"""
    try:
        success = test_email_configuration()
        if success:
            return jsonify({"success": True, "message": "Test email sent successfully!"})
        return jsonify({"success": False, "message": "Failed to send test email"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@bio_ai_bp.route("/admin/config/recipient-emails", methods=["GET", "POST"])
@admin_required
def manage_recipient_emails():
    """Manage recipient email addresses"""
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "add":
            email = request.form.get("email", "").strip()
            if email and "@" in email:
                current_emails = config_manager.get("recipient_emails", [])
                if isinstance(current_emails, str):
                    current_emails = [e.strip() for e in current_emails.split(",") if e.strip()]
                if email not in current_emails:
                    current_emails.append(email)
                    config_manager.set("recipient_emails", current_emails)
                    return jsonify({"success": True, "message": f"Email '{email}' added"})
                return jsonify({"success": False, "message": "Email already exists"})
            return jsonify({"success": False, "message": "Invalid email"})
        
        elif action == "update":
            old_email = request.form.get("old_email", "").strip()
            new_email = request.form.get("new_email", "").strip()
            if old_email and new_email and "@" in new_email:
                current_emails = config_manager.get("recipient_emails", [])
                if isinstance(current_emails, str):
                    current_emails = [e.strip() for e in current_emails.split(",") if e.strip()]
                if old_email in current_emails and new_email not in current_emails:
                    current_emails[current_emails.index(old_email)] = new_email
                    config_manager.set("recipient_emails", current_emails)
                    return jsonify({"success": True, "message": f"Email updated"})
                return jsonify({"success": False, "message": "Update failed"})
            return jsonify({"success": False, "message": "Invalid emails"})
        
        elif action == "delete":
            email = request.form.get("email", "").strip()
            if email:
                current_emails = config_manager.get("recipient_emails", [])
                if isinstance(current_emails, str):
                    current_emails = [e.strip() for e in current_emails.split(",") if e.strip()]
                if email in current_emails and len(current_emails) > 1:
                    current_emails.remove(email)
                    config_manager.set("recipient_emails", current_emails)
                    return jsonify({"success": True, "message": f"Email '{email}' deleted"})
                return jsonify({"success": False, "message": "Cannot delete last email or not found"})
            return jsonify({"success": False, "message": "Email required"})
    
    recipient_emails = config_manager.get("recipient_emails", [])
    if isinstance(recipient_emails, str):
        recipient_emails = [e.strip() for e in recipient_emails.split(",") if e.strip()]
    return jsonify({"success": True, "emails": recipient_emails})
