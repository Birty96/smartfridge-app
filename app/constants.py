"""
Application Constants

This module contains constants used throughout the application to avoid
magic numbers and improve maintainability.
"""

# Security Constants
DEFAULT_PASSWORD_MIN_LENGTH = 8
DEFAULT_MAX_LOGIN_ATTEMPTS = 5
DEFAULT_LOGIN_LOCKOUT_TIME = 300  # 5 minutes in seconds

# Session Constants
DEFAULT_SESSION_LIFETIME = 604800  # 7 days in seconds

# Token Constants
DEFAULT_TOKEN_EXPIRY = 1800  # 30 minutes in seconds

# API Constants
DEFAULT_API_TIMEOUT = 10  # seconds
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.7
MAX_RECIPES_RETURNED = 3

# Database Constants
DEFAULT_PASSWORD_HASH_LENGTH = 256
DEFAULT_USERNAME_MIN_LENGTH = 3
DEFAULT_USERNAME_MAX_LENGTH = 64
DEFAULT_EMAIL_MAX_LENGTH = 120

# File Upload Constants
MAX_INGREDIENT_NAME_LENGTH = 100
MAX_RECIPE_TITLE_LENGTH = 200
MAX_SITE_NAME_LENGTH = 100
MAX_URL_LENGTH = 500

# Pagination Constants
DEFAULT_ITEMS_PER_PAGE = 20

# Logging Constants
MAX_LOG_RESPONSE_LENGTH = 200  # characters to log from AI responses

# Special Characters for Password Validation
SPECIAL_CHARACTERS = '!@#$%^&*(),.?":{}|<>'

# Regex Patterns
USERNAME_PATTERN = r"^[A-Za-z0-9_]+$"
QUANTITY_PATTERN = r'^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$'
FRACTION_PATTERN = r'^(\d+)/(\d+)\s*([a-zA-Z]+)$'
MIXED_NUMBER_PATTERN = r'^(\d+)\s+(\d+)/(\d+)\s*([a-zA-Z]+)$'

# HTTP Status Codes (for clarity)
HTTP_OK = 200
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_INTERNAL_SERVER_ERROR = 500