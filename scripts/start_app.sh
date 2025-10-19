#!/bin/zsh

# Startup script for Shiny Chat with MCP
# Sets environment variables and starts the app

# Set OpenRouter API key
export OPENROUTER_API_KEY="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"

# Activate virtual environment
source .venv/bin/activate

# Kill any existing Shiny processes
pkill -9 -f "shiny run" 2>/dev/null || true

# Wait a moment for cleanup
sleep 1

# Start the Shiny app
echo "🚀 Starting Shiny Chat with MCP..."
shiny run app.py --reload
