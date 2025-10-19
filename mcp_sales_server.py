"""
MCP Server for Sales Data
Provides sales data as a pandas DataFrame using FastMCP
"""
import random
import pandas as pd
from mcp.server.fastmcp import FastMCP
from typing import Annotated, Optional
from datetime import datetime, timedelta

# Create FastMCP server
app = FastMCP("sales-data-server")

@app.tool()
def get_current_date() -> str:
    """Get the current date and time. Use this function when you need to know today's date
    to answer questions about relative dates like 'last month', 'this year', 'last week', etc.
    
    Returns:
        Current date and time in ISO format (YYYY-MM-DD HH:MM:SS)
    """
    now = datetime.now()
    return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"

@app.tool()
def get_sales_data(
    num_products: Annotated[int, "Number of products to generate sales data for"] = 5,
    region: Annotated[Optional[str], "Region to filter by (e.g., 'North', 'South', 'East', 'West'). If not specified, returns data for all regions"] = None,
    start_date: Annotated[Optional[str], "Start date for the date range in YYYY-MM-DD format. If not specified, returns data from the beginning"] = None,
    end_date: Annotated[Optional[str], "End date for the date range in YYYY-MM-DD format. If not specified, returns data up to today"] = None
) -> str:
    """Get sales data for products with optional filtering by region and date range.
    
    Args:
        num_products: Number of products to generate data for (default: 5)
        region: Optional region filter ('North', 'South', 'East', 'West')
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
    
    Returns:
        JSON string containing sales data with Product names, Sales figures, Region, and Date
    
    Examples:
        - get_sales_data(num_products=5) - Get 5 products
        - get_sales_data(num_products=10, region="North") - Get 10 products from North region
        - get_sales_data(num_products=5, start_date="2024-01-01", end_date="2024-12-31") - Get data for 2024
    """
    # Generate product names
    products = [f"Product {chr(65+i)}" for i in range(num_products)]
    
    # Define regions
    regions = ["North", "South", "East", "West"]
    
    # Generate random sales data with regions and dates
    data = []
    for product in products:
        # If region is specified, use it; otherwise pick random region
        product_region = region if region else random.choice(regions)
        
        # Generate random date within range
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                # Generate random date between start and end
                days_diff = (end - start).days
                random_days = random.randint(0, max(0, days_diff))
                sale_date = start + timedelta(days=random_days)
            except ValueError:
                # If date parsing fails, use current date
                sale_date = datetime.now()
        elif start_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                # Generate date between start and now
                days_diff = (datetime.now() - start).days
                random_days = random.randint(0, max(0, days_diff))
                sale_date = start + timedelta(days=random_days)
            except ValueError:
                sale_date = datetime.now()
        elif end_date:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d")
                # Generate date up to end date (assume 1 year back)
                start = end - timedelta(days=365)
                days_diff = (end - start).days
                random_days = random.randint(0, max(0, days_diff))
                sale_date = start + timedelta(days=random_days)
            except ValueError:
                sale_date = datetime.now()
        else:
            # Default: random date within last 30 days
            random_days = random.randint(0, 30)
            sale_date = datetime.now() - timedelta(days=random_days)
        
        data.append({
            "Product": product,
            "Sales": random.randint(10, 100),
            "Region": product_region,
            "Date": sale_date.strftime("%Y-%m-%d")
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Build description
    desc_parts = [f"Sales Data ({num_products} products)"]
    if region:
        desc_parts.append(f"Region: {region}")
    if start_date or end_date:
        date_range = f"Date Range: {start_date or 'beginning'} to {end_date or 'today'}"
        desc_parts.append(date_range)
    
    description = " | ".join(desc_parts)
    
    # Return as JSON string
    result = df.to_json(orient="records")
    
    return f"{description}\n\n{df.to_string(index=False)}\n\nJSON: {result}"

if __name__ == "__main__":
    # Run the MCP server on stdio
    app.run(transport="stdio")
