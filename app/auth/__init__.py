from flask import Blueprint

# Create a Blueprint instance for authentication routes
auth = Blueprint('auth', __name__, template_folder='../templates/auth')

# Import the routes associated with this blueprint
# This import is at the bottom to avoid circular dependencies
from . import routes 