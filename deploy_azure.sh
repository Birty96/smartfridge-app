#!/bin/bash

# Simplified Azure App Service deployment script
set -e

echo "🚀 Azure App Service Deployment for SmartFridge Flask App"
echo "========================================================"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo "🔑 Please login to Azure first:"
    az login
fi

# Get deployment details
read -p "📝 Resource Group name: " RESOURCE_GROUP
read -p "📝 App Service name: " APP_NAME
read -p "📝 Azure SQL connection string (optional, press Enter to skip): " DATABASE_URL

if [ -z "$RESOURCE_GROUP" ] || [ -z "$APP_NAME" ]; then
    echo "❌ Resource Group and App Service name are required"
    exit 1
fi

echo "⚙️  Configuring App Service..."

# Essential app settings
az webapp config appsettings set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_NAME" \
    --settings \
        FLASK_ENV=production \
        FLASK_APP=run.py \
        SCM_DO_BUILD_DURING_DEPLOYMENT=true \
        ENABLE_ORYX_BUILD=true

# Set database if provided
if [ ! -z "$DATABASE_URL" ]; then
    echo "🗄️  Setting database connection..."
    az webapp config appsettings set \
        --resource-group "$RESOURCE_GROUP" \
        --name "$APP_NAME" \
        --settings DATABASE_URL="$DATABASE_URL"
fi

# Configure runtime and startup
echo "🐍 Configuring Python runtime..."
az webapp config set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_NAME" \
    --linux-fx-version "PYTHON|3.11" \
    --startup-file "gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 120 run:app"

# Enable logging
az webapp log config \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_NAME" \
    --application-logging filesystem

echo "🚀 Deploying application..."
az webapp up \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_NAME" \
    --sku B1

echo "✅ Deployment completed!"
echo "🌐 App URL: https://${APP_NAME}.azurewebsites.net"
echo "📊 View logs: az webapp log tail --resource-group ${RESOURCE_GROUP} --name ${APP_NAME}"