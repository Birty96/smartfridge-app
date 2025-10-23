# 🍽️ SmartFridge App

A Flask web application for managing your fridge ingredients, generating recipe suggestions, and organizing favorite cooking websites. Perfect for home use!

## ✨ Features

- 🧊 **Ingredient Tracking** - Keep track of what's in your fridge with expiry dates
- 🤖 **AI Recipe Suggestions** - Get recipe ideas based on your available ingredients  
- ⭐ **Favorite Sites** - Save your go-to cooking websites
- 👥 **User Management** - Multi-user support with secure authentication
- 📱 **Mobile Friendly** - Works great on phones and tablets

---

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

```bash
# Create resource group
az group create --name SmartFridge-RG --location "UK South"

# Create App Service plan (Basic tier)
az appservice plan create --name SmartFridge-Plan --resource-group SmartFridge-RG --sku B1 --is-linux

# Create the web app
az webapp create --resource-group SmartFridge-RG --plan SmartFridge-Plan --name your-smartfridge-app --runtime "PYTHON|3.11"
```

**2. Configure Environment Variables:**
```bash
# Generate secret key locally
python3 generate_secret_key.py

# Set application settings (environment variables)
az webapp config appsettings set --resource-group SmartFridge-RG --name your-smartfridge-app --settings \
    SECRET_KEY="fe74eca42349621a21c6a693e5eb37293b129591844d5d5b576903d27e9a97ae" \
    FLASK_CONFIG="production" \
    SESSION_COOKIE_SECURE="true" \
    TALISMAN_FORCE_HTTPS="true" \
    OPENROUTER_API_KEY="your-api-key" \
    MAIL_SERVER="smtp.googlemail.com" \
    MAIL_PORT="587" \
    MAIL_USE_TLS="true" \
    MAIL_USERNAME="joshuabirtwistle@hotmail.com" \
    MAIL_PASSWORD="Icehockey2025!"
```

**3. Deploy Your Code:**

**Option 3A: Using Git (Recommended)**
```bash
# First, install Git if not already installed:
# Windows: Download from https://git-scm.com/download/win
# Or install via winget: winget install --id Git.Git -e --source winget

# After installing Git, restart PowerShell and run:
git init
git add .
git commit -m "Initial commit"

# Add Azure remote
git remote add azure https://your-smartfridge-app.scm.azurewebsites.net:443/your-smartfridge-app.git

# Deploy to Azure
git push azure main
```

**Option 3B: Using Azure CLI (If Git not available)**
```bash
# Create a ZIP file of your project
Compress-Archive -Path * -DestinationPath smartfridge.zip

# Deploy using Azure CLI
az webapp deployment source config-zip --resource-group SmartFridge-RG --name your-smartfridge-app --src smartfridge.zip
```

**Option 3C: Using VS Code (Easiest for Windows)**
```bash
# 1. Install the Azure App Service extension in VS Code
# 2. Open your project folder in VS Code
# 3. Right-click on your project in Explorer
# 4. Select "Deploy to Web App..."
# 5. Choose your Azure subscription and app
```

**4. Create Admin User:**
```bash
# Use Azure Cloud Shell or local terminal with Azure CLI
az webapp ssh --resource-group SmartFridge-RG --name your-smartfridge-app

# In the SSH session:
cd /home/site/wwwroot
python -m flask shell

# In Flask shell:
from app.models import User
from app import db
user = User.query.filter_by(email='your-email@example.com').first()
if user:
    user.is_approved = True
    user.is_admin = True
    db.session.commit()
    print(f"✅ {user.username} is now admin")
exit()
```

**5. Access Your App:**
- Your app will be available at: `https://your-smartfridge-app.azurewebsites.net`
- Azure automatically provides SSL certificates!

#### Option B: VPS Deployment (Traditional Linux Server)

#### Option B: VPS Deployment (Traditional Linux Server)

**Prerequisites:** Linux server, domain name, SSH access

#### 1. Server Setup
```bash
# On your server
git clone https://github.com/Birty96/WebV2.git /home/$(whoami)/Desktop/Web
cd /home/$(whoami)/Desktop/Web
```

#### 2. Security Configuration
```bash
# Generate a secure secret key
python3 generate_secret_key.py

# Copy and edit environment file
cp .env.example .env
nano .env
```

