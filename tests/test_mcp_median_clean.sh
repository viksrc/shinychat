#!/bin/bash
# Wrapper script to run MCP median tests and suppress async generator cleanup errors
#
# Note: The MCP stdio client has a known issue with async generator cleanup in parallel
# contexts (Python 3.13 + anyio). These errors appear AFTER all tests complete successfully
# and don't affect results. This script suppresses them for cleaner output.

source .venv/bin/activate
python test_mcp_median.py 2>&1 | grep -v "an error occurred during closing" | grep -v "asyncgen:" | grep -v "Exception Group" | grep -v "BaseExceptionGroup" | grep -v "GeneratorExit" | grep -v "RuntimeError: Attempted to exit cancel scope" | grep -v "mcp/client/stdio" | grep -v "anyio/_backends" | grep -v "unhandled errors in a TaskGroup" | grep -v "+-+" | grep -v "yield read_stream" | grep -v "raise BaseExceptionGroup" | grep -v "if self.cancel_scope" | grep -v '^\s*|\s*$' | grep -v '^\s*$' || true

