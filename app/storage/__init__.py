from flask import Blueprint

storage = Blueprint('storage', __name__, template_folder='templates')

from . import routes
