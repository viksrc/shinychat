"""
Standalone test to verify chart generation logic works correctly
This isolates the parsing and chart creation from Shiny
"""
import json
import re
import pandas as pd
import plotly.graph_objects as go

# Sample response text (exactly as it appears in the terminal output)
sample_response = """I'll help you retrieve the sales data using the get_sales_data function. Since no specific number of  
products was requested, I'll use the default value.                                                   

                                                                                                      
 # 🔧 tool request (toolu_bdrk_01Vors4jrGtwawvgwBrxdCKh)                                              
 get_sales_data()                                                                                     
                                                                                                      

                                                                                                      
 # ✅ tool result (toolu_bdrk_01Vors4jrGtwawvgwBrxdCKh)                                               
 Sales Data:                                                                                          
      Product  Sales                                                                                  
 0  Product A     18                                                                                  
 1  Product B     91                                                                                  
 2  Product C     51                                                                                  
 3  Product D     98                                                                                  
 4  Product E     46                                                                                  
                                                                                                      
 JSON: [{"Product":"Product A","Sales":18},{"Product":"Product B","Sales":91},{"Product":"Product     
 C","Sales":51},{"Product":"Product D","Sales":98},{"Product":"Product E","Sales":46}]                
                                                                                                      


Here's the sales data showing 5 products (A through E) and their respective sales figures. Product D  
has the highest sales at 98 units, followed by Product B with 91 units. Product A shows the lowest    
sales with 18 units. Would you like to see data for a different number of products or analyze this    
data in any specific way?"""

print("=" * 80)
print("TESTING CHART PARSING LOGIC")
print("=" * 80)

# Test 1: Extract JSON from response
print("\n1. Testing JSON extraction...")
sales_data = None
try:
    # Look for JSON pattern in the full response text
    json_match = re.search(r'JSON:\s*(\[{.*?"Product".*?"Sales".*?}\])', sample_response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        print(f"✅ Found JSON pattern!")
        print(f"   Raw JSON string: {json_str[:100]}...")
        
        # Clean up the JSON string (remove line breaks and extra spaces)
        json_str = ' '.join(json_str.split())
        print(f"   Cleaned JSON: {json_str[:100]}...")
        
        sales_data = json.loads(json_str)
        print(f"✅ Successfully parsed JSON!")
        print(f"   Found {len(sales_data)} products")
    else:
        print("❌ No JSON pattern found")
except Exception as parse_error:
    print(f"❌ Parse error: {parse_error}")
    import traceback
    print(traceback.format_exc())

# Test 2: Create DataFrame
if sales_data:
    print("\n2. Testing DataFrame creation...")
    try:
        df = pd.DataFrame(sales_data)
        print(f"✅ DataFrame created successfully!")
        print(df)
    except Exception as df_error:
        print(f"❌ DataFrame error: {df_error}")
        import traceback
        print(traceback.format_exc())
        
    # Test 3: Create Plotly chart
    print("\n3. Testing Plotly chart creation...")
    try:
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
        
        print(f"✅ Chart created successfully!")
        print(f"   Chart has {len(fig.data)} trace(s)")
        print(f"   Data points: {len(fig.data[0].x)}")
        
        # Save to HTML file to verify it works
        output_file = "/Users/vivek/projects/shiny/test_chart.html"
        fig.write_html(output_file)
        print(f"✅ Chart saved to: {output_file}")
        print(f"   Open this file in a browser to verify the chart displays correctly")
        
    except Exception as chart_error:
        print(f"❌ Chart error: {chart_error}")
        import traceback
        print(traceback.format_exc())
else:
    print("\n❌ Cannot proceed - no sales data was extracted")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
