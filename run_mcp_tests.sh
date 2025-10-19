#!/bin/bash

# Demo script to run MCP tests with proper environment setup

echo "🧪 MCP Tool Testing Framework Demo"
echo "===================================="
echo ""

# Check if API key is set
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ OPENROUTER_API_KEY not set!"
    echo "   Please run: export OPENROUTER_API_KEY='your-key-here'"
    exit 1
fi

echo "✅ API key is set"
echo ""

# Activate virtual environment
source .venv/bin/activate

echo "🚀 Starting quick test (3 models)..."
echo "   This will take approximately 2-3 minutes"
echo ""

# Run quick test
python test_mcp_quick.py

echo ""
echo "📊 Test complete! Check mcp_test_results.json for detailed results"
echo ""
echo "To run full test suite (all 8 models):"
echo "   python test_mcp_inspect.py"
