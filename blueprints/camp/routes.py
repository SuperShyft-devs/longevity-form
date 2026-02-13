# routes.py - Camp Blueprint Routes (Admin only - no public form)
# The public form has been removed. Use /longevity-camp/delhi/ or /longevity-camp/firozpur/ instead.

from flask import render_template, request, jsonify, redirect, url_for, session
from datetime import datetime, timedelta
import requests
import threading

from . import camp_bp
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


# Redirect root camp URL to forms page
@camp_bp.route("/")
def index():
    """Redirect to forms page - camp form has been removed"""
    return redirect("/forms")


# Admin Routes
@camp_bp.route("/admin")
@admin_required
def admin():
    """Admin dashboard for camp"""
    bookings = get_all_bookings()
    enhanced_bookings = []
    for booking in bookings:
        booking_dict = {
            "id": booking[0],
            "first_name": booking[1],
            "last_name": booking[2],
            "phone": booking[3],
            "email": booking[4],
            "age": booking[5],
            "gender": booking[6],
            "doctor_consultation": booking[7],
            "created_at": booking[8] if len(booking) > 8 else None,
        }
        enhanced_bookings.append(booking_dict)
    return render_template("camp/admin.html", bookings=enhanced_bookings)


@camp_bp.route("/admin/delete_booking/<int:booking_id>", methods=["POST"])
@admin_required
def delete_booking(booking_id):
    """Delete a booking"""
    try:
        success, booking_name = delete_booking_by_id(booking_id)
        if success:
            print(f"[CAMP] Booking #{booking_id} for {booking_name} deleted")
        else:
            print(f"[CAMP] Booking not found")
        return redirect(url_for("camp.admin"))
    except Exception as e:
        print(f"[CAMP] Error deleting booking: {str(e)}")
        return redirect(url_for("camp.admin"))


@camp_bp.route("/admin/delete_records")
@admin_required
def delete_records():
    """Delete records page"""
    bookings = get_all_bookings()
    enhanced_bookings = []
    for booking in bookings:
        booking_dict = {
            "id": booking[0],
            "first_name": booking[1],
            "last_name": booking[2],
            "phone": booking[3],
            "email": booking[4],
            "age": booking[5],
            "gender": booking[6],
            "doctor_consultation": booking[7],
            "created_at": booking[8] if len(booking) > 8 else None,
        }
        enhanced_bookings.append(booking_dict)
    return render_template("camp/delete_records.html", bookings=enhanced_bookings)


@camp_bp.route("/admin/config", methods=["GET", "POST"])
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
                return render_template("camp/admin_config_new.html", config=config_manager.get_all(), errors=errors)

            config_manager.update_multiple(config_data)
            return render_template("camp/admin_config_new.html", config=config_manager.get_all(), success="Configuration updated!")
        except Exception as e:
            return render_template("camp/admin_config_new.html", config=config_manager.get_all(), errors=[f"Error: {str(e)}"])

    return render_template("camp/admin_config_new.html", config=config_manager.get_all())


@camp_bp.route("/admin/config/email-management")
@admin_required
def admin_email_management():
    """Email recipients management page"""
    return render_template("camp/admin_email_management.html")


@camp_bp.route("/admin/config/reset", methods=["POST"])
@admin_required
def reset_config():
    """Reset configuration to defaults"""
    try:
        config_manager.reset_to_defaults()
        return redirect(url_for("camp.admin_config"))
    except Exception as e:
        return render_template("camp/admin_config.html", config=config_manager.get_all(), errors=[f"Error: {str(e)}"])


@camp_bp.route("/admin/config/test-email", methods=["POST"])
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


@camp_bp.route("/admin/config/recipient-emails", methods=["GET", "POST"])
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
