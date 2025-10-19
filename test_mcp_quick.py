"""
Quick MCP Tool Test - Test subset of models for faster results
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from test_mcp_inspect import MCPToolTester

# Quick test with your selected models (7 models - added GPT-4o)
QUICK_TEST_MODELS = [
    "anthropic/claude-sonnet-4",
    "openai/gpt-4o",
    "openai/gpt-4.1",
    "openai/gpt-oss-120b",
    "qwen/qwen3-30b-a3b",
    "qwen/qwen3-30b-a3b-thinking-2507",
    "deepseek/deepseek-chat-v3.1",
]

async def main():
    """Quick test run"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY environment variable not set")
        print("   Run: export OPENROUTER_API_KEY='your-key-here'")
        return
    
    tester = MCPToolTester(api_key)
    
    # Override models list
    import test_mcp_inspect
    test_mcp_inspect.MODELS_TO_TEST = QUICK_TEST_MODELS
    
    await tester.run_all_tests()
    
    print("\n✅ Quick test completed!")

if __name__ == "__main__":
    asyncio.run(main())
