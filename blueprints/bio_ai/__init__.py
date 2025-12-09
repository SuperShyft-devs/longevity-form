# bio_ai blueprint - Premium longevity assessment with time slots and reference API

from flask import Blueprint

bio_ai_bp = Blueprint('bio_ai', __name__, template_folder='../../templates/bio_ai')

from . import routes
