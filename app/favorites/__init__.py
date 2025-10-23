from flask import Blueprint

# Create a Blueprint instance for favorites routes
favorites = Blueprint('favorites', __name__, template_folder='../templates/favorites')

# Import the routes associated with this blueprint
from . import routes 