**Critical Security Settings for Internet Deployment:**
```env
# REQUIRED - Use the generated key from step above
SECRET_KEY=your-64-character-secure-key-here

# Production environment
FLASK_CONFIG=production

# Force HTTPS (CRITICAL for internet deployment)
SESSION_COOKIE_SECURE=true
TALISMAN_FORCE_HTTPS=true

# Database (SQLite for simple setup, PostgreSQL for high traffic)
DATABASE_URL=sqlite:///app.db

# Optional: AI Recipe Features
OPENROUTER_API_KEY=your-openrouter-key-here

# Optional: Email Features (for password reset)
MAIL_SERVER=smtp.googlemail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

#### 3. Automated Deployment
```bash
chmod +x deploy_flask_app.sh
./deploy_flask_app.sh
```

**The script automatically handles:**
- ✅ System updates and security patches
- ✅ Python environment setup
- ✅ Nginx web server configuration
- ✅ SSL certificate installation (Let's Encrypt)
- ✅ Firewall configuration (UFW)
- ✅ Systemd service creation
- ✅ Security headers and HTTPS enforcement

#### 4. Create Admin User
After deployment:
```bash
# Navigate to your domain and register the first user
# Then on the server:
cd /home/$(whoami)/Desktop/Web
source venv/bin/activate
flask shell
```

In the Flask shell:
```python
from app.models import User
from app import db

# Replace with your registered email
user = User.query.filter_by(email='your-email@example.com').first()
if user:
    user.is_approved = True
    user.is_admin = True
    db.session.commit()
    print(f"✅ {user.username} is now admin")
else:
    print("❌ User not found - check email address")
exit()
```

#### 5. Access Your App
Visit `https://yourdomain.com` - you're live! 🎉

### 🤔 Azure vs VPS Comparison

| Feature | Azure App Service | Linux VPS |
|---------|------------------|-----------|
| **Setup Time** | 15 minutes | 30-60 minutes |
| **SSL Certificates** | ✅ Automatic | Manual setup |
| **Scaling** | ✅ Automatic | Manual |
| **Maintenance** | ✅ Azure handles it | You manage updates |
| **Cost** | ~$13-55/month | ~$5-20/month |
| **Custom Domain** | ✅ Easy setup | DNS configuration needed |
| **Backups** | ✅ Built-in | Manual setup |
| **Monitoring** | ✅ Built-in | Manual setup |
| **Best For** | Beginners, production apps | Advanced users, cost-conscious |

**Recommendation:** Use Azure App Service for easiest deployment and management!

---

## 🔒 Security Features (Internet-Ready)

### Built-in Security
- **HTTPS Enforced** - All traffic encrypted with SSL/TLS
- **CSRF Protection** - Prevents cross-site request forgery
- **Secure Sessions** - HTTP-only, secure cookies
- **Password Security** - Bcrypt hashing, complexity requirements
- **Account Lockout** - Protection against brute force attacks
- **Security Headers** - HSTS, CSP, and more via Flask-Talisman

### User Authentication
- **Secure Registration** - Admin approval required for new users
- **Password Reset** - Secure token-based password recovery
- **Session Management** - Automatic logout, remember me options
- **Account Verification** - Email verification (if configured)

### Network Security
- **Firewall** - UFW configured to allow only necessary ports (80, 443, 22)
- **SSL Certificates** - Automatic Let's Encrypt renewal
- **Rate Limiting** - Built into the application framework
- **Secure Headers** - Content Security Policy, HSTS, etc.

---

## 🔧 Configuration Options

### Required for Internet Deployment

| Setting | Purpose | Security Impact |
|---------|---------|-----------------|
| `SECRET_KEY` | Session encryption | **CRITICAL** - Must be secure |
| `FLASK_CONFIG=production` | Production optimizations | **HIGH** - Disables debug info |
| `SESSION_COOKIE_SECURE=true` | HTTPS-only cookies | **HIGH** - Prevents cookie theft |
| `TALISMAN_FORCE_HTTPS=true` | Force SSL | **HIGH** - Encrypts all traffic |

### Optional Features

| Setting | Description | Default |
|---------|-------------|---------|
| `OPENROUTER_API_KEY` | AI recipe suggestions | Disabled |
| `MAIL_*` | Password reset emails | Disabled |
| `DATABASE_URL` | Database connection | SQLite |

### Getting API Keys

**OpenRouter (for AI recipe suggestions):**
1. Visit https://openrouter.ai/
2. Create account and get API key
3. Add credit to your account (~$5 for thousands of recipes)
4. Set `OPENROUTER_API_KEY` in your environment

**Barcode Lookup (for ingredient scanning):**
1. Visit https://www.barcodelookup.com/api
2. Get free API key (1000 requests/month)
3. Set `BARCODE_LOOKUP_API_KEY` in your environment

