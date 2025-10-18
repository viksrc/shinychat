#!/usr/bin/env python3
"""
Standalone test to troubleshoot MCP tool calling with Google Gemini via chatlas.
Tests both direct tool registration and MCP tool registration.
"""
import os
import sys
import asyncio
import json
from pathlib import Path
from chatlas import ChatGoogle

# Set API key
os.environ["GOOGLE_API_KEY"] = "AIzaSyCHLcitJnDUx2pC-inPwkv-_mMyQZ1E_bw"

def print_separator(title):
    """Print a nice separator"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def get_sales_data_direct(num_products: int = 5) -> str:
    """Direct tool implementation (not via MCP)"""
    import random
    import pandas as pd
    
    products = [f"Product {chr(65+i)}" for i in range(num_products)]
    sales = [random.randint(10, 100) for _ in range(num_products)]
    df = pd.DataFrame({"Product": products, "Sales": sales})
    result = df.to_json(orient="records")
    return f"Sales Data:\n{df.to_string()}\n\nJSON: {result}"


async def test_direct_tool_registration():
    """Test 1: Direct tool registration (baseline - should work)"""
    print_separator("TEST 1: Direct Tool Registration (Baseline)")
    
    llm = ChatGoogle(
        model='gemini-2.0-flash-exp',
        system_prompt='You are helpful. Use tools when appropriate.'
    )
    
    # Register tool directly
    llm.register_tool(get_sales_data_direct)
    
    # Check registered tools
    tools = llm.get_tools()
    print(f"✓ Registered {len(tools)} tool(s): {[t.name for t in tools]}")
    
    # Print tool schema
    for tool in tools:
        print(f"\n📋 Tool Schema for '{tool.name}':")
        print(json.dumps(tool.schema, indent=2))
    
    # Test the tool call
    print("\n🤖 Asking: 'Show me sales data for 3 products'\n")
    response = await llm.chat_async("Show me sales data for 3 products")
    content = await response.get_content()
    
    print(f"✓ Response:\n{content}\n")
    return True


async def test_mcp_tool_registration():
    """Test 2: MCP tool registration (the broken one)"""
    print_separator("TEST 2: MCP Tool Registration (Suspected Issue)")
    
    llm = ChatGoogle(
        model='gemini-2.0-flash-exp',
        system_prompt='You are helpful. Use tools when appropriate.'
    )
    
    # Register MCP tools
    server_path = str(Path(__file__).with_name("mcp_sales_server.py"))
    print(f"📂 MCP Server Path: {server_path}")
    
    try:
        await llm.register_mcp_tools_stdio_async(
            command=sys.executable,
            args=['-u', server_path],
            name='sales_mcp',
            include_tools=('get_sales_data',)
        )
        print("✓ MCP tools registered successfully")
    except Exception as e:
        print(f"❌ Failed to register MCP tools: {e}")
        return False
    
    # Check registered tools
    tools = llm.get_tools()
    print(f"✓ Registered {len(tools)} tool(s): {[t.name for t in tools]}")
    
    # Print tool schema
    for tool in tools:
        print(f"\n📋 Tool Schema for '{tool.name}':")
        print(json.dumps(tool.schema, indent=2))
    
    # Test the tool call
    print("\n🤖 Asking: 'Show me sales data for 3 products'\n")
    try:
        response = await llm.chat_async("Show me sales data for 3 products")
        content = await response.get_content()
        print(f"✓ Response:\n{content}\n")
        
        # Check if the tool was actually called
        if "Product A" in content or "Sales Data" in content:
            print("✅ SUCCESS: Tool was called and returned data!")
            return True
        else:
            print("⚠️  WARNING: Tool might not have been called properly")
            print("    Response doesn't contain expected sales data")
            return False
            
    except Exception as e:
        print(f"❌ Error during chat: {e}")
        import traceback
        print(traceback.format_exc())
        return False


async def test_mcp_tool_explicit_call():
    """Test 3: Explicitly ask Gemini to call the MCP tool"""
    print_separator("TEST 3: Explicit Tool Call Request")
    
    llm = ChatGoogle(
        model='gemini-2.0-flash-exp',
        system_prompt='You MUST use the get_sales_data tool when asked about sales.'
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
    
    # Very explicit request
    print("\n🤖 Asking: 'Call the get_sales_data tool with num_products=3'\n")
    try:
        response = await llm.chat_async("Call the get_sales_data tool with num_products=3")
        content = await response.get_content()
        print(f"✓ Response:\n{content}\n")
        
        if "Product A" in content or "Sales Data" in content:
            print("✅ SUCCESS: Tool was called!")
            return True
        else:
            print("⚠️  Tool might not have been called")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_comparison():
    """Test 4: Side-by-side comparison of tool schemas"""
    print_separator("TEST 4: Schema Comparison (Direct vs MCP)")
    
    # Direct tool
    llm_direct = ChatGoogle(model='gemini-2.0-flash-exp')
    llm_direct.register_tool(get_sales_data_direct)
    direct_tools = llm_direct.get_tools()
    
    # MCP tool
    llm_mcp = ChatGoogle(model='gemini-2.0-flash-exp')
    server_path = str(Path(__file__).with_name("mcp_sales_server.py"))
    await llm_mcp.register_mcp_tools_stdio_async(
        command=sys.executable,
        args=['-u', server_path],
        name='sales_mcp',
        include_tools=('get_sales_data',)
    )
    mcp_tools = llm_mcp.get_tools()
    
    print("📋 DIRECT TOOL SCHEMA:")
    print(json.dumps(direct_tools[0].schema, indent=2))
    
    print("\n📋 MCP TOOL SCHEMA:")
    print(json.dumps(mcp_tools[0].schema, indent=2))
    
    # Compare schemas
    print("\n🔍 COMPARISON:")
    direct_params = direct_tools[0].schema.get("function", {}).get("parameters", {})
    mcp_params = mcp_tools[0].schema.get("function", {}).get("parameters", {})
    
    print(f"  Direct tool parameters: {list(direct_params.get('properties', {}).keys())}")
    print(f"  MCP tool parameters: {list(mcp_params.get('properties', {}).keys())}")
    
    if direct_params == mcp_params:
        print("  ✅ Schemas are IDENTICAL")
    else:
        print("  ⚠️  Schemas are DIFFERENT!")
        print("\n  Differences:")
        print(f"    Direct: {direct_params}")
        print(f"    MCP: {mcp_params}")


async def main():
    """Run all tests"""
    print("\n" + "🧪 CHATLAS + GEMINI + MCP TOOL CALLING TEST SUITE".center(70))
    print("Testing if MCP tools work properly with Google Gemini\n")
    
    results = {}
    
    # Test 1: Direct tool (baseline)
    try:
        results['direct'] = await test_direct_tool_registration()
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        results['direct'] = False
    
    # Test 2: MCP tool
    try:
        results['mcp'] = await test_mcp_tool_registration()
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        results['mcp'] = False
    
    # Test 3: Explicit MCP call
    try:
        results['explicit'] = await test_mcp_tool_explicit_call()
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        results['explicit'] = False
    
    # Test 4: Schema comparison
    try:
        await test_comparison()
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
    
    # Summary
    print_separator("TEST SUMMARY")
    print(f"✓ Direct Tool Registration:  {'✅ PASS' if results.get('direct') else '❌ FAIL'}")
    print(f"✓ MCP Tool Registration:      {'✅ PASS' if results.get('mcp') else '❌ FAIL'}")
    print(f"✓ Explicit MCP Tool Call:     {'✅ PASS' if results.get('explicit') else '❌ FAIL'}")
    
    if results.get('direct') and not results.get('mcp'):
        print("\n" + "⚠️  CONCLUSION".center(70))
        print("Direct tool registration works, but MCP tools don't.")
        print("This confirms a bug in chatlas MCP + Gemini integration.")
        print("\nWorkaround: Use direct tool registration instead of MCP.")
    elif results.get('direct') and results.get('mcp'):
        print("\n" + "✅ CONCLUSION".center(70))
        print("Both direct and MCP tools work! The issue might be elsewhere.")
    else:
        print("\n" + "❌ CONCLUSION".center(70))
        print("Something is fundamentally broken. Check API key and network.")


if __name__ == "__main__":
    asyncio.run(main())
