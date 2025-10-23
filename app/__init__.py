import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
from flask_talisman import Talisman
from config import config # Import the config dictionary
from datetime import datetime # <-- Import datetime

# Initialize extensions without binding them to a specific app instance yet
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()
sess = Session()
talisman = Talisman()

# Configure Flask-Login
login_manager.login_view = 'auth.login' # The route function name for the login page
login_manager.login_message_category = 'info' # Bootstrap class for flash messages
login_manager.session_protection = "strong" # Helps prevent session fixation

# Content Security Policy (adjust as needed, especially for external JS/CSS/Fonts)
def get_csp():
    return {
        'default-src': [
            '\'self\'',
            'https://cdn.jsdelivr.net' # Example: Allow Bootstrap CDN
        ],
        'script-src': [
            '\'self\'',
            'https://cdn.jsdelivr.net', # Example: Allow Bootstrap JS
            'https://unpkg.com'       # Allow html5-qrcode library
        ],
        'style-src': [
            '\'self\'',
            'https://cdn.jsdelivr.net' # Example: Allow Bootstrap CSS'
        ],
        # Add img-src to allow data URIs for inline SVGs (e.g., from Bootstrap)
        'img-src': [
            '\'self\'',
            'data:',
            'https://cdn.jsdelivr.net'
        ],
        # Add other directives as needed (font-src, etc.)
    }

def create_app(config_name='default'):
    """Application factory function."""
    app = Flask(__name__)
    
    # Load configuration from the specified config object
    app.config.from_object(config[config_name])
    config[config_name].init_app(app) # Perform any config-specific initializations

    # FORCE pymssql driver for Azure deployment - override any existing database URL
    if app.config.get('DATABASE_URL'):
        original_url = app.config['DATABASE_URL']
        if original_url.startswith('mssql://') or original_url.startswith('mssql+pyodbc://'):
            # Force conversion to pymssql
            clean_url = original_url.replace('mssql+pyodbc://', 'mssql://').replace('mssql://', 'mssql+pymssql://')
            if '?' in clean_url:
                base_url = clean_url.split('?')[0]
                app.config['SQLALCHEMY_DATABASE_URI'] = base_url + '?charset=utf8&timeout=30'
            else:
                app.config['SQLALCHEMY_DATABASE_URI'] = clean_url + '?charset=utf8&timeout=30'
            app.logger.info(f"Forced database URL to use pymssql: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # Initialize extensions with the app instance
    try:
        db.init_app(app)
        app.logger.info("Database initialized successfully")
    except Exception as e:
        app.logger.error(f"Database initialization failed: {e}")
        # Continue with app creation, but log the error
        
    migrate.init_app(app, db) # Initialize Migrate after SQLAlchemy
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    sess.init_app(app) # Initialize Flask-Session
    
    # Initialize Flask-Talisman with Content Security Policy
    # Disable CSP in testing or if causing issues during development
    csp_enabled = not app.config.get('TESTING', False)
    talisman.init_app(
        app,
        force_https=app.config['TALISMAN_FORCE_HTTPS'],
        strict_transport_security=app.config['TALISMAN_STRICT_TRANSPORT_SECURITY'],
        session_cookie_secure=app.config['TALISMAN_SESSION_COOKIE_SECURE'],
        content_security_policy=get_csp() if csp_enabled else None,
        content_security_policy_nonce_in=['script-src'] # Optional: For inline scripts if needed
    )

    # --- Inject datetime into template context --- #
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow}

    # --- Register Blueprints --- #
    # (We will create these blueprint files next)
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .fridge import fridge as fridge_blueprint
    app.register_blueprint(fridge_blueprint, url_prefix='/fridge')

    from .favorites import favorites as favorites_blueprint
    app.register_blueprint(favorites_blueprint, url_prefix='/favorites')
    
    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    from .storage import storage as storage_blueprint
    app.register_blueprint(storage_blueprint, url_prefix='/storage')
    
    from app.team import team as team_blueprint
    app.register_blueprint(team_blueprint, url_prefix='/team')

    # --- Define a simple main route --- #
    @app.route('/')
    def index():
        return render_template('index.html') # We'll create this template later

    # --- Error Handlers --- #
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        # Log the error details if not in debug mode
        if not app.debug:
            app.logger.error(f"Server Error: {e}", exc_info=True)
        return render_template('500.html'), 500
        
    # --- Create necessary directories if they don't exist --- #
    if not os.path.exists(app.config['SESSION_FILE_DIR']):
        os.makedirs(app.config['SESSION_FILE_DIR'])

    # --- Initialize Database Tables if needed --- #
    @app.before_first_request
    def create_tables():
        """Create database tables on first request if they don't exist."""
        try:
            # Test database connection first
            with app.app_context():
                with db.engine.connect() as connection:
                    connection.execute(db.text('SELECT 1'))
                app.logger.info("Database connection successful")
                
            db.create_all()
            app.logger.info("Database tables created/verified")
            
            # Create admin user if it doesn't exist
            from .models import User
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin = User(
                    username='admin',
                    email='admin@smartfridge.com',
                    is_admin=True,
                    is_approved=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                app.logger.info("Admin user created")
            else:
                app.logger.info("Admin user already exists")
                
        except Exception as e:
            app.logger.error(f"Database initialization error: {e}")
            # Don't fail the app start, just log the error
            pass

    return app