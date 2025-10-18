# MCP Sales Data Server

This MCP server provides sales data as pandas DataFrames.

## Setup

1. Install dependencies:
```bash
pip install mcp pandas
```

2. Run the MCP server:
```bash
python mcp_sales_server.py
```

## Tools Available

### get_sales_data
Returns random sales data for products as a pandas DataFrame.

**Parameters:**
- `num_products` (int, optional): Number of products to generate (default: 5)

**Returns:**
- JSON array of sales data with Product and Sales columns

## Integration with Shiny App

The Shiny app simulates calling this MCP server to get sales data, which is then:
1. Converted to a pandas DataFrame
2. Visualized as an interactive Plotly chart
3. Embedded inline in the chat

## ChatLas Integration

The app uses ChatLas to interface with OpenAI's LLM for:
- Natural conversation responses
- Analysis of sales data
- Context-aware chat interactions

To use ChatLas with OpenAI, set your API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

If no API key is set, the app falls back to simple keyword-based responses.
