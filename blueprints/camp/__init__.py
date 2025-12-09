# camp blueprint - Longevity camp registration (simpler, no time slots)

from flask import Blueprint

camp_bp = Blueprint('camp', __name__, template_folder='../../templates/camp')

from . import routes
