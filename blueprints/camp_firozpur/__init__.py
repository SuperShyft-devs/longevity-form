# camp_firozpur blueprint - Longevity camp registration for Firozpur (copy of camp)

from flask import Blueprint

camp_firozpur_bp = Blueprint('camp_firozpur', __name__, template_folder='../../templates/camp_firozpur')

from . import routes
