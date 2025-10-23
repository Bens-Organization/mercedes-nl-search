#!/bin/bash
# use-production.sh - Switch to production environment

echo "🔄 Switching to PRODUCTION environment..."
echo ""

if [ ! -f .env.production ]; then
    echo "❌ Error: .env.production file not found"
    echo "   Please create .env.production with your production credentials"
    echo "   See DEPLOYMENT.md for details"
    exit 1
fi

cp .env.production .env

echo "✅ Using production Typesense cluster"
echo "✅ Environment: PRODUCTION"
echo ""
echo "⚠️  WARNING: You are now using PRODUCTION environment!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep "TYPESENSE_HOST" .env | sed 's/^/  /'
grep "ENVIRONMENT" .env | sed 's/^/  /'
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "You can now run:"
echo "  python src/indexer_neon.py      # ⚠️  Index to PRODUCTION"
echo "  python src/setup_nl_model.py    # ⚠️  Setup NL model on PRODUCTION"
echo "  python src/app.py               # Run API server"
echo ""
echo "⚠️  Be careful with production data!"
echo ""
