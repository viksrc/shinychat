#!/bin/zsh

# Startup script for Shiny Chat with MCP
# Sets environment variables and starts the app

# Activate virtual environment
source .venv/bin/activate

# Load .env file if present (simple parser)
if [ -f ".env" ]; then
	echo "🔁 Found .env file, loading environment variables from .env"
	# shellcheck disable=SC2046
	set -o allexport
	# shellcheck disable=SC1091
	source .env
	set +o allexport
fi

# Require OPENROUTER_API_KEY to be set in the environment
if [ -z "$OPENROUTER_API_KEY" ]; then
	echo "❌ OPENROUTER_API_KEY not set!"
	echo "   Please run: export OPENROUTER_API_KEY='your-openrouter-key'"
	echo "   Or add OPENROUTER_API_KEY=your-openrouter-key to a .env file in the repo root"
	exit 1
fi

# Kill any existing Shiny processes
pkill -9 -f "shiny run" 2>/dev/null || true

# Wait a moment for cleanup
sleep 1

# Start the Shiny app
echo "🚀 Starting Shiny Chat with MCP..."
shiny run app/app.py --reload
