import pandas as pd
import plotly.graph_objects as go
import time
from shiny import ui, render
from shinywidgets import output_widget, render_widget

def create_sales_chart(output, sales_data, chart_counter_value):
    """
    Create and display a sales chart and data table from the provided data
    
    Args:
        sales_data: List of dictionaries containing sales data
        chart_counter_value: Unique counter value for chart IDs
        
    Returns:
        UI element containing the chart and table in a tabbed view
    """
    print(f"📊 Detected sales data, creating chart and table...")
    try:
        # Create DataFrame
        df = pd.DataFrame(sales_data)
        
        # Create unique IDs (include timestamp to avoid collisions)
        timestamp = int(time.time() * 1000)
        chart_id = f"sales_chart_{chart_counter_value}_{timestamp}"
        table_id = f"sales_table_{chart_counter_value}_{timestamp}"
        
        # Create Plotly bar chart
        fig = go.Figure(data=[
            go.Bar(
                x=df['Product'],
                y=df['Sales'],
                marker_color='rgb(102, 126, 234)',
                text=df['Sales'],
                textposition='auto',
            )
        ])
        
        fig.update_layout(
            title="📊 Sales Data Visualization",
            xaxis_title="Products",
            yaxis_title="Sales",
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
        def make_table():
            return df
        
        # Register the data frame output
        output(id=table_id)(make_table)

        # Create tabbed view with chart and table
        return ui.div(
            ui.navset_tab(
                ui.nav_panel("Chart", output_widget(chart_id)),
                ui.nav_panel("Data Table", 
                    ui.div(
                        ui.output_data_frame(table_id),
                        style="height: 400px; overflow: auto;"
                    )
                ),
                id=f"tabs_{chart_counter_value}_{timestamp}"
            ),
            class_="my-3"
        )
        
    except Exception as chart_error:
        print(f"⚠️  Failed to create chart/table: {chart_error}")
        import traceback
        print(traceback.format_exc())
        return False
