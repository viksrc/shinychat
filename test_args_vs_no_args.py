#!/usr/bin/env python3
"""
Test MCP tool calling with NO arguments vs WITH arguments
to isolate if the bug is parameter-specific
"""
import os
import sys
import asyncio
import json
from pathlib import Path
from chatlas import ChatGoogle

# Set API key
os.environ["GOOGLE_API_KEY"] = "AIzaSyCHLcitJnDUx2pC-inPwkv-_mMyQZ1E_bw"


async def test_no_args():
    """Test MCP tool with NO parameters"""
    print("\n" + "="*70)
    print("  TEST 1: MCP Tool with NO Arguments")
    print("="*70 + "\n")
    
    llm = ChatGoogle(
        model='gemini-2.5-flash',
        system_prompt='You are helpful. Use tools when appropriate.'
    )
    
    # Register MCP tool WITHOUT arguments
    server_path = str(Path(__file__).with_name("mcp_sales_server_no_args.py"))
    await llm.register_mcp_tools_stdio_async(
        command=sys.executable,
        args=['-u', server_path],
        name='sales_mcp',
        include_tools=('get_sales_data',)
    )
    
    tools = llm.get_tools()
    print(f"✓ Registered {len(tools)} tool(s): {[t.name for t in tools]}")
    
    # Print tool schema
    print(f"\n📋 Tool Schema:")
    print(json.dumps(tools[0].schema, indent=2))
    
    # Test the tool call
    print("\n🤖 Asking: 'Show me sales data'\n")
    response = await llm.chat_async("Show me sales data")
    content = await response.get_content()
    
    print(f"Response:\n{content}\n")
    
    # Check if tool was called
    if "Product A" in content or "Sales Data" in content:
        print("✅ SUCCESS: Tool with NO args was called!")
        return True
    else:
        print("❌ FAILED: Tool with NO args was NOT called")
        return False


async def test_with_args():
    """Test MCP tool WITH parameters"""
    print("\n" + "="*70)
    print("  TEST 2: MCP Tool WITH Arguments")
    print("="*70 + "\n")
    
    llm = ChatGoogle(
        model='gemini-2.5-flash',
        system_prompt='You are helpful. Use tools when appropriate.'
    )
    
    # Register MCP tool WITH arguments
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
    print(f"\n📋 Tool Schema:")
    print(json.dumps(tools[0].schema, indent=2))
    
    # Test the tool call
    print("\n🤖 Asking: 'Show me sales data for 3 products'\n")
    response = await llm.chat_async("Show me sales data for 3 products")
    content = await response.get_content()
    
    print(f"Response:\n{content}\n")
    
    # Check if tool was called
    if "Product A" in content or "Sales Data" in content:
        print("✅ SUCCESS: Tool with args was called!")
        return True
    else:
        print("❌ FAILED: Tool with args was NOT called")
        return False


async def test_direct_no_args():
    """Test direct tool registration with NO parameters"""
    print("\n" + "="*70)
    print("  TEST 3: Direct Tool with NO Arguments (Baseline)")
    print("="*70 + "\n")
    
    def get_sales_data_direct() -> str:
        """Get sales data directly"""
        import random
        import pandas as pd
        
        products = [f"Product {chr(65+i)}" for i in range(5)]
        sales = [random.randint(10, 100) for _ in range(5)]
        df = pd.DataFrame({"Product": products, "Sales": sales})
        result = df.to_json(orient="records")
        return f"Sales Data:\n{df.to_string()}\n\nJSON: {result}"
    
    llm = ChatGoogle(
        model='gemini-2.5-flash',
        system_prompt='You are helpful. Use tools when appropriate.'
    )
    
    llm.register_tool(get_sales_data_direct)
    
    tools = llm.get_tools()
    print(f"✓ Registered {len(tools)} tool(s): {[t.name for t in tools]}")
    
    # Print tool schema
    print(f"\n📋 Tool Schema:")
    print(json.dumps(tools[0].schema, indent=2))
    
    # Test the tool call
    print("\n🤖 Asking: 'Show me sales data'\n")
    response = await llm.chat_async("Show me sales data")
    content = await response.get_content()
    
    print(f"Response:\n{content}\n")
    
    # Check if tool was called
    if "Product A" in content or "Sales Data" in content:
        print("✅ SUCCESS: Direct tool with NO args was called!")
        return True
    else:
        print("❌ FAILED: Direct tool with NO args was NOT called")
        return False


async def main():
    """Run all tests"""
    print("\n" + "🧪 Testing: Arguments vs No Arguments".center(70))
    
    results = {}
    
    # Test direct tool without args (baseline)
    try:
        results['direct_no_args'] = await test_direct_no_args()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        results['direct_no_args'] = False
    
    # Test MCP tool without args
    try:
        results['mcp_no_args'] = await test_no_args()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        results['mcp_no_args'] = False
    
    # Test MCP tool with args
    try:
        results['mcp_with_args'] = await test_with_args()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        results['mcp_with_args'] = False
    
    # Summary
    print("\n" + "="*70)
    print("  SUMMARY")
    print("="*70 + "\n")
    
    print(f"Direct tool (no args):  {'✅ WORKS' if results.get('direct_no_args') else '❌ FAILS'}")
    print(f"MCP tool (no args):     {'✅ WORKS' if results.get('mcp_no_args') else '❌ FAILS'}")
    print(f"MCP tool (with args):   {'✅ WORKS' if results.get('mcp_with_args') else '❌ FAILS'}")
    
    print("\n" + "🔍 ANALYSIS".center(70))
    if results.get('direct_no_args') and not results.get('mcp_no_args'):
        print("Even tools with NO arguments fail with MCP!")
        print("→ The bug is NOT parameter-specific")
        print("→ MCP tools are fundamentally broken with Gemini")
    elif results.get('mcp_no_args') and not results.get('mcp_with_args'):
        print("Tools work WITHOUT parameters but fail WITH parameters")
        print("→ The bug IS parameter-specific")
        print("→ Gemini can't see MCP tool parameters properly")
    elif results.get('mcp_no_args') and results.get('mcp_with_args'):
        print("MCP tools work with AND without parameters!")
        print("→ Something else is wrong in your app")
    else:
        print("Nothing works - fundamental issue")


if __name__ == "__main__":
    asyncio.run(main())
