#!/usr/bin/env python3
"""
Database initialization script for SmartFridge application.
This script creates tables and initial data for the application.
"""

import os
import sys

# Add the current directory to Python path so we can import our app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User

def init_database():
    """Initialize the database with tables and admin user."""
    print("🔧 Initializing SmartFridge database...")
    
    # Create Flask app
    app = create_app('production')  # Use production config
    
    with app.app_context():
        try:
            # Create all tables
            print("📋 Creating database tables...")
            db.create_all()
            
            # Check if admin user already exists
            admin_user = User.query.filter_by(username='admin').first()
            if admin_user:
                print("✅ Admin user already exists")
            else:
                # Create admin user
                print("👤 Creating admin user...")
                admin = User(
                    username='admin',
                    email='admin@smartfridge.com',
                    is_admin=True,
                    is_approved=True
                )
                # Use a secure random password
                import secrets
                import string
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                temp_password = ''.join(secrets.choice(alphabet) for i in range(16))
                admin.set_password(temp_password)
                db.session.add(admin)
                db.session.commit()
                print(f"✅ Admin user created: username='admin', password='{temp_password}'")
                print("⚠️  IMPORTANT: Save this password and change it after first login!")
            
            print("🎉 Database initialization completed successfully!")
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            db.session.rollback()
            return False
    
    return True

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)