from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, FloatField, DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, URL, Regexp, InputRequired
from sqlalchemy.exc import OperationalError
from app.models import User
from app.constants import (
    DEFAULT_USERNAME_MIN_LENGTH, DEFAULT_USERNAME_MAX_LENGTH, DEFAULT_EMAIL_MAX_LENGTH,
    MAX_INGREDIENT_NAME_LENGTH, MAX_SITE_NAME_LENGTH, MAX_URL_LENGTH, SPECIAL_CHARACTERS
)

# --- Custom Validators ---
def password_complexity(form, field):
    """Custom validator for password complexity based on config."""
    password = field.data
    min_length = current_app.config.get('PASSWORD_MIN_LENGTH', 8)
    req_upper = current_app.config.get('PASSWORD_REQ_UPPER', True)
    req_lower = current_app.config.get('PASSWORD_REQ_LOWER', True)
    req_digit = current_app.config.get('PASSWORD_REQ_DIGIT', True)
    req_special = current_app.config.get('PASSWORD_REQ_SPECIAL', False)
    
    errors = []
    if len(password) < min_length:
        errors.append(f'Password must be at least {min_length} characters long.')
    if req_upper and not any(c.isupper() for c in password):
        errors.append('Password must contain an uppercase letter.')
    if req_lower and not any(c.islower() for c in password):
        errors.append('Password must contain a lowercase letter.')
    if req_digit and not any(c.isdigit() for c in password):
        errors.append('Password must contain a digit.')
    if req_special and not any(c in SPECIAL_CHARACTERS for c in password):
        errors.append('Password must contain a special character.')
        
    if errors:
        raise ValidationError(errors)

def either_quantity_or_weight(form, field):
    """Validator to ensure at least quantity or weight is provided for an ingredient."""
    if not form.quantity.data and not form.weight.data:
        raise ValidationError('Please provide either Quantity or Weight.')
    # If quantity is provided, unit is optional but good practice
    # If weight is provided, weight_unit is optional but good practice
    # Could add further validation here if units become mandatory based on value
    
# --- Forms ---

class RegistrationForm(FlaskForm):
    """Form for user registration."""
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=DEFAULT_USERNAME_MIN_LENGTH, max=DEFAULT_USERNAME_MAX_LENGTH),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0, 
               'Usernames must have only letters, numbers, dots or underscores')
    ])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=DEFAULT_EMAIL_MAX_LENGTH)])
    password = PasswordField('Password', validators=[DataRequired(), password_complexity])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        try:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is already taken. Please choose a different one.')
        except OperationalError:
            # Database connection issue - log it but don't fail validation
            current_app.logger.error("Database connection error during username validation")
            # Allow the form to proceed - the actual registration will handle the database error
            pass
        except Exception as e:
            current_app.logger.error(f"Unexpected error during username validation: {e}")
            # Allow the form to proceed for non-database errors too

    def validate_email(self, email):
        try:
            user = User.query.filter_by(email=email.data.lower()).first()
            if user:
                raise ValidationError('That email is already registered. Please use a different one or log in.')
        except OperationalError:
            # Database connection issue - log it but don't fail validation  
            current_app.logger.error("Database connection error during email validation")
            # Allow the form to proceed - the actual registration will handle the database error
            pass
        except Exception as e:
            current_app.logger.error(f"Unexpected error during email validation: {e}")
            # Allow the form to proceed for non-database errors too

class LoginForm(FlaskForm):
    """Form for user login."""
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=DEFAULT_EMAIL_MAX_LENGTH)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ChangePasswordForm(FlaskForm):
    """Form for changing password."""
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), password_complexity])
    confirm_new_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class PasswordResetRequestForm(FlaskForm):
    """Form to request a password reset email."""
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=DEFAULT_EMAIL_MAX_LENGTH)])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        try:
            user = User.query.filter_by(email=email.data.lower()).first()
            if not user:
                # Avoid revealing if email exists
                # raise ValidationError('There is no account with that email. You must register first.')
                pass # Silently pass if email doesn't exist for security
        except OperationalError:
            # Database connection issue - log it but don't fail validation
            current_app.logger.error("Database connection error during password reset email validation")
            # Allow the form to proceed - the actual password reset will handle the database error
            pass
        except Exception as e:
            current_app.logger.error(f"Unexpected error during password reset email validation: {e}")
            # Allow the form to proceed for non-database errors too

class PasswordResetForm(FlaskForm):
    """Form to set a new password after verifying the token."""
    password = PasswordField('New Password', validators=[DataRequired(), password_complexity])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


class IngredientForm(FlaskForm):
    """Form for adding or editing ingredients."""
    name = StringField('Ingredient Name', validators=[DataRequired(), Length(max=MAX_INGREDIENT_NAME_LENGTH)])
    quantity = FloatField('Quantity', validators=[Optional(), either_quantity_or_weight])
    unit = StringField('Unit (e.g., cups, pcs)', validators=[Optional(), Length(max=50)])
    weight = FloatField('Weight', validators=[Optional()])
    weight_unit = StringField('Weight Unit (e.g., g, kg, oz)', validators=[Optional(), Length(max=50)])
    expiry_date = DateField('Expiry Date (Optional)', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Add Ingredient')
    
    # You might add more complex validation, e.g., requiring unit if quantity is set
    # def validate_unit(self, field):
    #     if self.quantity.data and not field.data:
    #         raise ValidationError('Unit is required if Quantity is provided.')

    # def validate_weight_unit(self, field):
    #     if self.weight.data and not field.data:
    #         raise ValidationError('Weight Unit is required if Weight is provided.')

class UpdateIngredientQuantityForm(FlaskForm):
    """Simple form to update ingredient quantity/weight via modal or similar."""
    # Using InputRequired here instead of DataRequired to allow 0 as a valid input
    quantity = FloatField('New Quantity', validators=[Optional()])
    weight = FloatField('New Weight', validators=[Optional()]) 
    submit = SubmitField('Update')

    def validate(self, extra_validators=None):
        """Ensure at least one field is filled."""
        if not super().validate(extra_validators):
            return False
        if self.quantity.data is None and self.weight.data is None:
            # Add error to a field or create a non-field error if preferred
            self.quantity.errors.append('Please provide either a new Quantity or Weight.')
            return False
        return True

class FavoriteSiteForm(FlaskForm):
    """Form for adding favorite websites."""
    name = StringField('Site Name', validators=[DataRequired(), Length(max=MAX_SITE_NAME_LENGTH)])
    url = StringField('URL', validators=[DataRequired(), URL(require_tld=True, message='Invalid URL.'), Length(max=MAX_URL_LENGTH)])
    submit = SubmitField('Add Favorite Site') 