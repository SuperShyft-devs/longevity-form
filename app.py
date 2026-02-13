# app.py - Unified Flask Application for Longevity Forms
# Consolidates three separate booking forms into one application with blueprints

from flask import Flask, render_template, session, redirect, url_for, request, jsonify
from datetime import datetime
import os

# Import shared utilities
from shared_config import SECRET_KEY, ADMIN_PASSWORD
from shared_utils import admin_required

# Initialize Flask app
app = Flask(__name__)
app.secret_key = SECRET_KEY

# Register blueprints for each form
from blueprints.bio_ai import bio_ai_bp
from blueprints.bio_ai_free import bio_ai_free_bp
from blueprints.camp import camp_bp
from blueprints.camp_delhi import camp_delhi_bp
from blueprints.camp_firozpur import camp_firozpur_bp

# Register blueprints with URL prefixes
app.register_blueprint(bio_ai_bp, url_prefix='/')
app.register_blueprint(bio_ai_free_bp, url_prefix='/longevity-bio-ai-93727-free')
app.register_blueprint(camp_bp, url_prefix='/camp')
app.register_blueprint(camp_delhi_bp, url_prefix='/camp/delhi')
app.register_blueprint(camp_firozpur_bp, url_prefix='/camp/firozpur')


# Forms landing page (moved from root)
@app.route('/forms')
def landing():
    """Main landing page with links to all forms"""
    # Get booking counts for stats
    from blueprints.bio_ai.database import get_booking_count as get_bio_ai_count
    from blueprints.bio_ai_free.database import get_booking_count as get_bio_ai_free_count
    from blueprints.camp_delhi.database import get_booking_count as get_camp_delhi_count
    from blueprints.camp_firozpur.database import get_booking_count as get_camp_firozpur_count
    
    try:
        bio_ai_count = get_bio_ai_count()
        bio_ai_free_count = get_bio_ai_free_count()
        camp_delhi_count = get_camp_delhi_count()
        camp_firozpur_count = get_camp_firozpur_count()
        total_count = bio_ai_count + bio_ai_free_count + camp_delhi_count + camp_firozpur_count
    except:
        bio_ai_count = bio_ai_free_count = camp_delhi_count = camp_firozpur_count = total_count = 0
    
    stats = {
        'total': total_count,
        'bio_ai': bio_ai_count,
        'bio_ai_free': bio_ai_free_count,
        'camp_delhi': camp_delhi_count,
        'camp_firozpur': camp_firozpur_count
    }
    
    return render_template('landing.html', stats=stats)


# Unified Admin Routes
@app.route('/forms/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Unified admin login for all forms"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid password')
    
    return render_template('admin_login.html')


@app.route('/forms/admin/logout')
def admin_logout():
    """Logout from admin panel"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('landing'))


@app.route('/forms/admin')
@admin_required
def admin_dashboard():
    """Unified admin dashboard showing all bookings from all forms"""
    from blueprints.bio_ai.database import get_all_bookings as get_bio_ai_bookings
    from blueprints.bio_ai_free.database import get_all_bookings as get_bio_ai_free_bookings
    from blueprints.camp_delhi.database import get_all_bookings as get_camp_delhi_bookings
    from blueprints.camp_firozpur.database import get_all_bookings as get_camp_firozpur_bookings
    
    # Get filter parameter
    form_filter = request.args.get('form', 'all')
    
    # Fetch bookings from all forms
    bio_ai_bookings = []
    bio_ai_free_bookings = []
    camp_delhi_bookings = []
    camp_firozpur_bookings = []
    
    try:
        if form_filter in ['all', 'bio_ai']:
            bio_ai_bookings = [(b, 'bio_ai') for b in get_bio_ai_bookings()]
        if form_filter in ['all', 'bio_ai_free']:
            bio_ai_free_bookings = [(b, 'bio_ai_free') for b in get_bio_ai_free_bookings()]
        if form_filter in ['all', 'camp_delhi']:
            camp_delhi_bookings = [(b, 'camp_delhi') for b in get_camp_delhi_bookings()]
        if form_filter in ['all', 'camp_firozpur']:
            camp_firozpur_bookings = [(b, 'camp_firozpur') for b in get_camp_firozpur_bookings()]
    except Exception as e:
        print(f"Error fetching bookings: {e}")
    
    # Combine all bookings
    all_bookings = bio_ai_bookings + bio_ai_free_bookings + camp_delhi_bookings + camp_firozpur_bookings
    
    # Sort by date (most recent first)
    all_bookings.sort(key=lambda x: x[0].get('created_at', ''), reverse=True)
    
    return render_template('admin_dashboard.html', 
                         bookings=all_bookings, 
                         form_filter=form_filter)


@app.route('/forms/admin/config/<form_name>')
@admin_required
def admin_config(form_name):
    """Configuration page for specific form"""
    if form_name == 'bio_ai':
        return redirect(url_for('bio_ai.admin_config'))
    elif form_name == 'bio_ai_free':
        return redirect(url_for('bio_ai_free.admin_config'))
    elif form_name == 'camp_delhi':
        return redirect(url_for('camp_delhi.admin_config'))
    elif form_name == 'camp_firozpur':
        return redirect(url_for('camp_firozpur.admin_config'))
    else:
        return redirect(url_for('admin_dashboard'))


@app.route('/forms/admin/delete_booking/<form_name>/<int:booking_id>', methods=['POST'])
@admin_required
def admin_delete_booking(form_name, booking_id):
    """Delete booking from specific form"""
    try:
        if form_name == 'bio_ai':
            from blueprints.bio_ai.database import delete_booking_by_id
            delete_booking_by_id(booking_id)
        elif form_name == 'bio_ai_free':
            from blueprints.bio_ai_free.database import delete_booking_by_id
            delete_booking_by_id(booking_id)
        elif form_name == 'camp_delhi':
            from blueprints.camp_delhi.database import delete_booking_by_id
            delete_booking_by_id(booking_id)
        elif form_name == 'camp_firozpur':
            from blueprints.camp_firozpur.database import delete_booking_by_id
            delete_booking_by_id(booking_id)
        
        return jsonify({'success': True, 'message': 'Booking deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Internal server error'), 500


# Initialize all databases
def init_all_databases():
    """Initialize all form databases"""
    from blueprints.bio_ai.database import init_db as init_bio_ai_db
    from blueprints.bio_ai_free.database import init_db as init_bio_ai_free_db
    from blueprints.camp.database import init_db as init_camp_db
    from blueprints.camp_delhi.database import init_db as init_camp_delhi_db
    from blueprints.camp_firozpur.database import init_db as init_camp_firozpur_db
    
    init_bio_ai_db()
    init_bio_ai_free_db()
    init_camp_db()
    init_camp_delhi_db()
    init_camp_firozpur_db()
    print("All databases initialized successfully")

init_all_databases()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
