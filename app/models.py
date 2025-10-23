import re
from datetime import datetime, timedelta
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import validates
from itsdangerous import URLSafeTimedSerializer as Serializer

from app import db, login_manager
from app.constants import (
    DEFAULT_TOKEN_EXPIRY, DEFAULT_PASSWORD_HASH_LENGTH,
    DEFAULT_USERNAME_MIN_LENGTH, DEFAULT_USERNAME_MAX_LENGTH,
    DEFAULT_EMAIL_MAX_LENGTH, USERNAME_PATTERN, SPECIAL_CHARACTERS,
    MAX_INGREDIENT_NAME_LENGTH, MAX_RECIPE_TITLE_LENGTH,
    MAX_SITE_NAME_LENGTH, MAX_URL_LENGTH
)

# --- Association Tables ---
# Many-to-many relationship between Users and saved Recipes
user_saved_recipes = db.Table('user_saved_recipes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipes.id'), primary_key=True)
)

# Many-to-many relationship between Users and completed Recipes
user_completed_recipes = db.Table('user_completed_recipes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipes.id'), primary_key=True),
    db.Column('completed_at', db.DateTime, default=datetime.utcnow) # Track completion time
)

# --- Models ---
class User(UserMixin, db.Model):
    """User model for authentication and relationships."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(DEFAULT_USERNAME_MAX_LENGTH), index=True, unique=True, nullable=False)
    email = db.Column(db.String(DEFAULT_EMAIL_MAX_LENGTH), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(DEFAULT_PASSWORD_HASH_LENGTH))
    is_admin = db.Column(db.Boolean, default=False)
    # Add approval status field
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Login attempt tracking
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)

    # Relationships
    ingredients = db.relationship('Ingredient', backref='owner', lazy='dynamic', cascade="all, delete-orphan")
    favorite_sites = db.relationship('FavoriteSite', backref='owner', lazy='dynamic', cascade="all, delete-orphan")
    saved_recipes = db.relationship('Recipe', secondary=user_saved_recipes,
                                    backref=db.backref('saved_by_users', lazy='dynamic'),
                                    lazy='dynamic')
    completed_recipes = db.relationship('Recipe', secondary=user_completed_recipes,
                                        backref=db.backref('completed_by_users', lazy='dynamic'),
                                        lazy='dynamic')
    team_memberships = db.relationship('TeamMember', backref='user', lazy='dynamic')
    application_permissions = db.relationship('ApplicationPermission', 
        backref='user', 
        lazy='dynamic',
        foreign_keys='ApplicationPermission.user_id'
    )

    def __repr__(self):
        return f'<User {self.username}>'

    @validates('username')
    def validate_username(self, key, username):
        if not username:
            raise AssertionError('Username cannot be empty')
        if len(username) < DEFAULT_USERNAME_MIN_LENGTH or len(username) > DEFAULT_USERNAME_MAX_LENGTH:
            raise AssertionError(f'Username must be between {DEFAULT_USERNAME_MIN_LENGTH} and {DEFAULT_USERNAME_MAX_LENGTH} characters')
        if not re.match(USERNAME_PATTERN, username):
            raise AssertionError('Username must contain only letters, numbers, and underscores')
        return username

    @validates('email')
    def validate_email(self, key, email):
        if not email:
            raise AssertionError('Email cannot be empty')
        # Basic format check; more robust validation done by forms (email-validator)
        if '@' not in email or '.' not in email.split('@')[1]:
            raise AssertionError('Invalid email format')
        return email.lower() # Store emails in lowercase

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        # Validate password complexity based on config
        min_length = current_app.config.get('PASSWORD_MIN_LENGTH', 8)
        req_upper = current_app.config.get('PASSWORD_REQ_UPPER', True)
        req_lower = current_app.config.get('PASSWORD_REQ_LOWER', True)
        req_digit = current_app.config.get('PASSWORD_REQ_DIGIT', True)
        req_special = current_app.config.get('PASSWORD_REQ_SPECIAL', False)
        
        if len(password) < min_length:
            raise ValueError(f'Password must be at least {min_length} characters long.')
        if req_upper and not re.search(r"[A-Z]", password):
            raise ValueError('Password must contain an uppercase letter.')
        if req_lower and not re.search(r"[a-z]", password):
            raise ValueError('Password must contain a lowercase letter.')
        if req_digit and not re.search(r"[0-9]", password):
            raise ValueError('Password must contain a digit.')
        if req_special and not re.search(rf"[{re.escape(SPECIAL_CHARACTERS)}]", password):
            raise ValueError('Password must contain a special character.')
            
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    # --- Lockout Logic ---
    def is_locked(self):
        return self.locked_until is not None and self.locked_until > datetime.utcnow()

    def increment_login_attempts(self):
        if not self.is_locked():
            self.login_attempts = (self.login_attempts or 0) + 1
            max_attempts = current_app.config.get('MAX_LOGIN_ATTEMPTS', 5)
            if self.login_attempts >= max_attempts:
                lockout_time = current_app.config.get('LOGIN_LOCKOUT_TIME', 300)
                self.locked_until = datetime.utcnow() + timedelta(seconds=lockout_time)
            db.session.add(self)

    def reset_login_attempts(self):
        self.login_attempts = 0
        self.locked_until = None
        db.session.add(self)

    # --- Password Reset Token Logic ---
    def get_reset_token(self, expires_sec: int = DEFAULT_TOKEN_EXPIRY) -> str:
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token: str, expires_sec: int = DEFAULT_TOKEN_EXPIRY):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expires_sec)
            user_id = data.get('user_id')
        except Exception as e:
            current_app.logger.warning(f"Password reset token verification failed: {e}")
            return None
        return User.query.get(user_id)

    # --- Recipe Management ---
    def save_recipe(self, recipe):
        if not self.has_saved_recipe(recipe):
            self.saved_recipes.append(recipe)

    def unsave_recipe(self, recipe):
        if self.has_saved_recipe(recipe):
            self.saved_recipes.remove(recipe)

    def has_saved_recipe(self, recipe):
        return self.saved_recipes.filter(
            user_saved_recipes.c.recipe_id == recipe.id).count() > 0

    # Add methods for completed recipes
    def complete_recipe(self, recipe):
        # Avoid adding if already completed? Or allow multiple completions?
        # Simple approach: Add if not already associated via this table.
        if not self.has_completed_recipe(recipe):
             # Use the association table directly to add with timestamp
             # Note: This requires the table to be defined BEFORE the User model
             ins = user_completed_recipes.insert().values(
                 user_id=self.id, 
                 recipe_id=recipe.id, 
                 completed_at=datetime.utcnow()
             )
             db.session.execute(ins)

    def has_completed_recipe(self, recipe):
        # Query the association table directly
        return db.session.query(user_completed_recipes).filter_by(
            user_id=self.id, recipe_id=recipe.id
        ).count() > 0

# Flask-Login user loader callback
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Ingredient(db.Model):
    """Model for ingredients stored by users."""
    __tablename__ = 'ingredients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(MAX_INGREDIENT_NAME_LENGTH), nullable=False, index=True)
    quantity = db.Column(db.Float, nullable=True)
    unit = db.Column(db.String(50), nullable=True)
    weight = db.Column(db.Float, nullable=True)
    weight_unit = db.Column(db.String(50), nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    @validates('name')
    def validate_name(self, key, name):
        if not name:
            raise AssertionError('Ingredient name cannot be empty')
        return name.strip()
    
    # Constraint: Either quantity or weight must be provided (handled in forms/routes)

    def __repr__(self):
        return f'<Ingredient {self.name}>'


class Recipe(db.Model):
    """Model for generated or saved recipes."""
    __tablename__ = 'recipes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(MAX_RECIPE_TITLE_LENGTH), nullable=False)
    ingredients_text = db.Column(db.Text, nullable=False) # Store ingredients list as text
    instructions = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(100), default='AI Generated') # Or URL if imported
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Note: Relationship to users who saved it is via user_saved_recipes table

    def __repr__(self):
        return f'<Recipe {self.title}>'


class FavoriteSite(db.Model):
    """Model for users' favorite websites."""
    __tablename__ = 'favorite_sites'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(MAX_SITE_NAME_LENGTH), nullable=False)
    url = db.Column(db.String(MAX_URL_LENGTH), nullable=False)
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    @validates('name')
    def validate_name(self, key, name):
        if not name:
            raise AssertionError('Site name cannot be empty')
        return name.strip()

    @validates('url')
    def validate_url(self, key, url):
        if not url:
            raise AssertionError('URL cannot be empty')
        # Basic check, more robust validation/sanitization happens elsewhere (e.g., utils)
        if not url.startswith(('http://', 'https://')):
             url = 'http://' + url # Add default scheme if missing
        # Add more robust URL validation if needed
        return url

    def __repr__(self):
        return f'<FavoriteSite {self.name}: {self.url}>'

