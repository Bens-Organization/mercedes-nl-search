#!/bin/bash
# use-staging.sh - Switch to staging environment

echo "🔄 Switching to STAGING environment..."
echo ""

if [ ! -f .env.staging ]; then
    echo "❌ Error: .env.staging file not found"
    echo "   Please create .env.staging with your staging credentials"
    echo "   See STAGING.md for details"
    exit 1
fi

cp .env.staging .env

echo "✅ Using staging Typesense cluster"
echo "✅ Environment: STAGING"
echo ""
echo "Current configuration:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep "TYPESENSE_HOST" .env | sed 's/^/  /'
grep "ENVIRONMENT" .env | sed 's/^/  /'
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "You can now run:"
echo "  python src/indexer_neon.py      # Index to staging"
echo "  python src/setup_nl_model.py    # Setup NL model"
echo "  python src/app.py               # Run API server"
echo ""
