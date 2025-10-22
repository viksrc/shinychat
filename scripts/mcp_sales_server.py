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
    region: Annotated[Optional[str], "Region to filter by (e.g., 'North', 'South', 'East', 'West'). If not specified, returns data for all regions"] = None,
    start_date: Annotated[Optional[str], "Start date for the date range in YYYY-MM-DD format. If not specified, returns data from the beginning"] = None,
    end_date: Annotated[Optional[str], "End date for the date range in YYYY-MM-DD format. If not specified, returns data up to today"] = None,
    groupby: Annotated[Optional[str], "Optional grouping: 'region', 'week', 'month', 'quarter', or 'year'. When provided, returns aggregated sales per group."] = None,
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
    # Generate product names (fixed 25 products: Product A..Y)
    num_products = 25
    products = [f"Product {chr(65+i)}" for i in range(num_products)]
    
    # Define regions
    regions = ["North", "South", "East", "West"]
    
    # Generate sales data: for each product, create a sales row for each day in the date range
    data = []

    # Compute date range: if not provided, default to last 30 days
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            start = datetime.now() - timedelta(days=30)
            end = datetime.now()
    elif start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.now()
        except ValueError:
            start = datetime.now() - timedelta(days=30)
            end = datetime.now()
    elif end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            start = end - timedelta(days=30)
        except ValueError:
            start = datetime.now() - timedelta(days=30)
            end = datetime.now()
    else:
        start = datetime.now() - timedelta(days=30)
        end = datetime.now()

    # Normalize to date-only
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = end.replace(hour=0, minute=0, second=0, microsecond=0)

    days = (end - start).days + 1

    for product in products:
        for d in range(days):
            sale_date = start + timedelta(days=d)
            product_region = region if region else random.choice(regions)
            data.append({
                "Product": product,
                "Sales": random.randint(1, 20),
                "Region": product_region,
                "Date": sale_date.strftime("%Y-%m-%d")
            })
    
    # Create DataFrame
    df = pd.DataFrame(data)

    # Ensure Date column is datetime for grouping
    df['Date'] = pd.to_datetime(df['Date'])

    # Apply region filter if provided
    if region:
        df = df[df['Region'] == region]
    
    # Build description
    desc_parts = [f"Sales Data ({num_products} products)"]
    if region:
        desc_parts.append(f"Region: {region}")
    if start_date or end_date:
        date_range = f"Date Range: {start_date or 'beginning'} to {end_date or 'today'}"
        desc_parts.append(date_range)

    description = " | ".join(desc_parts)

    # If grouping requested, aggregate accordingly
    if groupby:
        g = groupby.lower()
        if g == 'region':
            agg = df.groupby('Region', as_index=False)['Sales'].sum().rename(columns={'Sales': 'TotalSales'})
        elif g == 'week':
            # ISO week number (year-week) to avoid collisions across years
            agg = (
                df.assign(Year=df['Date'].dt.isocalendar().year, Week=df['Date'].dt.isocalendar().week)
                  .groupby(['Year', 'Week'], as_index=False)['Sales']
                  .sum()
                  .rename(columns={'Sales': 'TotalSales'})
            )
            agg['Period'] = agg['Year'].astype(str) + '-W' + agg['Week'].astype(str)
            agg = agg[['Period', 'TotalSales']]
        elif g == 'month':
            agg = (
                df.assign(Period=df['Date'].dt.to_period('M').astype(str))
                  .groupby('Period', as_index=False)['Sales']
                  .sum()
                  .rename(columns={'Sales': 'TotalSales'})
            )
        elif g == 'quarter':
            agg = (
                df.assign(Period=df['Date'].dt.to_period('Q').astype(str))
                  .groupby('Period', as_index=False)['Sales']
                  .sum()
                  .rename(columns={'Sales': 'TotalSales'})
            )
        elif g == 'year':
            agg = (
                df.assign(Period=df['Date'].dt.year)
                  .groupby('Period', as_index=False)['Sales']
                  .sum()
                  .rename(columns={'Sales': 'TotalSales'})
            )
        else:
            return f"❌ Invalid groupby value: {groupby}. Valid: region, week, month, quarter, year"

        # Return aggregated JSON and pretty table
        result_json = agg.to_json(orient='records')
        return f"{description} | Grouped by: {groupby}\n\n{agg.to_string(index=False)}\n\nJSON: {result_json}"

    # No grouping: return raw records
    result = df.to_json(orient="records")

    return f"{description}\n\n{df.to_string(index=False)}\n\nJSON: {result}"

if __name__ == "__main__":
    # Run the MCP server on stdio
    app.run(transport="stdio")
