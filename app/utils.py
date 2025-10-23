import requests
import json
from threading import Thread
from typing import Optional, Dict, Any, Tuple, List, Union
from flask import current_app, render_template, url_for, abort
from flask_mail import Message
from app import mail # Import the Mail instance
from openai import OpenAI # Import if using OpenAI directly
import httpx # <-- Add import
import re # Add import for re
from functools import wraps
from flask_login import current_user
from app.constants import (
    DEFAULT_API_TIMEOUT, QUANTITY_PATTERN, FRACTION_PATTERN, 
    MIXED_NUMBER_PATTERN, MAX_LOG_RESPONSE_LENGTH
)

# --- Email Sending --- #
def send_async_email(app, msg: Message) -> None:
    """Helper function to send email asynchronously in a separate thread."""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            app.logger.error(f"Failed to send email: {e}")

def send_email(subject: str, recipients: List[str], text_body: str, html_body: str) -> None:
    """Sends an email using Flask-Mail, potentially asynchronously."""
    app = current_app._get_current_object() # Get the actual app instance
    msg = Message(subject, sender=app.config['MAIL_DEFAULT_SENDER'], recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    # Send email in background thread
    Thread(target=send_async_email, args=(app, msg)).start()

def send_password_reset_email(user) -> None:
    """Generates a password reset token and sends the email."""
    token = user.get_reset_token()
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    subject = '[Your App Name] Password Reset Request' # CHANGE 'Your App Name'
    send_email(subject,
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt', user=user, reset_url=reset_url),
               html_body=render_template('email/reset_password.html', user=user, reset_url=reset_url))
    # NOTE: You need to create the templates/email/reset_password.txt and .html files.

# --- Barcode Lookup --- #
def fetch_product_info(barcode: str) -> Optional[Dict[str, Any]]:
    """Fetches product information from Open Food Facts API based on barcode."""
    app = current_app._get_current_object()
    # Example using Open Food Facts API (World)
    api_url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    # Some APIs might require user agent or auth
    # headers = {'User-Agent': 'YourAppName/1.0 (yourwebsite.com)'}
    # headers = {'Authorization': f"Bearer {app.config['SOME_API_KEY']}"} 
    headers = {'User-Agent': 'FridgeApp/0.1 - Development'} # Be polite
    
    try:
        response = requests.get(api_url, headers=headers, timeout=DEFAULT_API_TIMEOUT)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        
        data = response.json()
        if data.get('status') == 1 and 'product' in data:
            product = data['product']
            # Extract relevant info (adjust based on API response structure)
            product_info = {
                'name': product.get('product_name') or product.get('generic_name'),
                'quantity': product.get('quantity'), # e.g., "500 g"
                'brands': product.get('brands'),
                'categories': product.get('categories'),
                'image_url': product.get('image_front_url') or product.get('image_url'),
                'barcode': barcode
            }
            # Filter out None values if needed
            product_info = {k: v for k, v in product_info.items() if v is not None and v != ''}
            
            # --- Attempt to parse quantity and unit --- #
            if 'quantity' in product_info and isinstance(product_info['quantity'], str):
                parsed_qty, parsed_unit = parse_quantity_string(product_info['quantity'])
                if parsed_qty is not None:
                    product_info['parsed_quantity'] = parsed_qty
                if parsed_unit:
                    product_info['parsed_unit'] = parsed_unit
            # --- End parsing attempt --- #
            
            return product_info
        else:
            app.logger.info(f"Product not found or status not 1 for barcode {barcode}. Status: {data.get('status')}")
            return None
            
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching barcode {barcode} from Open Food Facts: {e}")
        # Consider specific handling for timeouts, connection errors, etc.
        return None # Or re-raise a custom exception
    except json.JSONDecodeError as e:
        app.logger.error(f"Error decoding JSON response for barcode {barcode}: {e}")
        return None
    except Exception as e:
        app.logger.error(f"Unexpected error during barcode lookup for {barcode}: {e}")
        raise # Re-raise unexpected errors

# --- Helper function for quantity parsing --- #
def parse_quantity_string(quantity_str: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Parse a quantity string like "500 g", "1.5 kg", "250 ml" into quantity and unit.
    
    Args:
        quantity_str: The quantity string to parse
        
    Returns:
        tuple: (quantity_float, unit_string) or (None, None) if parsing fails
    """
    if not quantity_str or not isinstance(quantity_str, str):
        return None, None
    
    # Clean up the string
    quantity_str = quantity_str.strip()
    
    # Common patterns: "500 g", "1.5kg", "250ml", "2 cups", etc.
    # Use regex to extract number and unit
    import re
    
    # Pattern to match: optional decimal number followed by optional whitespace and unit
    pattern = QUANTITY_PATTERN
    match = re.match(pattern, quantity_str)
    
    if match:
        try:
            quantity = float(match.group(1))
            unit = match.group(2).lower()
            return quantity, unit
        except ValueError:
            pass
    
    # Try alternative patterns
    # Pattern for fractions like "1/2 cup"
    fraction_pattern = FRACTION_PATTERN
    fraction_match = re.match(fraction_pattern, quantity_str)
    
    if fraction_match:
        try:
            numerator = float(fraction_match.group(1))
            denominator = float(fraction_match.group(2))
            unit = fraction_match.group(3).lower()
            quantity = numerator / denominator
            return quantity, unit
        except (ValueError, ZeroDivisionError):
            pass
    
    # Pattern for mixed numbers like "1 1/2 cups"
    mixed_pattern = MIXED_NUMBER_PATTERN
    mixed_match = re.match(mixed_pattern, quantity_str)
    
    if mixed_match:
        try:
            whole = float(mixed_match.group(1))
            numerator = float(mixed_match.group(2))
            denominator = float(mixed_match.group(3))
            unit = mixed_match.group(4).lower()
            quantity = whole + (numerator / denominator)
            return quantity, unit
        except (ValueError, ZeroDivisionError):
            pass
    
    # If no patterns match, return None
    return None, None

# --- Recipe Suggestions --- #
def get_recipe_suggestions(ingredient_list: List[str], servings: int = 2) -> Optional[List[Dict[str, Any]]]:
    """
    Gets recipe suggestions from an AI API (e.g., OpenRouter/OpenAI).
    
    This function has been refactored to use the RecipeGenerator class
    for better maintainability and testing.
    """
    from .recipe_generator import RecipeGenerator
    
    try:
        generator = RecipeGenerator()
        return generator.generate_recipes(ingredient_list, servings)
    except Exception as e:
        app = current_app._get_current_object()
        app.logger.error(f"Error getting recipe suggestions: {e}")
        raise

# --- URL Sanitization (Optional) --- #
def sanitize_url(url_string: Optional[str]) -> Optional[str]:
    """Basic URL cleanup (add scheme if missing). More robust sanitization could be added."""
    if not url_string:
        return None
    url_string = url_string.strip()
    if not url_string.startswith(('http://', 'https://')):
        # Add http:// as default, consider https:// if appropriate
        url_string = 'http://' + url_string 
    # Could use libraries like `bleach` for more thorough sanitization if needed
    # from urllib.parse import urlparse, urlunparse
    # parsed = urlparse(url_string)
    # Rebuild or validate components
    return url_string 

def check_permission(application: str, required_level: str):
    """Decorator to check if a user has the required permission level for an application."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
                
            # Admin users have all permissions
            if current_user.is_admin:
                return f(*args, **kwargs)
                
            # Check if user has the required permission
            permission = current_user.application_permissions.filter_by(
                application=application,
                is_active=True
            ).first()
            
            if not permission:
                abort(403)
                
            # Define permission levels hierarchy
            levels = {
                'read': 1,
                'write': 2,
                'admin': 3
            }
            
            if levels.get(permission.permission_level, 0) < levels.get(required_level, 0):
                abort(403)
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator 