# 🍽️ SmartFridge App

A Flask web application for managing your fridge ingredients, generating recipe suggestions, and organizing favorite cooking websites. Designed for secure internet deployment.

## ✨ Features

- 🧊 **Ingredient Tracking** - Keep track of what's in your fridge with expiry dates
- 🤖 **AI Recipe Suggestions** - Get recipe ideas based on your available ingredients  
- ⭐ **Favorite Sites** - Save your go-to cooking websites
- 👥 **User Management** - Multi-user support with secure authentication
- 📱 **Mobile Friendly** - Works great on phones and tablets
- 🔒 **Security First** - Built for safe internet deployment

---

## 🌐 Internet Deployment (Production)

### Prerequisites
- Domain name (optional for Azure)
- Azure account OR Linux server
- SSH access (for VPS) OR Azure CLI (for Azure)

### 🚀 Azure App Service (Recommended for Easy Deployment)

Azure App Service is perfect for this Flask app - it handles SSL, scaling, and maintenance automatically.

#### Option A: Deploy to Azure (Easiest)

**1. Create Azure App Service:**
```bash
# Install Azure CLI if needed
# https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

# Login to Azure
az login

# Create resource group
az group create --name SmartFridge-RG --location "East US"

# Create App Service plan (Linux with Python)
az appservice plan create --name SmartFridge-Plan --resource-group SmartFridge-RG --sku B1 --is-linux

# Create web app
az webapp create --resource-group SmartFridge-RG --plan SmartFridge-Plan --name your-smartfridge-app --runtime "PYTHON|3.11"
```

**2. Configure App Settings:**
```bash
# Generate a secure secret key first
python3 generate_secret_key.py

# Set application settings (environment variables)
az webapp config appsettings set --resource-group SmartFridge-RG --name your-smartfridge-app --settings \
    SECRET_KEY="" \
    FLASK_CONFIG="production" \
    SESSION_COOKIE_SECURE="true" \
    SESSION_COOKIE_HTTPONLY="true" \
    SESSION_COOKIE_SAMESITE="Lax" \
    MAIL_SERVER="smtp.gmail.com" \
    MAIL_PORT="587" \
    MAIL_USE_TLS="true" \
    MAIL_USERNAME="" \
    MAIL_PASSWORD="" \
    SQLALCHEMY_DATABASE_URI=""
```

**⚠️ SECURITY NOTICE:**
- Generate a secure SECRET_KEY using the included script
- Use App Passwords for Gmail SMTP (not your account password)
- Never commit credentials to your repository
- Set all sensitive values through Azure portal or CLI

**3. Deploy to Azure:**
```bash
# Option 1: Deploy from GitHub (Recommended)
az webapp deployment source config --name your-smartfridge-app --resource-group SmartFridge-RG \
    --repo-url https://github.com/yourusername/smartfridge-app --branch main --manual-integration

# Option 2: Deploy ZIP file
az webapp deployment source config-zip --resource-group SmartFridge-RG --name your-smartfridge-app --src smartfridge-app.zip
```

**4. Initialize Database:**
```bash
# SSH into your Azure app to run database initialization
az webapp ssh --resource-group SmartFridge-RG --name your-smartfridge-app

# Inside the SSH session:
python3 -m flask init-db
```

#### Option B: Traditional VPS Deployment

**1. Server Setup:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv nginx git -y

# Clone your repository
git clone https://github.com/yourusername/smartfridge-app.git
cd smartfridge-app
```

**2. Create Virtual Environment:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Configure Environment:**
```bash
# Create environment file
cp .env.example .env
nano .env  # Edit with your settings
```

**4. Initialize Database:**
```bash
python3 init_db.py
```

**5. Configure Nginx (Production):**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**6. Setup SSL with Let's Encrypt:**
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

**7. Run with Gunicorn:**
```bash
pip install gunicorn
gunicorn --bind 0.0.0.0:5000 run:app
```

---

## 🏠 Local Development

### Quick Start
```bash
# Clone and enter directory
git clone https://github.com/yourusername/smartfridge-app.git
cd smartfridge-app

# Run setup script (creates venv, installs deps, initializes DB)
python setup_and_run.py
```

### Manual Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Run the application
python run.py
```

Open your browser to `http://localhost:5000`

### Default Admin Account
- Username: `admin`
- Password: Generated randomly (shown in console during first setup)

---

## 🛠️ Configuration

### Environment Variables
Set these in your `.env` file or system environment:

```env
SECRET_KEY=your-secret-key-here
FLASK_CONFIG=development  # or 'production'
SQLALCHEMY_DATABASE_URI=sqlite:///smartfridge.db  # or your database URL
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### Security Settings
- Strong SECRET_KEY required for production
- CSRF protection enabled
- Session security configured
- Password requirements enforced
- SQL injection protection

---

## 📋 CLI Commands

```bash
# Create admin user
python run.py create-admin

# Reset user password
python run.py set-password username

# Initialize database
python run.py init-db
```

---

## 🗄️ Database Schema

- **Users** - Authentication and user management
- **Items** - Fridge ingredients with expiry tracking
- **Recipes** - Generated and saved recipes
- **Sites** - Favorite cooking websites
- **Teams** - Team/family management (optional)

---

## 🔒 Security Features

- 🛡️ CSRF Protection
- 🔐 Secure Password Hashing (bcrypt)
- 🍪 Secure Session Management
- 🔒 SQL Injection Prevention
- 🌐 HTTPS Enforcement (production)
- 👤 User Input Validation
- 🚫 XSS Protection Headers

---

## 🧪 Testing

```bash
# Run tests
python -m pytest

# Run with coverage
python -m pytest --cov=app
```

---

## 📝 License

This project is open source. Feel free to use and modify for your needs.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 📞 Support

For issues or questions:
- Create an issue on GitHub
- Check existing documentation
- Review the configuration settings

---

## 📊 Tech Stack

- **Backend**: Flask 2.3+, SQLAlchemy, Flask-Login
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap
- **Database**: SQLite (dev), PostgreSQL/MySQL (prod)
- **Deployment**: Azure App Service, Docker, traditional VPS
- **Security**: Flask-Talisman, CSRF, bcrypt

Enjoy your SmartFridge! 🍽️✨