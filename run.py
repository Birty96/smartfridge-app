#!/usr/bin/env python
import os
import click # Import click for CLI commands
from flask import current_app # Import current_app
from app import create_app, db
from app.models import User, Ingredient, Recipe, FavoriteSite # Add Recipe, FavoriteSite
from flask_migrate import Migrate

# Load environment variables from .env file if it exists
# from dotenv import load_dotenv
# load_dotenv()

# Determine which configuration to use (default to 'default')
# Set FLASK_CONFIG environment variable to 'development', 'testing', or 'production'
config_name = os.environ.get('FLASK_CONFIG') or 'default'

app = create_app(config_name)
migrate = Migrate(app, db)

@app.shell_context_processor
def make_shell_context():
    """Makes variables available in the Flask shell context."""
    return {'db': db, 'User': User, 'Ingredient': Ingredient, 'Recipe': Recipe, 'FavoriteSite': FavoriteSite} 

# --- CLI Commands --- #
@app.cli.command('create-admin')
@click.argument('username')
@click.argument('email')
@click.password_option()
def create_admin(username, email, password):
    """Creates a new admin user."""
    if User.query.filter((User.username == username) | (User.email == email)).first():
        click.echo(f'Error: Username \'{username}\' or Email \'{email}\' already exists.')
        return
    
    try:
        user = User(username=username, email=email.lower(), is_admin=True)
        user.password = password # Use the setter for validation and hashing
        db.session.add(user)
        db.session.commit()
        click.echo(f'Admin user \'{username}\' created successfully.')
    except ValueError as e:
        click.echo(f'Error creating admin: {e}')
    except Exception as e:
        db.session.rollback()
        click.echo(f'An unexpected error occurred: {e}')

@app.cli.command('set-password')
@click.argument('identifier') # Can be username or email
@click.password_option(prompt='New password', confirmation_prompt=True)
def set_password(identifier, password):
    """Sets a new password for a user identified by username or email."""
    user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
    
    if not user:
        click.echo(f'Error: User \'{identifier}\' not found.')
        return
        
    try:
        user.password = password # Use the setter for validation and hashing
        # Optionally reset lockout status if desired
        user.reset_login_attempts() 
        db.session.commit()
        click.echo(f'Password for user \'{user.username}\' updated successfully.')
    except ValueError as e:
        # Catch password validation errors
        click.echo(f'Error setting password: {e}')
    except Exception as e:
        db.session.rollback()
        click.echo(f'An unexpected error occurred: {e}')

# --- DEPLOYMENT WARNING --- #
# DO NOT use 'flask run' for production deployment.
# Use a production WSGI server like Gunicorn or uWSGI.
# Example with Gunicorn: gunicorn --bind 0.0.0.0:5000 run:app
# Run behind a reverse proxy like Nginx for HTTPS, static files, and added security.
# --- END DEPLOYMENT WARNING --- #

if __name__ == '__main__':
    # Note: app.run() is suitable for development.
    # For production, consider using a more robust WSGI server like Waitress or Gunicorn.
    app.run() 