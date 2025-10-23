from flask import Blueprint

# Create a Blueprint instance for admin routes
admin = Blueprint('admin', __name__, template_folder='../templates/admin')

# Import routes and decorators
from . import routes, decorators 