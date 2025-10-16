#!/bin/bash

# Start the frontend development server

echo "=========================================="
echo "Starting Mercedes Scientific Search UI"
echo "=========================================="
echo ""

# Navigate to frontend directory
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

echo "🚀 Starting development server..."
echo ""
echo "Frontend will be available at: http://localhost:5173"
echo "Make sure the API is running at: http://localhost:5001"
echo ""
echo "Press CTRL+C to stop"
echo "=========================================="
echo ""

# Start the dev server
npm run dev
