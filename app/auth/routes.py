from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from datetime import datetime
from sqlalchemy.exc import OperationalError

from app import db
from app.models import User
from . import auth # Import the blueprint instance
from app.forms import (LoginForm, RegistrationForm, ChangePasswordForm, 
                     PasswordResetRequestForm, PasswordResetForm)
from app.utils import send_password_reset_email # We will create utils.py later

@auth.before_request
def before_request():
    """Update last_seen timestamp for logged-in users before each request to this blueprint."""
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('index')) # Redirect logged-in users
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(username=form.username.data, email=form.email.data.lower())
            user.password = form.password.data # Use the password setter
            db.session.add(user)
            db.session.commit()
            flash('Congratulations, you are now a registered user! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except ValueError as e:
             # Catch password validation errors from the model setter
            flash(str(e), 'danger')
        except OperationalError as e:
            db.session.rollback()
            current_app.logger.error(f"Database connection error during registration: {e}")
            flash('Database connection error. Please try again later.', 'danger')
        except Exception as e:
            db.session.rollback() # Rollback in case of other errors
            flash('An unexpected error occurred during registration. Please try again.', 'danger')
            current_app.logger.error(f"Registration error: {e}")
            
    return render_template('auth/register.html', title='Register', form=form)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(email=form.email.data.lower()).first()
            
            if user is None:
                flash('Invalid email or password.', 'warning') # Generic message
                return redirect(url_for('auth.login'))

            if user.is_locked():
                flash(f'Account locked due to too many failed login attempts. Please try again later or reset your password.', 'danger')
                return redirect(url_for('auth.login'))

            if not user.verify_password(form.password.data):
                user.increment_login_attempts()
                db.session.commit()
                flash('Invalid email or password.', 'warning') # Generic message
                return redirect(url_for('auth.login'))

            # --- NEW: Check if user is approved --- #
            if not user.is_approved:
                 flash('Your account has not been approved by an administrator yet.', 'warning')
                 return redirect(url_for('auth.login'))
            # --- END NEW --- #

            # Password is correct, reset attempts and log in
            user.reset_login_attempts()
            db.session.commit()
            login_user(user, remember=form.remember_me.data)
            flash('Login successful!', 'success')
            
        except OperationalError as e:
            current_app.logger.error(f"Database connection error during login: {e}")
            flash('Database connection error. Please try again later.', 'danger')
            return render_template('auth/login.html', title='Sign In', form=form)
        except Exception as e:
            current_app.logger.error(f"Unexpected error during login: {e}")
            flash('An unexpected error occurred. Please try again.', 'danger')
            return render_template('auth/login.html', title='Sign In', form=form)
        
        # Redirect to the page the user was trying to access, or the index page
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
        
    return render_template('login.html', title='Sign In', form=form)

@auth.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@auth.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Allow logged-in users to change their password."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.verify_password(form.old_password.data):
            flash('Invalid old password.', 'danger')
        else:
            try:
                current_user.password = form.new_password.data # Use the setter
                db.session.commit()
                flash('Your password has been updated successfully.', 'success')
                return redirect(url_for('index')) # Or profile page
            except ValueError as e:
                 flash(str(e), 'danger') # Show complexity errors
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while updating your password.', 'danger')
                current_app.logger.error(f"Change password error: {e}")
                
    return render_template('change_password.html', title='Change Password', form=form)

@auth.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    """Handle request for password reset email."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            # Check if email sending is configured
            if not current_app.config.get('MAIL_SERVER') or \
               not current_app.config.get('MAIL_USERNAME') or \
               not current_app.config.get('MAIL_PASSWORD'):
                flash('Password reset emails are not configured on this server. Please contact the administrator.', 'danger')
                return redirect(url_for('auth.login'))
            try:
                send_password_reset_email(user)
                flash('Check your email for instructions to reset your password.', 'info')
            except Exception as e:
                 flash('An error occurred while sending the password reset email. Please try again later.', 'danger')
                 current_app.logger.error(f"Password reset email error: {e}")
        else:
             # Still show the same message even if user doesn't exist
             flash('Check your email for instructions to reset your password.', 'info')
             
        return redirect(url_for('auth.login'))
        
    return render_template('reset_password_request.html', title='Reset Password', form=form)

@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset after verifying the token."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    user = User.verify_reset_token(token)
    if not user:
        flash('The password reset link is invalid or has expired.', 'warning')
        return redirect(url_for('auth.reset_password_request'))
        
    form = PasswordResetForm()
    if form.validate_on_submit():
        try:
            user.password = form.password.data # Use the setter
            user.reset_login_attempts() # Unlock account if it was locked
            db.session.commit()
            flash('Your password has been reset successfully. You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        except ValueError as e:
            flash(str(e), 'danger') # Show complexity errors
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while resetting your password.', 'danger')
            current_app.logger.error(f"Password reset error: {e}")
            
    return render_template('reset_password.html', title='Reset Password', form=form, token=token) 