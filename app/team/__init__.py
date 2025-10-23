from flask import Blueprint

team = Blueprint('team', __name__)

from . import routes 