#!/bin/zsh

# Startup script for Shiny Chat with MCP
# Sets environment variables and starts the app

# Activate virtual environment
source .venv/bin/activate

# Load .env file if present. Support both 'KEY=value' and 'export KEY=value' formats.
if [ -f ".env" ]; then
	echo "🔁 Found .env file, loading environment variables from .env"

	# Prefer a simple parser that will export KEY=VALUE lines.
	# This avoids executing arbitrary code in .env while still supporting common formats.
	while IFS= read -r line; do
		# Skip comments and empty lines
		case "$line" in
			''|\#*) continue ;;
		esac

		# Support both 'KEY=VALUE' and 'export KEY=VALUE'
		# Remove leading 'export ' if present
		cleaned=$(echo "$line" | sed -E 's/^export[[:space:]]+//')

		# Only accept simple KEY=VALUE lines (no command execution)
		if ! echo "$cleaned" | grep -qE '^[A-Za-z_][A-Za-z0-9_]*='; then
			continue
		fi

		key=$(echo "$cleaned" | cut -d '=' -f 1 | tr -d ' \t\r\n')
		val=$(echo "$cleaned" | cut -d '=' -f 2-)
		# Remove surrounding quotes from value if present
		val=$(echo "$val" | sed -e 's/^\s*"//' -e 's/"\s*$//' -e "s/^\s*'//" -e "s/'\s*$//")
		# Export the variable
		export "$key=$val"
	done < <(grep -E "^(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=.*$" .env || true)
fi

# Require OPENROUTER_API_KEY to be set in the environment
if [ -z "$OPENROUTER_API_KEY" ]; then
	echo "❌ OPENROUTER_API_KEY not set!"
	echo "   Please run: export OPENROUTER_API_KEY='your-openrouter-key'"
	echo "   Or add OPENROUTER_API_KEY=your-openrouter-key to a .env file in the repo root"
	exit 1
fi

# For troubleshooting: print a masked preview and a fingerprint (SHA-256) of the key.
# WARNING: this does NOT print the full key. Sharing the hash or a small prefix/suffix
# is safe for debugging but do NOT paste the full key into public channels.
masked_prefix="${OPENROUTER_API_KEY:0:4}"
# Use negative offset for suffix; ensure portability with parameter expansion
masked_suffix="${OPENROUTER_API_KEY: -4}"
key_length=${#OPENROUTER_API_KEY}
echo "🔐 OPENROUTER_API_KEY present (length=${key_length}) — preview: ${masked_prefix}...${masked_suffix}"

# Print a SHA-256 fingerprint so we can compare whether the running process has the same key
# without revealing it. Use Python (available in the venv) to compute the hash.
if command -v python >/dev/null 2>&1; then
    key_hash=$(python -c "import hashlib,sys;print(hashlib.sha256(sys.stdin.read().encode()).hexdigest())" <<< "$OPENROUTER_API_KEY")
    echo "🔎 OPENROUTER_API_KEY SHA256: ${key_hash}"
fi

# Kill any existing Shiny processes
pkill -9 -f "shiny run" 2>/dev/null || true

# Wait a moment for cleanup
sleep 1

# Start the Shiny app
echo "🚀 Starting Shiny Chat with MCP..."
shiny run app/app.py --reload
