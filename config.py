import os
from dotenv import load_dotenv
from app.constants import (
    DEFAULT_SESSION_LIFETIME, DEFAULT_PASSWORD_MIN_LENGTH, 
    DEFAULT_MAX_LOGIN_ATTEMPTS, DEFAULT_LOGIN_LOCKOUT_TIME
)

# Determine the base directory of the project
basedir = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env file
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Base configuration settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is required and must be set")
    
    # Database Configuration - Support both Azure SQL and SQLite
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        # Azure SQL Database or other external database
        if DATABASE_URL.startswith('mssql://'):
            # Convert Azure SQL connection string format
            # First try to detect which driver is available
            available_driver = None
            
            # Check for ODBC Driver 18 (newest)
            try:
                import pyodbc
                drivers = [d for d in pyodbc.drivers() if 'ODBC Driver' in d]
                if any('18' in d for d in drivers):
                    available_driver = 'ODBC Driver 18 for SQL Server'
                elif any('17' in d for d in drivers):
                    available_driver = 'ODBC Driver 17 for SQL Server'
                elif drivers:
                    available_driver = drivers[0]  # Use first available
            except (ImportError, Exception):
                pass
            
            if available_driver:
                # Use pyodbc with detected driver
                SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('mssql://', 'mssql+pyodbc://')
                driver_param = f'driver={available_driver}'
                connection_params = 'Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30'
                
                if '?' not in SQLALCHEMY_DATABASE_URI:
                    SQLALCHEMY_DATABASE_URI += f'?{driver_param}&{connection_params}'
                else:
                    SQLALCHEMY_DATABASE_URI += f'&{driver_param}&{connection_params}'
            else:
                # Fall back to pymssql for Linux environments
                SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('mssql://', 'mssql+pymssql://')
                if '?' not in SQLALCHEMY_DATABASE_URI:
                    SQLALCHEMY_DATABASE_URI += '?charset=utf8&timeout=30'
                else:
                    SQLALCHEMY_DATABASE_URI += '&charset=utf8&timeout=30'
        else:
            SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Fallback to SQLite for local development
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # Mail server configuration (using Gmail as an example, requires App Password)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') # Your Gmail address or App Password username
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') # Your Gmail App Password
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') # Should be same as MAIL_USERNAME for Gmail

    # Session configuration (using filesystem)
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(basedir, 'flask_session') # Directory to store session files
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    PERMANENT_SESSION_LIFETIME = DEFAULT_SESSION_LIFETIME
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ['true', 'on', '1'] # Set True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Security settings
    PASSWORD_MIN_LENGTH = DEFAULT_PASSWORD_MIN_LENGTH
    PASSWORD_REQ_UPPER = True
    PASSWORD_REQ_LOWER = True
    PASSWORD_REQ_DIGIT = True
    PASSWORD_REQ_SPECIAL = False # Keep false for simpler home use?
    MAX_LOGIN_ATTEMPTS = DEFAULT_MAX_LOGIN_ATTEMPTS
    LOGIN_LOCKOUT_TIME = DEFAULT_LOGIN_LOCKOUT_TIME

    # External API Keys (placeholders)
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    # Add other API keys if needed (e.g., for barcode lookup)
    # OPEN_FOOD_FACTS_API_USER = os.environ.get('OPEN_FOOD_FACTS_API_USER')

    # Flask-Talisman settings (for HTTPS enforcement and security headers)
    # Ensure this is True when deploying with HTTPS
    TALISMAN_FORCE_HTTPS = os.environ.get('TALISMAN_FORCE_HTTPS', 'False').lower() in ['true', 'on', '1']
    TALISMAN_STRICT_TRANSPORT_SECURITY = TALISMAN_FORCE_HTTPS # Enable HSTS only if HTTPS is forced
    TALISMAN_SESSION_COOKIE_SECURE = SESSION_COOKIE_SECURE # Ensure Talisman and Session agree

    @staticmethod
    def init_app(app):
        # Create the directory for filesystem sessions if it doesn't exist
        session_dir = app.config.get('SESSION_FILE_DIR')
        if session_dir and not os.path.exists(session_dir):
            os.makedirs(session_dir)
        pass

class DevelopmentConfig(Config):
    """Development-specific configuration."""
    DEBUG = True
    # In development, we typically don't force HTTPS or secure cookies
    SESSION_COOKIE_SECURE = False
    TALISMAN_FORCE_HTTPS = False
    TALISMAN_STRICT_TRANSPORT_SECURITY = False
    TALISMAN_SESSION_COOKIE_SECURE = False

class TestingConfig(Config):
    """Testing-specific configuration."""
    TESTING = True
    SECRET_KEY = 'test-key-only-for-testing'  # Override for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Use in-memory SQLite for tests
    WTF_CSRF_ENABLED = False # Disable CSRF protection in tests
    SESSION_COOKIE_SECURE = False
    TALISMAN_FORCE_HTTPS = False
    TALISMAN_STRICT_TRANSPORT_SECURITY = False
    TALISMAN_SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Production-specific configuration."""
    # Ensure HTTPS is forced and cookies are secure in production
    SESSION_COOKIE_SECURE = True
    TALISMAN_FORCE_HTTPS = True
    TALISMAN_STRICT_TRANSPORT_SECURITY = True
    TALISMAN_SESSION_COOKIE_SECURE = True
    
    # Use secure session storage for Azure App Service
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = '/tmp/flask_session'  # Use /tmp for Azure App Service

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Ensure session directory exists
        import os
        session_dir = app.config.get('SESSION_FILE_DIR')
        if session_dir and not os.path.exists(session_dir):
            try:
                os.makedirs(session_dir, mode=0o755)
            except OSError:
                # Fallback to in-memory sessions if filesystem is not writable
                app.config['SESSION_TYPE'] = 'null'
        
        # Log errors to stderr or configure more sophisticated logging
        import logging
        from logging import StreamHandler
        handler = StreamHandler()
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)

# Dictionary mapping config names to their classes
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 