# --- Team Management Models ---
class Team(db.Model):
    """Model for hockey teams."""
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    members = db.relationship('TeamMember', backref='team', lazy='dynamic', cascade="all, delete-orphan")
    events = db.relationship('TeamEvent', backref='team', lazy='dynamic', cascade="all, delete-orphan")
    documents = db.relationship('TeamDocument', backref='team', lazy='dynamic', cascade="all, delete-orphan")
    messages = db.relationship('TeamMessage', backref='team', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Team {self.name}>'

class TeamMember(db.Model):
    """Model for team members and their roles."""
    __tablename__ = 'team_members'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'coach', 'player'
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Statistics
    games_played = db.Column(db.Integer, default=0)
    goals = db.Column(db.Integer, default=0)
    assists = db.Column(db.Integer, default=0)
    penalty_minutes = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<TeamMember {self.user_id} in Team {self.team_id}>'

class TeamEvent(db.Model):
    """Model for team events (games, practices, etc.)."""
    __tablename__ = 'team_events'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_type = db.Column(db.String(50), nullable=False)  # 'game', 'practice', 'meeting'
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    rsvps = db.relationship('EventRSVP', backref='event', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<TeamEvent {self.title}>'

class EventRSVP(db.Model):
    """Model for event RSVPs."""
    __tablename__ = 'event_rsvps'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('team_events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'attending', 'not_attending', 'maybe'
    responded_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<EventRSVP {self.user_id} for Event {self.event_id}>'

class TeamDocument(db.Model):
    """Model for team documents."""
    __tablename__ = 'team_documents'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<TeamDocument {self.title}>'

class TeamMessage(db.Model):
    """Model for team messages and announcements."""
    __tablename__ = 'team_messages'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_announcement = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='team_messages')

    def __repr__(self):
        return f'<TeamMessage {self.id} by User {self.user_id}>'

# --- Application Permissions Model ---
class ApplicationPermission(db.Model):
    """Model for application-specific permissions."""
    __tablename__ = 'application_permissions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    application = db.Column(db.String(50), nullable=False)  # 'team_management', 'recipe_app', etc.
    permission_level = db.Column(db.String(20), nullable=False)  # 'read', 'write', 'admin'
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    granted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<ApplicationPermission {self.application} for User {self.user_id}>' 