---

## 📈 Monitoring & Maintenance

### Azure Monitoring
```bash
# View application performance
az monitor app-insights component show --app your-smartfridge-app --resource-group SmartFridge-RG

# Set up alerts for downtime
az monitor activity-log alert create --name "SmartFridge Down" --resource-group SmartFridge-RG
```

### Regular Maintenance Tasks
- **Weekly:** Check application logs for errors
- **Monthly:** Review user accounts and remove inactive ones
- **Quarterly:** Update Python dependencies for security patches
- **As needed:** Backup recipe and user data

### Performance Optimization
```bash
# For high traffic, upgrade Azure tier
az appservice plan update --name SmartFridge-Plan --resource-group SmartFridge-RG --sku S1

# Monitor database size (SQLite has limits)
# Consider upgrading to PostgreSQL for >1000 users
```

---

## 🎯 Quick Start Summary

**For immediate internet deployment:**

1. **Azure (Recommended - 15 minutes):**
   ```bash
   az group create --name SmartFridge-RG --location "UK South"
   az appservice plan create --name SmartFridge-Plan --resource-group SmartFridge-RG --sku B1 --is-linux
   az webapp create --resource-group SmartFridge-RG --plan SmartFridge-Plan --name your-smartfridge-app --runtime "PYTHON|3.11"
   # Follow Azure deployment steps above
   ```

2. **VPS (Advanced users - 2 hours):**
   ```bash
   # Follow Linux VPS deployment steps above
   # Requires domain, SSL setup, and server hardening
   ```

**Your SmartFridge app will be live and secure! 🚀**

**OpenRouter (for AI recipes):**
1. Visit https://openrouter.ai/
2. Create account and get API key
3. Add to `.env`: `OPENROUTER_API_KEY=your-key`

**Gmail (for password reset emails):**
1. Enable 2FA on your Gmail account
2. Generate an App Password
3. Use App Password (not your regular password) in `.env`

---

## 📋 Basic Usage

### Adding Ingredients
1. Go to "My Fridge"
2. Click "Add Ingredient"
3. Enter name, quantity, and expiry date
4. Or use the barcode scanner! 📷

### Getting Recipe Suggestions
1. Go to "My Fridge"
2. Click "Get Recipe Suggestions"
3. The AI will suggest recipes using only your available ingredients

