#!/bin/bash

# Start local development environment (100% FREE!)

echo "=========================================="
echo "Starting Local Development Environment"
echo "=========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

echo "✓ Docker is running"

# Start Typesense with Docker Compose
echo -e "\n1. Starting Typesense..."
docker-compose up -d

# Wait for Typesense to be ready
echo -e "\n2. Waiting for Typesense to be ready..."
sleep 3

# Check if Typesense is healthy
if curl -s http://localhost:8108/health > /dev/null; then
    echo "✓ Typesense is running at http://localhost:8108"
else
    echo "❌ Typesense failed to start"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ Local Environment Ready!"
echo "=========================================="
echo ""
echo "Services running:"
echo "  • Typesense: http://localhost:8108"
echo "  • API Key: mercedes-dev-key-123"
echo ""
echo "Next steps:"
echo "  1. Copy .env.local to .env"
echo "     cp .env.local .env"
echo ""
echo "  2. Add your OpenAI API key to .env"
echo ""
echo "  3. Activate virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  4. Index products:"
echo "     python src/indexer.py"
echo ""
echo "  5. Start API server:"
echo "     python src/app.py"
echo ""
echo "To stop Typesense:"
echo "  docker-compose down"
echo ""
