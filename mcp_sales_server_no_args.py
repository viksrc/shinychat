"""
MCP Server for Sales Data - NO ARGUMENTS VERSION
Test if the issue is with parameters
"""
import random
import pandas as pd
from mcp.server.fastmcp import FastMCP

# Create FastMCP server
app = FastMCP("sales-data-server")

@app.tool()
def get_sales_data() -> str:
    """Get random sales data for 5 products. No parameters needed.
    
    Returns:
        Sales data as formatted string with JSON
    """
    # Generate random sales data for 5 products
    products = [f"Product {chr(65+i)}" for i in range(5)]
    sales = [random.randint(10, 100) for _ in range(5)]
    
    # Create DataFrame
    df = pd.DataFrame({
        "Product": products,
        "Sales": sales
    })
    
    # Return as JSON string
    result = df.to_json(orient="records")
    
    return f"Sales Data:\n{df.to_string()}\n\nJSON: {result}"

if __name__ == "__main__":
    # Run the MCP server on stdio
    app.run(transport="stdio")
