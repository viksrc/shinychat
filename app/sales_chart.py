import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime
from shiny import ui, render
from shinywidgets import output_widget, render_widget


def _log(message: str) -> None:
    """Print log messages with a timestamp prefix."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} {message}")

def create_sales_chart(output, sales_data, chart_counter_value):
    """
    Create and display a sales chart and data table from the provided data
    
    Args:
        sales_data: List of dictionaries containing sales data
        chart_counter_value: Unique counter value for chart IDs
        
    Returns:
        UI element containing the chart and table in a tabbed view
    """
    _log("📊 Detected sales data, creating chart and table...")
    # Create DataFrame
    df = pd.DataFrame(sales_data)
    
    # Create unique IDs (include timestamp to avoid collisions)
    timestamp = int(time.time() * 1000)
    chart_id = f"sales_chart_{chart_counter_value}_{timestamp}"
    table_id = f"sales_table_{chart_counter_value}_{timestamp}"
    
    # Determine columns for plotting. Support both raw product-level data
    # and aggregated outputs (Period/TotalSales, Region/TotalSales, Year, etc.).
    x_col = None
    y_col = None

    if 'Product' in df.columns and 'Sales' in df.columns:
        x_col, y_col = 'Product', 'Sales'
    elif 'Period' in df.columns and 'TotalSales' in df.columns:
        x_col, y_col = 'Period', 'TotalSales'
    elif 'Region' in df.columns and 'TotalSales' in df.columns:
        x_col, y_col = 'Region', 'TotalSales'
    elif 'Sales' in df.columns and len(df.columns) >= 2:
        # pick first non-Sales column as x
        other_cols = [c for c in df.columns if c != 'Sales']
        x_col = other_cols[0] if other_cols else None
        y_col = 'Sales'
    elif 'TotalSales' in df.columns and len(df.columns) >= 2:
        other_cols = [c for c in df.columns if c != 'TotalSales']
        x_col = other_cols[0] if other_cols else None
        y_col = 'TotalSales'
    else:
        # Fallback: try to find any numeric column for y and any other column for x
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if numeric_cols:
            y_col = numeric_cols[0]
            other_cols = [c for c in df.columns if c != y_col]
            x_col = other_cols[0] if other_cols else None

    # Create Plotly bar chart
    if x_col is not None and y_col is not None:
        fig = go.Figure(data=[
            go.Bar(
                x=df[x_col],
                y=df[y_col],
                marker_color='rgb(102, 126, 234)',
                text=df[y_col],
                textposition='auto',
            )
        ])
    else:
        # No suitable columns for charting; create an empty figure with a message
        fig = go.Figure()
        fig.add_annotation(text="No numeric data available for charting", showarrow=False)
    
    fig.update_layout(
        title="📊 Sales Data Visualization",
        xaxis_title=x_col if x_col is not None else "",
        yaxis_title=y_col if y_col is not None else "",
        showlegend=False,
        height=400,
        template="plotly_white"
    )
    
    # Create the render function with the figure
    @render_widget
    def make_chart():
        return fig

    # Register the chart output
    output(id=chart_id)(make_chart)
    
    # Create the render function for the data frame
    @render.data_frame
    def make_grid():
        return render.DataGrid(
            df,
            height="400px",
            filters=False,
            editable=False,
            selection_mode="row",
        )
    
    # Register the data frame output
    output(id=table_id)(make_grid)

    _log(f"✅ Created chart '{chart_id}' and table '{table_id}'")

    # Create tabbed view with chart and table. Keep both panes the same height to
    # avoid double scrollbars and visual jump when switching tabs.
    tab_height = "400px"
    panel_flex_style = "height:100%; width:100%; display:flex; flex-direction:column;"
    table_wrapper_style = "flex:1; width:100%; overflow:auto;"
    # Outer container fixes the total height. Inner panels fill 100% and handle overflow.
    return ui.div(
        ui.div(
            ui.navset_tab(
                ui.nav_panel(
                    "Chart",
                    ui.div(
                        output_widget(chart_id),
                        style=f"{panel_flex_style} align-items:stretch; justify-content:center; overflow:hidden;",
                    ),
                ),
                ui.nav_panel(
                    "Data Table",
                    ui.div(
                        ui.div(
                            ui.output_data_frame(table_id),
                            style=table_wrapper_style,
                        ),
                        style=panel_flex_style,
                    ),
                ),
                id=f"tabs_{chart_counter_value}_{timestamp}",
                
            ),
            style=f"height: {tab_height};"
        ),
        class_="my-3"
    )
