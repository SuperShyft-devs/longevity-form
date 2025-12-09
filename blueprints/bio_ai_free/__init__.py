# bio_ai_free blueprint - Free longevity assessment with time slots

from flask import Blueprint

bio_ai_free_bp = Blueprint('bio_ai_free', __name__, template_folder='../../templates/bio_ai_free')

from . import routes
