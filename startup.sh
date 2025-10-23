#!/bin/bash
# Azure App Service startup script
# This runs when the container starts

echo "🚀 Starting SmartFridge application..."

# Navigate to the app directory
cd /home/site/wwwroot

# Debug environment variables
echo "🔍 Environment check..."
echo "DATABASE_URL is set: $([ -n "$DATABASE_URL" ] && echo "YES" || echo "NO")"
echo "SECRET_KEY is set: $([ -n "$SECRET_KEY" ] && echo "YES" || echo "NO")"

# Check if database needs initialization
echo "🔍 Checking database status..."

# Run database initialization script with error handling
if python init_db.py; then
    echo "✅ Database ready"
else
    echo "❌ Database initialization failed - continuing with app start"
    echo "   The app will try to initialize the database on first request"
fi

# Start the Flask application with Gunicorn
echo "🌐 Starting web server..."
exec gunicorn --bind 0.0.0.0:8000 --timeout 120 --workers 1 run:app