### Managing Users (Admin)
Control who can access your internet-deployed app:
1. Go to "Admin" → "Manage Users"
2. Approve new users (they can't login until approved)
3. Grant admin access to trusted family/friends
4. Remove access if needed

---

## 📋 Managing Your Internet-Deployed App

### User Management
As admin, you control who can access your app:
1. Users register but cannot login until approved
2. Go to Admin → Manage Users
3. Approve trusted users
4. Grant admin access to family/trusted friends

### Monitoring & Maintenance
```bash
# Check app status
sudo systemctl status Web

# View app logs
sudo journalctl -u Web -f

# Restart if needed
sudo systemctl restart Web nginx

# SSL certificate renewal (automatic, but to check)
sudo certbot renew --dry-run
```

### Backup Your Data
```bash
# Backup database
cp app.db app.db.backup.$(date +%Y%m%d)

# Backup uploaded files (if any)
tar -czf uploads.backup.$(date +%Y%m%d).tar.gz app/static/uploads/
```

---

## 🛠️ Local Development (Optional)

If you want to develop features locally before deploying:

### Quick Local Setup
```bash
git clone https://github.com/Birty96/WebV2.git
cd WebV2
cp .env.example .env
python generate_secret_key.py
# Copy the generated key to .env
python setup_and_run.py
```

Access at http://localhost:5000

### Development vs Production
| Feature | Development | Production |
|---------|-------------|------------|
| HTTPS | Optional | **Required** |
| Debug Mode | Enabled | **Disabled** |
| User Approval | Optional | **Required** |
| Error Pages | Detailed | Generic |
| Session Security | Relaxed | **Strict** |

---

## 🔍 Troubleshooting Internet Deployment

### Azure App Service Issues

**Deployment fails:**
```bash
# Check deployment logs
az webapp log tail --resource-group SmartFridge-RG --name your-smartfridge-app

# View application logs
az webapp log show --resource-group SmartFridge-RG --name your-smartfridge-app
```

**App won't start:**
```bash
# Check if environment variables are set
az webapp config appsettings list --resource-group SmartFridge-RG --name your-smartfridge-app

# Restart the app
az webapp restart --resource-group SmartFridge-RG --name your-smartfridge-app
```

**Database issues on Azure:**
```bash
# If using SQLite, create the database file
az webapp ssh --resource-group SmartFridge-RG --name your-smartfridge-app
cd /home/site/wwwroot
python -m flask db upgrade
```

### VPS/Linux Server Issues

**Domain/DNS Issues**
**"Site can't be reached"**
- Verify DNS records point to your server IP
- Check domain propagation: `nslookup yourdomain.com`
- Ensure ports 80/443 are open in your cloud provider's firewall

### SSL Certificate Issues
**"Not secure" warning in browser**
```bash
# Check certificate status
sudo certbot certificates

# Manual renewal if needed
sudo certbot renew

# Check Nginx configuration
sudo nginx -t
```

### Application Errors
**500 Internal Server Error**
```bash
# Check detailed logs
sudo journalctl -u Web -f

# Common fixes
sudo systemctl restart Web
sudo systemctl restart nginx
```

**Database locked errors**
```bash
# If using SQLite and getting locks
sudo chown -R www-data:www-data /path/to/your/app/
sudo chmod 664 app.db
```

### Performance Issues
**Slow loading**
- Consider upgrading to PostgreSQL for better performance
- Monitor resource usage: `htop`
- Check if you need more server resources

---

## 🔐 Security Best Practices for Internet Deployment

### Essential Security Checklist
- [ ] **SECRET_KEY** is cryptographically secure (64+ characters)
- [ ] **HTTPS** is enforced (check the padlock in browser)
- [ ] **User approval** is enabled (prevents unauthorized access)
- [ ] **Firewall** is configured (UFW enabled)
- [ ] **Regular updates** scheduled (`sudo apt update && sudo apt upgrade`)
- [ ] **Strong admin password** set
- [ ] **Backup strategy** in place

### Regular Maintenance
```bash
# Monthly security updates
sudo apt update && sudo apt upgrade -y

# Check for failed login attempts
sudo grep "Failed password" /var/log/auth.log

# Monitor disk space
df -h

# Check SSL certificate expiry
sudo certbot certificates
```

---

## 📞 Getting Help

**For deployment issues:**
- Check the logs: `sudo journalctl -u Web -f`
- Verify DNS settings
- Ensure `.env` file has no placeholder values

**For application issues:**
- Check user is approved in Admin panel
- Verify API keys if using optional features
- Test with a fresh browser/incognito mode

**Security concerns:**
- Monitor logs for suspicious activity
- Keep system updated
- Use strong passwords
- Limit admin access to trusted users only

---

*🌐 Deployed securely on the internet for remote access by family and friends!*

---

## 🛠️ Development

### Running in Development Mode
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Run the app
flask run
```

### Making Database Changes
```bash
# Create migration
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade
```

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest
```

---

## 🔍 Troubleshooting

### Common Issues

**"Secret key not set" error**
- Make sure you've copied the generated SECRET_KEY to your `.env` file
- Run `python generate_secret_key.py` to get a new key

**"No such file or directory: .env"**
- Copy the example file: `cp .env.example .env`

**Recipe suggestions not working**
- Get an OpenRouter API key from https://openrouter.ai/
- Add it to your `.env` file as `OPENROUTER_API_KEY=your-key`

**500 Internal Server Error**
- Check the terminal/logs for detailed error messages
- Make sure all required environment variables are set

### Getting Help

**Development Mode:**
- Check the terminal output for error messages
- Flask shows detailed error pages in debug mode

**Production Mode:**
- Check logs: `sudo journalctl -u your-service-name -f`
- Check Nginx logs: `sudo tail -f /var/log/nginx/error.log`

---

## 📁 Project Structure

```
SmartFridge/
├── app/                    # Main application
│   ├── auth/              # User authentication
│   ├── fridge/            # Ingredient management
│   ├── templates/         # HTML templates
│   ├── static/            # CSS, JS, images
│   └── models.py          # Database models
├── migrations/            # Database migrations
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── setup_and_run.py     # Easy setup script
└── .env.example         # Environment variables template
```

---

## 🔒 Security Notes

- Always use HTTPS in production
- Keep your SECRET_KEY secure and never commit it to version control
- Regularly update dependencies
- Use strong passwords for admin accounts
- The app includes built-in security features:
  - CSRF protection
  - Secure session cookies
  - Password complexity requirements
  - Account lockout after failed attempts

---

## 📄 License

This project is open source. Feel free to use and modify for your needs!

---

## 🤝 Contributing

Found a bug or want to add a feature? 
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

*Made with ❤️ for home cooks who want to make the most of their ingredients!*
