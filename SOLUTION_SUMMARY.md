# Shiny Chat App with MCP Tools - Summary

## 🎯 What We Built

A Shiny for Python chat application that uses **Claude 3.5 Sonnet** (via OpenRouter) with **MCP (Model Context Protocol) tools** to fetch and visualize sales data.

## 🔍 The Problem We Discovered

**MCP tools are broken with Google Gemini in chatlas 0.13.2**

### Evidence:
1. **Direct testing** showed Gemini literally can't see MCP-registered tools
2. Gemini reports tools as `_call()` instead of their actual names
3. Tested across **all Gemini models** (2.5 Pro, 2.5 Flash, 2.0 Flash) - all failed
4. Even tools with **NO parameters** failed - proving it's not parameter-specific

### Root Cause:
chatlas's Google Gemini provider doesn't properly translate MCP tool schemas to Gemini's API format. The tools register internally but Gemini's API never receives them correctly.

## ✅ The Solution

**Use Claude 3.5 Sonnet via OpenRouter instead of direct Gemini**

### Why This Works:
- ✅ Claude, GPT-4o, and Llama all work perfectly with MCP tools
- ✅ Same MCP server code works flawlessly
- ✅ Tools are properly exposed with all parameters
- ✅ OpenRouter provides access to multiple models

## 📁 Files Created

### Test Files (for debugging):
- `test_mcp_gemini.py` - Comprehensive test suite proving the Gemini bug
- `test_gemini_2_5.py` - Tests with Gemini 2.5 models
- `test_args_vs_no_args.py` - Proves bug isn't parameter-specific
- `test_openrouter_mcp.py` - Shows MCP works with other models
- `mcp_sales_server_no_args.py` - Tool with no parameters for testing

### Production Files:
- `app.py` - Updated Shiny app using Claude via OpenRouter
- `mcp_sales_server.py` - FastMCP server providing sales data tool

## 🚀 How to Use

1. **Start the app:**
   ```bash
   shiny run app.py --reload
   ```

2. **Access the app:**
   Open http://127.0.0.1:8000 in your browser

3. **Try it out:**
   - Type: "Show me sales data for 3 products"
   - Claude will call the `get_sales_data` MCP tool
   - You'll see the text response AND a Plotly chart!

## 📊 Features

- **MCP Tool Integration**: Sales data tool via Model Context Protocol
- **Dynamic Charting**: Automatically creates Plotly charts from sales data
- **Claude 3.5 Sonnet**: Superior reasoning and tool calling via OpenRouter
- **Chat Interface**: Clean Shiny chat UI with message history
- **Real-time Stats**: Message count and timestamps

## 🔧 Technical Details

### MCP Tool:
```python
def get_sales_data(num_products: int = 5) -> str:
    """Get random sales data for products"""
    # Generates random sales data
    # Returns JSON with Product names and Sales figures
```

### Chart Generation:
When sales data is detected in the response:
1. Parse JSON from tool result
2. Create pandas DataFrame
3. Generate Plotly bar chart
4. Inject into chat as widget

### API Keys:
- **OpenRouter**: Configured in code
- **Model**: `anthropic/claude-3.5-sonnet`

## 📈 Test Results

| Model | Direct Tool | MCP Tool | Status |
|-------|-------------|----------|--------|
| Claude 3.5 Sonnet | ✅ | ✅ | **WORKS** |
| GPT-4o | ✅ | ✅ | **WORKS** |
| Llama 3.3 70B | ✅ | ✅ | **WORKS** |
| Gemini 2.5 Pro | ✅ | ❌ | **BROKEN** |
| Gemini 2.5 Flash | ✅ | ❌ | **BROKEN** |
| Gemini 2.0 Flash | ✅ | ❌ | **BROKEN** |

## 🐛 Bug Report for chatlas

**Issue**: MCP tools registered via `register_mcp_tools_stdio_async()` are not properly exposed to Google Gemini's API

**Symptoms**:
- Tools register successfully (visible in `llm.get_tools()`)
- Tool schemas are correct
- Gemini claims tools don't exist or are named `_call()`

**Affects**: All Google Gemini models (2.0 and 2.5 series)

**Workaround**: Use Claude, GPT-4o, or Llama via OpenRouter

## 📚 Key Learnings

1. **MCP tools work** - the protocol is sound
2. **Provider-specific bugs exist** - not all LLM integrations are equal
3. **OpenRouter is reliable** - consistent behavior across models
4. **Testing is crucial** - standalone tests isolated the bug
5. **Claude is excellent** - superior tool calling and reasoning

## 🎓 Next Steps

- Monitor chatlas GitHub for Gemini MCP fix
- Consider filing detailed bug report with evidence
- Explore other MCP tools for the app
- Add more chart types (pie, line, etc.)
