# camp_delhi blueprint - Longevity camp registration for Delhi (copy of camp)

from flask import Blueprint

camp_delhi_bp = Blueprint('camp_delhi', __name__, template_folder='../../templates/camp_delhi')

from . import routes
