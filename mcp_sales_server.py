"""
MCP Server for Sales Data
Provides sales data as a pandas DataFrame using FastMCP
"""
import random
import pandas as pd
from mcp.server.fastmcp import FastMCP
from typing import Annotated

# Create FastMCP server
app = FastMCP("sales-data-server")

@app.tool()
def get_sales_data(
    num_products: Annotated[int, "Number of products to generate sales data for"] = 5
) -> str:
    """Get random sales data for products. Returns sales figures with product names and values.
    
    Args:
        num_products: Number of products to generate data for (default: 5)
    
    Returns:
        JSON string containing sales data with Product names and Sales figures
    """
    # Generate random sales data
    products = [f"Product {chr(65+i)}" for i in range(num_products)]
    sales = [random.randint(10, 100) for _ in range(num_products)]
    
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
