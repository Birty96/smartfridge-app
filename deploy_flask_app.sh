#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration Variables (EDIT THESE!) ---
APP_USER=$(whoami) # Uses the user running the script (should be webserver)
APP_NAME="Web" # Match directory name
# REPO_URL removed as Git operations are skipped
DOMAIN_NAME="birty.dev" # Your primary domain name
WWW_DOMAIN_NAME="www.birty.dev" # Include www subdomain if used
EMAIL_FOR_CERTBOT="joshuabirtwistle@hotmail.com" # Your email for Let's Encrypt/Certbot
PYTHON_VERSION="3.12" # Your server's Python version
# --- End Configuration ---

PROJECT_DIR="/home/webserver/Desktop/Web" # Project Path
VENV_DIR="$PROJECT_DIR/venv"
FLASK_CONFIG="production" # Set the Flask config environment

# --- Helper Functions ---
print_step() {
    echo "--------------------------------------------------"
    echo ">>> $1"
    echo "--------------------------------------------------"
}

# --- Main Script ---

print_step "Prerequisite Check: Ensure Project Code Exists"
if [ ! -d "$PROJECT_DIR" ] || [ ! -f "$PROJECT_DIR/run.py" ] || [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "!!! ERROR: Project directory '$PROJECT_DIR' not found or incomplete. !!!"
    echo "!!! Make sure your project code (including 'run.py' and             !!!"
    echo "!!! 'requirements.txt') is in the correct location before running.   !!!"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    exit 1
else
    echo "Project directory found at '$PROJECT_DIR'. Proceeding..."
    # Navigate into the project directory for subsequent commands
    cd "$PROJECT_DIR"
fi

print_step "1. Updating System Packages"
sudo apt update && sudo apt upgrade -y

print_step "2. Installing System Dependencies (Python, Nginx, Certbot)"
# Removed 'git' from the install list
sudo apt install -y python3-venv python3-dev nginx curl certbot python3-certbot-nginx

# Step 3 (Cloning/Updating Application Repository) is SKIPPED

print_step "4. Setting up Python Virtual Environment"
# Ensure we are in the project directory
cd "$PROJECT_DIR"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment using python${PYTHON_VERSION}..."
    # Use the specific Python version defined above
    python${PYTHON_VERSION} -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists."
fi

print_step "5. Installing/Updating Python Dependencies"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt
echo "Ensuring cachelib is installed (dependency for Flask-Session)..."
"$VENV_DIR/bin/pip" install cachelib # <<< ADDED cachelib installation
"$VENV_DIR/bin/pip" install gunicorn # Ensure Gunicorn is installed

print_step "6. **MANUAL STEP REMINDER:** Setting up Environment Variables"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo "!!! IMPORTANT: Create or verify the .env file in $PROJECT_DIR !!!"
echo "!!! It MUST contain REAL values for SECRET_KEY, DATABASE_URL, etc. !!!"
echo "!!! ***FAILURE TO REPLACE PLACEHOLDERS (like 'YOUR_..._HERE') WILL CAUSE ERRORS***"
echo "!!! ***Especially check DATABASE_URL and MAIL_PORT before proceeding!***"
echo "!!!"
echo "!!! Example values (replace with your actual data):"
echo "!!!   SECRET_KEY='your_long_random_secret_key'"
echo "!!!   DATABASE_URL='sqlite:///app.db'  # Or your PostgreSQL/MySQL URL"
echo "!!!   OPENROUTER_API_KEY='sk-or-v1-your_actual_key'"
echo "!!!   FLASK_CONFIG='production'"
echo "!!!   MAIL_PORT=587  # Must be a number, no quotes!"
echo "!!!   # ... and other MAIL settings if using email features"
echo "!!!"
echo "!!! >>> Press Enter ONLY after you have created/verified the .env file <<<"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
read -p ""

print_step "7. Running Database Migrations"
export FLASK_CONFIG=$FLASK_CONFIG # Ensure Flask uses production config
# Load .env variables for this command if needed by Flask/Alembic during migration
if [ -f "$PROJECT_DIR/.env" ]; then
  export $(grep -v '^#' $PROJECT_DIR/.env | xargs)
fi
"$VENV_DIR/bin/flask" db upgrade

print_step "7.1. Setting up Team Management Directories"
# Create necessary directories for team management
TEAM_UPLOAD_DIR="$PROJECT_DIR/app/static/uploads/team_documents"
SESSION_DIR="$PROJECT_DIR/flask_session"

# Create directories if they don't exist
mkdir -p "$TEAM_UPLOAD_DIR"
mkdir -p "$SESSION_DIR"

# Set proper permissions
sudo chown -R $CURRENT_USER:$SERVICE_GROUP "$TEAM_UPLOAD_DIR"
sudo chown -R $CURRENT_USER:$SERVICE_GROUP "$SESSION_DIR"
sudo chmod -R 775 "$TEAM_UPLOAD_DIR"
sudo chmod -R 775 "$SESSION_DIR"

print_step "8. Setting up Gunicorn Systemd Service"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service" # Will be /etc/systemd/system/Web.service
echo "Creating/Updating Gunicorn service file: $SERVICE_FILE"
# Use the user running the script for User= and Group= by default, adjust if needed
CURRENT_USER=$(whoami)
# Find primary group of the user
CURRENT_GROUP=$(id -gn $CURRENT_USER)

# Use www-data for Group if Nginx needs access, otherwise use user's group
SERVICE_GROUP="www-data" # Common default for Nginx access to socket
if ! getent group www-data > /dev/null; then
    echo "Warning: Group www-data not found. Using user's group ($CURRENT_GROUP) for Gunicorn service."
    SERVICE_GROUP=$CURRENT_GROUP
fi

cat << EOF | sudo tee "$SERVICE_FILE"
[Unit]
Description=Gunicorn instance for $APP_NAME
After=network.target

[Service]
User=$CURRENT_USER
Group=$SERVICE_GROUP
WorkingDirectory=$PROJECT_DIR
# Load environment variables from .env file for the Gunicorn process
EnvironmentFile=$PROJECT_DIR/.env
# Ensure the path includes the virtual environment
Environment="PATH=$VENV_DIR/bin"
# Command to start Gunicorn
# Ensure the socket path is correct and permissions allow Nginx group (www-data) access
ExecStart=$VENV_DIR/bin/gunicorn --workers 3 --bind unix:$PROJECT_DIR/${APP_NAME}.sock -m 007 run:app

[Install]
WantedBy=multi-user.target
EOF

# Set permissions for the project directory if needed for the group
# sudo chown -R $CURRENT_USER:$SERVICE_GROUP $PROJECT_DIR
# sudo chmod -R g+w $PROJECT_DIR # Grant write access if Gunicorn needs it

sudo systemctl daemon-reload
sudo systemctl enable "$APP_NAME" # Enables Web.service
sudo systemctl restart "$APP_NAME" # Restarts Web.service

# Check Gunicorn status after restart attempt
sleep 2 # Give service time to start/fail
sudo systemctl status "$APP_NAME" --no-pager || echo "Warning: Gunicorn service might not have started correctly. Check status manually."


print_step "9. Configuring Nginx Reverse Proxy (HTTP Only Initially)"
NGINX_CONF="/etc/nginx/sites-available/$APP_NAME" # Will be /etc/nginx/sites-available/Web
# Ensure the sites-enabled directory exists
sudo mkdir -p /etc/nginx/sites-enabled
# Remove default config if it exists and is a symlink
if [ -L "/etc/nginx/sites-enabled/default" ]; then
    echo "Removing default Nginx site configuration..."
    sudo rm -f /etc/nginx/sites-enabled/default
fi

echo "Creating/Updating Nginx config file: $NGINX_CONF"
# Note: We set up for HTTP first, Certbot will modify it for HTTPS
cat << EOF | sudo tee "$NGINX_CONF"
server {
    listen 80;
    server_name $DOMAIN_NAME $WWW_DOMAIN_NAME; # Add www if used

    # Specify root for potential Certbot webroot challenges, though nginx plugin is preferred
    root $PROJECT_DIR/app/static; # Or a dedicated webroot path

    # Location for static files (adjust path if necessary)
    location /static {
        alias $PROJECT_DIR/app/static;
        expires 30d; # Add caching for static files
        add_header Cache-Control "public";
    }

    # Location for the application backend
    location / {
        # Pass requests to the Gunicorn socket
        proxy_pass http://unix:$PROJECT_DIR/${APP_NAME}.sock; # Uses Web.sock
        # Standard proxy headers
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        # Important for Flask-Talisman/HTTPS redirection later
        proxy_set_header X-Forwarded-Proto \$scheme;
        # Increase timeout if needed
        # proxy_connect_timeout 60s;
        # proxy_read_timeout 60s;
    }

    # Optional: Improve security headers (some might be handled by Flask-Talisman)
    # add_header X-Frame-Options "SAMEORIGIN" always;
    # add_header X-XSS-Protection "1; mode=block" always;
    # add_header X-Content-Type-Options "nosniff" always;
    # add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    # add_header Content-Security-Policy "default-src 'self';" always; # Adjust CSP as needed
}
EOF

# Enable the site if not already enabled
if [ ! -L "/etc/nginx/sites-enabled/$APP_NAME" ]; then # Checks for /etc/nginx/sites-enabled/Web
    echo "Enabling Nginx site..."
    sudo ln -s "$NGINX_CONF" "/etc/nginx/sites-enabled/$APP_NAME"
else
    echo "Nginx site already enabled."
fi

# Test Nginx config and restart *before* running Certbot
print_step "Testing and Restarting Nginx..."
sudo nginx -t
if [ $? -ne 0 ]; then
    echo "Nginx configuration test failed! Please fix the errors."
    exit 1
fi
sudo systemctl restart nginx
sleep 5 # Give Nginx a moment to restart fully


print_step "10. Configuring Firewall (UFW)"
# Check if UFW is active
if sudo ufw status | grep -q inactive; then
    echo "UFW is inactive. Enabling..."
    sudo ufw enable
fi
sudo ufw allow ssh # Ensure SSH access is allowed
sudo ufw allow 'Nginx Full' # Allows both HTTP (80) and HTTPS (443)
sudo ufw status

print_step "11. Obtaining/Renewing SSL Certificate via Certbot"
echo "Running Certbot non-interactively for $DOMAIN_NAME and $WWW_DOMAIN_NAME..."
# Ensure Nginx is running before Certbot tries to use the plugin
sudo systemctl is-active --quiet nginx || (echo "Nginx is not running, cannot run Certbot Nginx plugin." && exit 1)

# Run Certbot command
sudo certbot --nginx \
    --non-interactive \
    --agree-tos \
    -m "$EMAIL_FOR_CERTBOT" \
    -d "$DOMAIN_NAME" \
    -d "$WWW_DOMAIN_NAME" \
    --redirect # Automatically redirect HTTP to HTTPS

# Certbot automatically tests and reloads Nginx after successful certificate generation

print_step "Deployment Script Finished!"
echo "--------------------------------------------------"
echo "Your site should now be accessible via HTTPS at https://$DOMAIN_NAME"
echo "Services ($APP_NAME Gunicorn, Nginx) have been started and enabled."
echo "Check Gunicorn status: sudo systemctl status $APP_NAME"
echo "Check Gunicorn logs: sudo journalctl -u $APP_NAME -f"
echo "Check Nginx status: sudo systemctl status nginx"
echo "Check Nginx logs: /var/log/nginx/access.log and /var/log/nginx/error.log"
echo "Check Certbot renewal status: sudo certbot renew --dry-run"
echo "Ensure your DNS records for $DOMAIN_NAME and $WWW_DOMAIN_NAME point to this server's IP."
echo "Remember to keep your .env file secure and backed up."
echo "--------------------------------------------------"
