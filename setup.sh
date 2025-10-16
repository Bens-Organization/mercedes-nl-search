#!/bin/bash

# Mercedes Scientific Natural Language Search - Setup Script

echo "=========================================="
echo "Mercedes Scientific NL Search - Setup"
echo "=========================================="

# Check Python version
echo -e "\n1. Checking Python version..."
python3 --version

# Create virtual environment
echo -e "\n2. Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo -e "\n3. Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo -e "\n4. Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env from example
if [ ! -f .env ]; then
    echo -e "\n5. Creating .env file..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your API keys:"
    echo "   - OPENAI_API_KEY"
    echo "   - TYPESENSE_API_KEY"
    echo "   - TYPESENSE_HOST"
    echo ""
else
    echo -e "\n5. .env file already exists, skipping..."
fi

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys"
echo "2. Run: source venv/bin/activate"
echo "3. Index products: python src/indexer.py"
echo "4. Start API: python src/app.py"
echo ""
