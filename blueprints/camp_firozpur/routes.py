# routes.py - Camp Firozpur Blueprint Routes (Simpler, no time slots)

from flask import render_template, request, jsonify, redirect, url_for, session
from datetime import datetime, timedelta
import requests
import threading

from . import camp_firozpur_bp
from .config import config_manager, reload_config, ADMIN_PASSWORD
from .whatsapp_integration import send_msg
from .database import (
    save_booking,
    get_booking_by_id,
    get_all_bookings,
    delete_booking_by_id,
    get_db_connection,
)
from shared_utils import admin_required
from .utils import validate_booking_data
from .booking_service import BookingManager
from .config_validator import ConfigValidator
from .email_service import send_booking_notification_email, test_email_configuration

# Initialize booking manager
booking_manager = BookingManager()


def send_to_api(booking_data):
    print(f"[CAMP_FIROZPUR] Sending to API: {booking_data}")
    try:
        gender_map = {"male": 1, "female": 2, "Male": 1, "Female": 2, "M": 1, "F": 2, "m": 1, "f": 2}
        payload = {
            "first_name": booking_data["first_name"],
            "last_name": booking_data["last_name"],
            "phone": booking_data["phone"],
            "email": booking_data["email"],
            "age": int(booking_data["age"]),
            "gender": gender_map.get(booking_data["gender"], 1),
        }

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
            print(f"[CAMP_FIROZPUR] API Success: {response.json()}")
            return True
        else:
            print(f"[CAMP_FIROZPUR] API Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[CAMP_FIROZPUR] API Exception: {str(e)}")
        return False


def send_email_async(booking_data):
    try:
        email_success = send_booking_notification_email(booking_data)
        if email_success:
            print("[CAMP_FIROZPUR] Booking notification email sent successfully (async)")
        else:
            print("[CAMP_FIROZPUR] Failed to send booking notification email (async)")
    except Exception as e:
        print(f"[CAMP_FIROZPUR] Exception in async email sending: {str(e)}")


# Main Routes
@camp_firozpur_bp.route("/")
def index():
    """Main registration form for Firozpur camp"""
    return render_template("camp_firozpur/index.html")


@camp_firozpur_bp.route("/api/config/minimum_days_ahead")
def get_minimum_days_ahead():
    """API endpoint to get minimum days ahead configuration"""
    minimum_days_ahead = int(config_manager.get("minimum_days_ahead", 2))
    return jsonify({"minimum_days_ahead": minimum_days_ahead})


@camp_firozpur_bp.route("/booking_success/<int:booking_id>")
def booking_success(booking_id):
    """Display booking confirmation"""
    booking = get_booking_by_id(booking_id)
    if not booking:
        return redirect(url_for('camp_firozpur.index'))
    return render_template("camp_firozpur/success.html", booking=booking)


@camp_firozpur_bp.route("/submit_booking", methods=["POST"])
def submit_booking():
    try:
        is_valid, error_message, booking_data = validate_booking_data(request.form)
        if not is_valid:
            return render_template("camp_firozpur/error.html", message=error_message)

        # Save booking first
        booking_id = save_booking(booking_data)

        # Send to API if enabled (non-blocking)
        api_enabled = config_manager.get("api_enabled", True)
        if api_enabled:
            try:
                if send_to_api(booking_data):
                    print(f"[CAMP_FIROZPUR] Booking #{booking_id}: API integration successful")
                else:
                    print(f"[CAMP_FIROZPUR] Booking #{booking_id}: API integration failed (booking still saved)")
            except Exception as api_error:
                print(f"[CAMP_FIROZPUR] Booking #{booking_id}: API integration error - {str(api_error)}")

        # Send email notification asynchronously
        threading.Thread(target=send_email_async, args=(booking_data,)).start()

        return redirect(url_for("camp_firozpur.booking_success", booking_id=booking_id))
    except Exception as e:
        return render_template("camp_firozpur/error.html", message=f"Unexpected error: {str(e)}")


# Admin Routes
@camp_firozpur_bp.route("/admin")
@admin_required
def admin():
    """Admin dashboard for Firozpur camp"""
    bookings = get_all_bookings()
    return render_template("camp_firozpur/admin.html", bookings=bookings)


@camp_firozpur_bp.route("/admin/delete_booking/<int:booking_id>", methods=["POST"])
@admin_required
def delete_booking(booking_id):
    """Delete a booking"""
    try:
        success, booking_name = delete_booking_by_id(booking_id)
        if success:
            print(f"[CAMP_FIROZPUR] Booking #{booking_id} for {booking_name} deleted")
        else:
            print(f"[CAMP_FIROZPUR] Booking not found")
        return redirect(url_for("camp_firozpur.admin"))
    except Exception as e:
        print(f"[CAMP_FIROZPUR] Error deleting booking: {str(e)}")
        return redirect(url_for("camp_firozpur.admin"))


@camp_firozpur_bp.route("/admin/delete_records")
@admin_required
def delete_records():
    """Delete records page"""
    bookings = get_all_bookings()
    return render_template("camp_firozpur/delete_records.html", bookings=bookings)


@camp_firozpur_bp.route("/admin/config", methods=["GET", "POST"])
@admin_required
def admin_config():
    """Configuration management"""
    if request.method == "POST":
        try:
            config_data = dict(request.form)
            config_data["api_enabled"] = request.form.get("api_enabled") == "true"
            config_data["email_enabled"] = request.form.get("email_enabled") == "true"

            is_valid, errors = ConfigValidator.validate_config(config_data)
            if not is_valid:
                return render_template("camp_firozpur/admin_config_new.html", config=config_manager.get_all(), errors=errors)

            config_manager.update_multiple(config_data)
            return render_template("camp_firozpur/admin_config_new.html", config=config_manager.get_all(), success="Configuration updated!")
        except Exception as e:
            return render_template("camp_firozpur/admin_config_new.html", config=config_manager.get_all(), errors=[f"Error: {str(e)}"])

    return render_template("camp_firozpur/admin_config_new.html", config=config_manager.get_all())


@camp_firozpur_bp.route("/admin/config/email-management")
@admin_required
def admin_email_management():
    """Email recipients management page"""
    return render_template("camp_firozpur/admin_email_management.html")


@camp_firozpur_bp.route("/admin/config/reset", methods=["POST"])
@admin_required
def reset_config():
    """Reset configuration to defaults"""
    try:
        config_manager.reset_to_defaults()
        return redirect(url_for("camp_firozpur.admin_config"))
    except Exception as e:
        return render_template("camp_firozpur/admin_config.html", config=config_manager.get_all(), errors=[f"Error: {str(e)}"])


@camp_firozpur_bp.route("/admin/config/test-email", methods=["POST"])
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


@camp_firozpur_bp.route("/admin/config/recipient-emails", methods=["GET", "POST"])
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
                    return jsonify({"success": True, "message": "Email updated"})
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
