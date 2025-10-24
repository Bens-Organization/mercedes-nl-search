#!/bin/bash

# Deploy OpenAI Middleware to Railway
# This script automates the Railway deployment process

set -e  # Exit on error

echo "======================================================"
echo "Railway Middleware Deployment"
echo "======================================================"
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found!"
    echo ""
    echo "Please install Railway CLI first:"
    echo "  npm install -g @railway/cli"
    echo ""
    exit 1
fi

# Check if logged in to Railway
if ! railway whoami &> /dev/null; then
    echo "❌ Not logged in to Railway!"
    echo ""
    echo "Please login first:"
    echo "  railway login"
    echo ""
    exit 1
fi

echo "✅ Railway CLI is installed and authenticated"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with required variables first."
    exit 1
fi

# Load environment variables
source .env

# Validate required environment variables
REQUIRED_VARS=(
    "OPENAI_API_KEY"
    "TYPESENSE_API_KEY"
    "TYPESENSE_HOST"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required environment variable: $var"
        exit 1
    fi
done

echo "✅ All required environment variables found"
echo ""

# Ask user if they want to create a new project or use existing
echo "Do you want to:"
echo "  1) Create a new Railway project"
echo "  2) Deploy to existing Railway project"
read -p "Enter choice (1 or 2): " choice

if [ "$choice" == "1" ]; then
    echo ""
    echo "Creating new Railway project..."
    railway init
elif [ "$choice" == "2" ]; then
    echo ""
    echo "Using existing Railway project"
    echo "Make sure you're in the correct project directory!"
else
    echo "Invalid choice. Exiting."
    exit 1
fi

echo ""
echo "Setting environment variables in Railway..."

# Set environment variables in Railway
railway variables set OPENAI_API_KEY="$OPENAI_API_KEY"
railway variables set TYPESENSE_API_KEY="$TYPESENSE_API_KEY"
railway variables set TYPESENSE_HOST="$TYPESENSE_HOST"
railway variables set TYPESENSE_PORT="${TYPESENSE_PORT:-443}"
railway variables set TYPESENSE_PROTOCOL="${TYPESENSE_PROTOCOL:-https}"
railway variables set FLASK_ENV="production"

echo "✅ Environment variables set"
echo ""

# Deploy to Railway
echo "Deploying to Railway..."
echo "This may take 2-5 minutes..."
echo ""

railway up

echo ""
echo "✅ Deployment complete!"
echo ""

# Get the deployment URL
echo "Getting deployment URL..."
RAILWAY_URL=$(railway domain 2>&1 | grep -o 'https://[^ ]*' || echo "")

if [ -z "$RAILWAY_URL" ]; then
    echo "⚠️  Could not automatically detect Railway URL"
    echo ""
    echo "Please get your URL manually:"
    echo "  railway domain"
    echo ""
    echo "Then update Typesense with:"
    echo "  ./venv/bin/python src/setup_middleware_model.py update YOUR_RAILWAY_URL"
else
    echo "✅ Railway URL: $RAILWAY_URL"
    echo ""

    # Ask if user wants to update Typesense automatically
    read -p "Update Typesense to use this Railway URL? (y/n): " update_typesense

    if [ "$update_typesense" == "y" ] || [ "$update_typesense" == "Y" ]; then
        echo ""
        echo "Updating Typesense model registration..."
        ./venv/bin/python src/setup_middleware_model.py update "$RAILWAY_URL"
        echo ""
        echo "✅ Typesense updated!"
    else
        echo ""
        echo "⚠️  Remember to update Typesense manually:"
        echo "  ./venv/bin/python src/setup_middleware_model.py update $RAILWAY_URL"
    fi
fi

echo ""
echo "======================================================"
echo "Deployment Complete!"
echo "======================================================"
echo ""
echo "Next steps:"
echo "  1. Test middleware health:"
echo "     curl $RAILWAY_URL/health"
echo ""
echo "  2. Test end-to-end search:"
echo "     curl -X POST https://mercedes-search-api-staging.onrender.com/api/search \\"
echo "       -H \"Content-Type: application/json\" \\"
echo "       -d '{\"query\": \"gloves\"}'"
echo ""
echo "  3. Monitor performance in Railway dashboard:"
echo "     railway open"
echo ""
