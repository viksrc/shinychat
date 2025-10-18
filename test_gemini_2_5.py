#!/usr/bin/env python3
"""
Test MCP tool calling with Gemini 2.5 models
"""
import os
import sys
import asyncio
import json
from pathlib import Path
from chatlas import ChatGoogle

# Set API key
os.environ["GOOGLE_API_KEY"] = "AIzaSyCHLcitJnDUx2pC-inPwkv-_mMyQZ1E_bw"


async def test_model(model_name: str):
    """Test MCP tools with a specific Gemini model"""
    print("\n" + "="*70)
    print(f"  Testing: {model_name}")
    print("="*70 + "\n")
    
    try:
        llm = ChatGoogle(
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
            print(json.dumps(tools[0].schema, indent=2))
        
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
            return False
            
    except Exception as e:
        print(f"❌ {model_name}: Error - {e}")
        return False


async def main():
    """Test multiple Gemini 2.5 models"""
    print("\n" + "🧪 Testing MCP Tools with Gemini 2.5 Series".center(70))
    
    models_to_test = [
        "gemini-2.5-pro",           # Most advanced
        "gemini-2.5-flash",         # Fast and capable
        "gemini-2.0-flash-exp",     # Original test model for comparison
    ]
    
    results = {}
    
    for model in models_to_test:
        results[model] = await test_model(model)
    
    # Summary
    print("\n" + "="*70)
    print("  SUMMARY")
    print("="*70 + "\n")
    
    for model, success in results.items():
        status = "✅ WORKS" if success else "❌ BROKEN"
        print(f"{model:35} {status}")
    
    if not any(results.values()):
        print("\n⚠️  CONCLUSION: MCP tools don't work with ANY Gemini model tested!")
        print("This confirms it's a chatlas + Gemini + MCP integration bug.")
    elif all(results.values()):
        print("\n✅ CONCLUSION: MCP tools work with all Gemini models!")
    else:
        working = [m for m, r in results.items() if r]
        broken = [m for m, r in results.items() if not r]
        print(f"\n⚠️  CONCLUSION: Works with {working} but NOT with {broken}")


if __name__ == "__main__":
    asyncio.run(main())
