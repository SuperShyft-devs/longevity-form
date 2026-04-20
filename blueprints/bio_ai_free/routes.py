# routes.py - Bio AI Free Blueprint Routes (Free with time slots, multiple bookings)

from flask import render_template, request, jsonify, redirect, url_for, session
from datetime import datetime, timedelta
import requests
import threading

from metsights_profiles import profiles_api_configured, sync_booking_to_metsights

from . import bio_ai_free_bp
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


def _send_metsights_engagement_register(booking_data):
    """Legacy flow: POST /engagements/{id}/register/ using per-gender keys from admin config."""
    print(f"[BIO-AI-FREE] Sending to engagement API: {booking_data}")
    try:
        gender_map = {
            "M": 1,
            "F": 2,
            "male": 1,
            "female": 2,
            "Male": 1,
            "Female": 2,
        }
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
            print(f"[BIO-AI-FREE] Engagement API success: {response.json()}")
            return True
        print(f"[BIO-AI-FREE] Engagement API error: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print(f"[BIO-AI-FREE] Engagement API exception: {str(e)}")
        return False


def send_to_api(booking_data):
    """
    B2B/HR form: MetSights Profiles API — MetSights Pro record — when METSIGHTS_API_KEY is set.
    Otherwise falls back to engagement register.
    """
    if profiles_api_configured():
        ok = sync_booking_to_metsights(booking_data, assessment_type="2")
        if ok:
            return True
        print("[BIO-AI-FREE] Profiles API failed; falling back to engagement register if configured.")

    return _send_metsights_engagement_register(booking_data)


def send_email_async(booking_data):
    try:
        email_success = send_booking_notification_email(booking_data)
        if email_success:
            print("[BIO-AI-FREE] Booking notification email sent successfully (async)")
        else:
            print("[BIO-AI-FREE] Failed to send booking notification email (async)")
    except Exception as e:
        print(f"[BIO-AI-FREE] Exception in async email sending: {str(e)}")


def parse_members_from_form(form_data):
    """Parse members data from form"""
    members = {}
    for key, value in form_data.items():
        if key.startswith('members[') and key.endswith(']'):
            parts = key[8:-1].split('][')
            if len(parts) == 2:
                member_id = int(parts[0])
                field = parts[1]
                if member_id not in members:
                    members[member_id] = {}
                members[member_id][field] = value
    return [members[mid] for mid in sorted(members.keys())]


# Main Routes
@bio_ai_free_bp.route("/")
def index():
    """Main registration form"""
    return render_template("bio_ai_free/index.html")


@bio_ai_free_bp.route("/api/config/minimum_days_ahead")
def get_minimum_days_ahead():
    """API endpoint to get minimum days ahead configuration"""
    minimum_days_ahead = int(config_manager.get("minimum_days_ahead", 2))
    return jsonify({"minimum_days_ahead": minimum_days_ahead})


@bio_ai_free_bp.route("/api/time_slots")
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
                print(f"[BIO-AI-FREE] Error checking availability: {e}")

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


@bio_ai_free_bp.route("/booking_success/<booking_ids>")
def booking_success(booking_ids):
    """Display booking confirmation"""
    booking_id_list = booking_ids.split(',')
    bookings = []
    for bid in booking_id_list:
        try:
            booking = get_booking_by_id(int(bid))
            if booking:
                bookings.append(booking)
        except ValueError:
            continue
    if not bookings:
        return redirect(url_for('bio_ai_free.index'))
    return render_template("bio_ai_free/success.html", bookings=bookings)


@bio_ai_free_bp.route("/submit_booking", methods=["POST"])
def submit_booking():
    booking_ids = []
    try:
        members = parse_members_from_form(request.form)
        if not members:
            print("[BIO-AI-FREE] No member data in form (redirecting, no error page)")
            return redirect(url_for("bio_ai_free.index"))

        api_enabled = config_manager.get("api_enabled", True)

        for member_data in members:
            try:
                is_valid, error_message, booking_data = validate_booking_data(member_data)
                if not is_valid:
                    print(f"[BIO-AI-FREE] Validation failed (redirecting, no error page): {error_message}")
                    if booking_ids:
                        break
                    return redirect(url_for("bio_ai_free.index"))

                booking_id = save_booking(booking_data)
                booking_ids.append(booking_id)

                try:
                    if api_enabled or profiles_api_configured():
                        try:
                            if send_to_api(booking_data):
                                print(f"[BIO-AI-FREE] Booking #{booking_id}: MetSights / engagement sync OK")
                            else:
                                print(
                                    f"[BIO-AI-FREE] Booking #{booking_id}: MetSights / engagement sync failed — "
                                    "booking was saved; check API keys or MetSights billing."
                                )
                        except Exception as api_error:
                            print(f"[BIO-AI-FREE] Booking #{booking_id}: MetSights sync exception (booking saved): {api_error}")

                    threading.Thread(target=send_email_async, args=(booking_data,)).start()

                    send_msg(
                        CAMPAIGN_NAME="longevity-welcome",
                        destination_phone=booking_data["phone"],
                        templateParams=[booking_data["first_name"] + " " + booking_data["last_name"]],
                    )
                    send_msg(
                        CAMPAIGN_NAME="user_registration_notification",
                        destination_phone=booking_data["phone"],
                        templateParams=[
                            booking_data["first_name"] + " " + booking_data["last_name"],
                            booking_data["appointment_date"],
                            booking_data["time_slot"],
                            "-"
                        ],
                    )

                    phone_numbers = ["8424029541", "9602763481", "7206239498", "9372799064", "7770081606"]
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
                                "HR",
                                booking_data["appointment_date"],
                                booking_data["time_slot"],
                            ],
                        )
                except Exception as member_post_err:
                    print(f"[BIO-AI-FREE] Post-save steps failed for booking #{booking_id} (row saved): {member_post_err}")
            except Exception as member_err:
                print(f"[BIO-AI-FREE] Member row failed (may be partial): {member_err}")
                continue

        if booking_ids:
            booking_ids_str = ",".join(map(str, booking_ids))
            return redirect(url_for("bio_ai_free.booking_success", booking_ids=booking_ids_str))
        return redirect(url_for("bio_ai_free.index"))
    except Exception as e:
        print(f"[BIO-AI-FREE] submit_booking: {e}")
        if booking_ids:
            booking_ids_str = ",".join(map(str, booking_ids))
            return redirect(url_for("bio_ai_free.booking_success", booking_ids=booking_ids_str))
        return redirect(url_for("bio_ai_free.index"))


