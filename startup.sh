#!/bin/bash
# Azure App Service startup script
# This runs when the container starts

echo "🚀 Starting SmartFridge application..."

# Navigate to the app directory
cd /home/site/wwwroot

# Check if database needs initialization
echo "🔍 Checking database status..."

# Run database initialization script
python init_db.py

# Check if initialization was successful
if [ $? -eq 0 ]; then
    echo "✅ Database ready"
else
    echo "❌ Database initialization failed"
fi

# Start the Flask application with Gunicorn
echo "🌐 Starting web server..."
exec gunicorn --bind 0.0.0.0:8000 run:app
