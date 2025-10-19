#!/usr/bin/env python3
"""
Test MCP tool calling with OpenRouter
Compare multiple models via OpenRouter
"""
import os
import sys
import asyncio
import json
from pathlib import Path
from chatlas import ChatOpenRouter

# Set OpenRouter API key
os.environ["OPENROUTER_API_KEY"] = "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"


async def test_mcp_with_openrouter(model_name: str):
    """Test MCP tools with OpenRouter model"""
    print("\n" + "="*70)
    print(f"  Testing: {model_name}")
    print("="*70 + "\n")
    
    try:
        llm = ChatOpenRouter(
            model=model_name,
            system_prompt='You are helpful. Use tools when appropriate to answer questions.'
        )
        
        # Register MCP tools
        server_path = str(Path(__file__).with_name("mcp_sales_server.py"))
        await llm.register_mcp_tools_stdio_async(
            command=sys.executable,
            args=['-u', server_path],
            name='sales_mcp',
            include_tools=('get_sales_data',)
        )
        
        tools = llm.get_tools()
        print(f"✓ Registered {len(tools)} tool(s): {[t.name for t in tools]}")
        
        # Print tool schema
        if tools:
            print(f"\n📋 Tool Schema:")
            schema = tools[0].schema
            print(json.dumps(schema, indent=2))
        
        # Test the tool call
        print("\n🤖 Asking: 'Show me sales data for 3 products'\n")
        response = await llm.chat_async("Show me sales data for 3 products")
        content = await response.get_content()
        
        print(f"Response:\n{content}\n")
        
        # Check if tool was called
        if "Product A" in content or "Sales Data" in content:
            print(f"✅ {model_name}: Tool calling WORKS!")
            return True
        else:
            print(f"❌ {model_name}: Tool was NOT called")
            print(f"   Response suggests: {content[:100]}...")
            return False
            
    except Exception as e:
        print(f"❌ {model_name}: Error - {e}")
        import traceback
        print(traceback.format_exc())
        return False


async def test_direct_with_openrouter(model_name: str):
    """Test direct tool registration with OpenRouter (baseline)"""
    print("\n" + "="*70)
    print(f"  BASELINE: Direct Tool with {model_name}")
    print("="*70 + "\n")
    
    def get_sales_data(num_products: int = 5) -> str:
        """Get sales data"""
        import random
        import pandas as pd
        
        products = [f"Product {chr(65+i)}" for i in range(num_products)]
        sales = [random.randint(10, 100) for _ in range(num_products)]
        df = pd.DataFrame({"Product": products, "Sales": sales})
        result = df.to_json(orient="records")
        return f"Sales Data:\n{df.to_string()}\n\nJSON: {result}"
    
    try:
        llm = ChatOpenRouter(
            model=model_name,
            system_prompt='You are helpful. Use tools when appropriate.'
        )
        
        llm.register_tool(get_sales_data)
        
        tools = llm.get_tools()
        print(f"✓ Registered {len(tools)} tool(s): {[t.name for t in tools]}")
        
        print("\n🤖 Asking: 'Show me sales data for 3 products'\n")
        response = await llm.chat_async("Show me sales data for 3 products")
        content = await response.get_content()
        
        print(f"Response:\n{content}\n")
        
        if "Product A" in content or "Sales Data" in content:
            print(f"✅ {model_name}: Direct tool WORKS!")
            return True
        else:
            print(f"❌ {model_name}: Direct tool failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    """Test multiple models via OpenRouter"""
    print("\n" + "🧪 Testing MCP Tools with OpenRouter".center(70))
    
    # Test various models available via OpenRouter (7 models - added GPT-4o)
    models_to_test = [
        "anthropic/claude-sonnet-4",
        "openai/gpt-4o",
        "openai/gpt-4.1",
        "openai/gpt-oss-120b",
        "qwen/qwen3-30b-a3b",
        "qwen/qwen3-30b-a3b-thinking-2507",
        "deepseek/deepseek-chat-v3.1",
    ]
    
    results = {}
    
    # First test direct tool registration with one model as baseline
    print("\n" + "🎯 BASELINE TEST".center(70))
    baseline_model = models_to_test[0]
    results['baseline'] = await test_direct_with_openrouter(baseline_model)
    
    # Test MCP tools with all models
    print("\n" + "🔧 MCP TOOLS TESTS".center(70))
    for model in models_to_test:
        results[model] = await test_mcp_with_openrouter(model)
    
    # Summary
    print("\n" + "="*70)
    print("  SUMMARY")
    print("="*70 + "\n")
    
    print(f"{'Baseline (Direct Tool):':<45} {'✅ WORKS' if results.get('baseline') else '❌ FAILS'}")
    print()
    for model, success in results.items():
        if model != 'baseline':
            status = "✅ WORKS" if success else "❌ BROKEN"
            print(f"{model:<45} {status}")
    
    # Analysis
    print("\n" + "🔍 ANALYSIS".center(70))
    mcp_results = {k: v for k, v in results.items() if k != 'baseline'}
    
    if not any(mcp_results.values()):
        print("❌ MCP tools don't work with ANY model via OpenRouter")
        print("   This suggests a broader MCP issue in chatlas")
    elif all(mcp_results.values()):
        print("✅ MCP tools work with ALL models via OpenRouter!")
        print("   The issue is specific to Google Gemini's direct API")
    else:
        working = [m for m, r in mcp_results.items() if r]
        broken = [m for m, r in mcp_results.items() if not r]
        print(f"⚠️  Mixed results:")
        print(f"   ✅ Working: {', '.join(working)}")
        print(f"   ❌ Broken: {', '.join(broken)}")


if __name__ == "__main__":
    asyncio.run(main())
