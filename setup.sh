#!/bin/bash

echo "🚀 Setting up Hacker News Semantic Search"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Build the search index: python build_index.py"
echo "2. Start the search server: python search_api.py"
echo "3. Open http://localhost:8000 in your browser"
echo ""
echo "Or use the CLI: python search_cli.py 'your search query'"
