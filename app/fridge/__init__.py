from flask import Blueprint

# Create a Blueprint instance for fridge routes
fridge = Blueprint('fridge', __name__, template_folder='../templates/fridge')

# Import the routes associated with this blueprint
# This import is at the bottom to avoid circular dependencies
from . import routes 