# Admin Routes
@bio_ai_free_bp.route("/admin")
@admin_required
def admin():
    """Admin dashboard for bio_ai_free"""
    bookings = get_all_bookings()
    return render_template("bio_ai_free/admin.html", bookings=bookings)


@bio_ai_free_bp.route("/admin/delete_booking/<int:booking_id>", methods=["POST"])
@admin_required
def admin_delete_booking(booking_id):
    """Delete a booking"""
    try:
        delete_booking_by_id(booking_id)
        return jsonify({"success": True, "message": "Booking deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@bio_ai_free_bp.route("/admin/delete_records")
@admin_required
def admin_delete_records():
    """Delete records page"""
    return render_template("bio_ai_free/delete_records.html")


@bio_ai_free_bp.route("/admin/config", methods=["GET", "POST"])
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
                "slot_start_time": request.form.get("slot_start_time", "06:00"),
                "slot_end_time": request.form.get("slot_end_time", "13:00"),
                "slot_duration": int(request.form.get("slot_duration", 60)),
                "max_people_per_slot": int(request.form.get("max_people_per_slot", 2)),
                "minimum_days_ahead": int(request.form.get("minimum_days_ahead", 2)),
                "smtp_server": request.form.get("smtp_server", ""),
                "smtp_port": int(request.form.get("smtp_port", 587)),
                "sender_email": request.form.get("sender_email", ""),
                "sender_password": request.form.get("sender_password", ""),
            }
            
            config_data["api_enabled"] = request.form.get("api_enabled") == "true"
            config_data["email_enabled"] = request.form.get("email_enabled") == "true"

            is_valid, errors = ConfigValidator.validate_config(config_data)
            if not is_valid:
                return render_template("bio_ai_free/admin_config_new.html", config=config_manager.get_all(), errors=errors)

            config_manager.update_multiple(config_data)
            return render_template("bio_ai_free/admin_config_new.html", config=config_manager.get_all(), success="Configuration updated!")
        except Exception as e:
            return render_template("bio_ai_free/admin_config_new.html", config=config_manager.get_all(), errors=[f"Error: {str(e)}"])

    return render_template("bio_ai_free/admin_config_new.html", config=config_manager.get_all())


@bio_ai_free_bp.route("/admin/config/email-management")
@admin_required
def admin_email_management():
    """Email recipients management page"""
    return render_template("bio_ai_free/admin_email_management.html")


@bio_ai_free_bp.route("/admin/config/reset", methods=["POST"])
@admin_required
def reset_config():
    """Reset configuration to defaults"""
    try:
        config_manager.reset_to_defaults()
        return redirect(url_for("bio_ai_free.admin_config"))
    except Exception as e:
        return render_template("bio_ai_free/admin_config.html", config=config_manager.get_all(), errors=[f"Error: {str(e)}"])


@bio_ai_free_bp.route("/admin/config/test-email", methods=["POST"])
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


@bio_ai_free_bp.route("/admin/config/recipient-emails", methods=["GET", "POST"])
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
