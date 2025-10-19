from shiny import App, ui, render, reactive
import datetime
import random
import plotly.graph_objects as go
from shinywidgets import output_widget, render_widget
import pandas as pd
import json
from chatlas import ChatOpenRouter
import os
import sys
from pathlib import Path

# Define the UI
app_ui = ui.page_fluid(
    # Custom CSS for chat styling
    ui.tags.head(
        ui.tags.style("""
            .chat-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
            }
            
            .chat-container {
                height: 500px;
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 10px;
                margin-bottom: 20px;
            }
            
            .stats-panel {
                margin-top: 20px;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 10px;
            }
        """)
    ),
    
    # Header
    ui.div(
        ui.h1("🚀 Python Shiny Chat App", class_="mb-2"),
        ui.p("Welcome to your interactive chat application!", class_="mb-0"),
        class_="chat-header"
    ),
    
    # Model selector
    ui.div(
        ui.input_select(
            "model_select",
            "🤖 Select AI Model:",
            choices={
                "openai/gpt-4o": "GPT-4o",
                "openai/gpt-oss-120b": "GPT-OSS-120B",
                "openai/gpt-4.1": "GPT-4.1",
                "anthropic/claude-sonnet-4": "Claude Sonnet-4",
                "deepseek/deepseek-chat-v3.1": "DeepSeek Chat v3.1",
                "qwen/qwen3-30b-a3b": "Qwen3 30B",
                "qwen/qwen3-30b-a3b-thinking-2507": "Qwen3 30B Thinking",
            },
            selected="openai/gpt-4o"
        ),
        class_="mb-3"
    ),
    
    # Chat component
    ui.div(
        ui.chat_ui(
            id="chat",
            messages=["Hello! 👋 I'm your friendly chatbot. How can I help you today?"],
        ),
        # Clear button positioned below chat input
        ui.div(
            ui.input_action_button(
                "clear_chat",
                "🗑️ Clear Chat",
                class_="btn btn-danger btn-sm mt-2"
            ),
            class_="text-end"
        ),
        class_="chat-container"
    ),
    
    # Chat statistics
    ui.div(
        ui.h5("Chat Statistics"),
        ui.output_text("message_count"),
        ui.output_text("last_message_time"),
        class_="stats-panel"
    ),
    
    class_="container-fluid p-4"
)

def server(input, output, session):
    # Create chat instance
    chat = ui.Chat(id="chat")
    
    # Store current LLM instance
    current_llm = reactive.value(None)
    
    # Get OpenRouter API key from environment variable
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("⚠️  OPENROUTER_API_KEY not set. Please set it in your environment.")
        print("   export OPENROUTER_API_KEY='your-key-here'")
    
    # Function to create LLM instance
    def create_llm(model_name: str):
        """Create a new LLM instance with the selected model"""
        try:
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable is required")
            
            llm = ChatOpenRouter(
                model=model_name,
                api_key=api_key,
                # Instruct the model to use available tools
                system_prompt=(
                    "You are a helpful assistant with access to sales data tools. "
                    "\n\nIMPORTANT: You do NOT know the current date. When users ask questions involving "
                    "dates like 'last month', 'this year', 'last week', 'today', etc., you MUST first call "
                    "the 'get_current_date' tool to find out what today's date is before answering."
                    "\n\nAvailable tools:"
                    "\n- get_current_date: Get today's date and time (use this when date context is needed)"
                    "\n- get_sales_data: Retrieve sales data with optional filters:"
                    "\n  * num_products: Number of products to return"
                    "\n  * region: Filter by region (North, South, East, West)"
                    "\n  * start_date: Start of date range (YYYY-MM-DD format)"
                    "\n  * end_date: End of date range (YYYY-MM-DD format)"
                    "\n\nExamples:"
                    "\n- 'sales for last month' -> First get_current_date, then calculate date range, then get_sales_data"
                    "\n- 'North region sales' -> get_sales_data with region='North'"
                    "\n- 'sales from January to March 2024' -> get_sales_data with start_date='2024-01-01', end_date='2024-03-31'"
                    "\n\nAlways use these tools when they can help answer the user's question."
                )
            )
            print(f"✅ {model_name} initialized!")
            return llm
        except Exception as e:
            print(f"❌ Failed to initialize {model_name}: {e}")
            return None
    
    # Initialize with default model
    llm = create_llm("anthropic/claude-3.5-sonnet")
    
    # Flag to indicate MCP tools are registered and ready
    mcp_ready = reactive.value(False)
    
    # Store the current LLM instance
    current_llm.set(llm)
    
    # React to model selection changes
    @reactive.effect
    @reactive.event(input.model_select)
    async def _on_model_change():
        """Handle model selection changes"""
        selected_model = input.model_select()
        print(f"🔄 Switching to model: {selected_model}")
        
        # Create new LLM instance
        new_llm = create_llm(selected_model)
        if new_llm:
            current_llm.set(new_llm)
            # Reset MCP registration flag
            mcp_ready.set(False)
            # Clear chat history for new model
            await chat.clear_messages()
            await chat.append_message(f"Switched to {selected_model}. How can I help you? 👋")
        else:
            await chat.append_message(f"⚠️ Failed to switch to {selected_model}")

    # Register MCP server tools asynchronously on app startup
    @reactive.effect
    async def _register_mcp():
        """Register MCP tools when the app starts or model changes"""
        llm_instance = current_llm.get()
        if llm_instance and not mcp_ready.get():
            try:
                # Register the MCP server tools via stdio.
                server_path = str(Path(__file__).with_name("mcp_sales_server.py"))
                await llm_instance.register_mcp_tools_stdio_async(
                    command=sys.executable,
                    # Use unbuffered stdio to avoid any potential buffering issues
                    args=["-u", server_path],
                    # Give this MCP session a stable name and namespace its tools
                    name="sales_mcp",
                    include_tools=("get_sales_data", "get_current_date"),
                )
                # Debug: list registered tools so we can verify availability at runtime
                try:
                    tools = llm_instance.get_tools()
                    print("🔧 Registered tools:", [t.name for t in tools])
                except Exception as _e:
                    print(f"ℹ️  Could not list tools: {_e}")
                print("✅ MCP sales server tools registered!")
                mcp_ready.set(True)
            except Exception as e:
                print(f"❌ Failed to register MCP tools: {e}")
                import traceback
                print(f"🔍 DEBUG: Full traceback:\n{traceback.format_exc()}")
    
    # Track message timestamps
    message_times = reactive.value([])
    
    # Counter for unique chart IDs
    chart_counter = reactive.value(0)
    
    @chat.on_user_submit
    async def handle_user_input(user_input: str):
        """Handle user message submission and generate bot response"""
        
        # Record message time
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        times = message_times.get()
        times.append(current_time)
        message_times.set(times)
        
        # Get current LLM instance
        llm = current_llm.get()
        
        # Use LLM for conversation - it will decide whether to call the tool
        if llm:
            try:
                # Ensure MCP tools are registered before first prompt to avoid Unknown tool errors
                if not mcp_ready.get():
                    import asyncio
                    for _ in range(10):  # wait up to ~2s
                        if mcp_ready.get():
                            break
                        await asyncio.sleep(0.2)
                
                selected_model = input.model_select()
                print(f"🤖 Using {selected_model} with MCP tool calling...")
                
                # Get the response (not streaming for easier parsing)
                response = await llm.chat_async(user_input)
                
                # Get the full response content
                full_text = await response.get_content()
                
                # STEP 1: Display all tool requests FIRST
                sales_data = None
                tool_requests_found = False
                try:
                    # Use get_turns() to access the chat history
                    from chatlas import ContentToolResult, ContentToolRequest
                    
                    # Get all turns from the chat
                    turns = llm.get_turns()
                    print(f"🔍 Found {len(turns)} turns in chat history")
                    
                    # Look through recent turns for tool requests and results
                    # We check the last few turns as tool requests/results appear there
                    for turn in turns[-3:]:
                        print(f"🔍 Turn role: {turn.role}")
                        if hasattr(turn, 'contents'):
                            print(f"   - Turn has {len(turn.contents)} content items")
                            for content in turn.contents:
                                content_type = type(content).__name__
                                print(f"   - Content type: {content_type}")
                                
                                # Display tool REQUEST with parameters
                                if isinstance(content, ContentToolRequest):
                                    tool_name = getattr(content, 'name', None)
                                    tool_id = getattr(content, 'id', None)
                                    tool_arguments = getattr(content, 'arguments', {})
                                    
                                    print(f"🔧 Found ContentToolRequest: {tool_name}")
                                    tool_requests_found = True
                                    
                                    # Display the tool request in the chat
                                    tool_request_msg = f"🔧 **Tool Request**: `{tool_name}`"
                                    if tool_arguments:
                                        tool_request_msg += f"\n📋 **Arguments**: `{json.dumps(tool_arguments)}`"
                                    else:
                                        tool_request_msg += f"\n📋 **Arguments**: `{{}}`"
                                    
                                    await chat.append_message(tool_request_msg)
                                
                                # Extract sales data from tool RESULT (don't display yet)
                                if isinstance(content, ContentToolResult):
                                    tool_name = getattr(content, 'name', None)
                                    print(f"📊 Found ContentToolResult: {tool_name}")
                                    
                                    if tool_name == 'get_sales_data':
                                        # Get the structured value
                                        tool_value = content.value
                                        print(f"🔍 Tool result type: {type(tool_value)}")
                                        print(f"🔍 Tool result value: {tool_value[:200] if isinstance(tool_value, str) else tool_value}")
                                        
                                        # Parse the JSON from the tool result
                                        import re
                                        if isinstance(tool_value, str):
                                            json_match = re.search(r'JSON:\s*(\[.*?\])', tool_value, re.DOTALL)
                                            if json_match:
                                                json_str = json_match.group(1)
                                                json_str = ' '.join(json_str.split())
                                                sales_data = json.loads(json_str)
                                                print(f"✅ Extracted sales data: {len(sales_data)} products")
                    
                    if not sales_data and tool_requests_found:
                        print(f"ℹ️  Tool requests found but no sales data extracted")
                        
                except Exception as parse_error:
                    print(f"⚠️  Could not extract tool results: {parse_error}")
                    import traceback
                    print(traceback.format_exc())
                
                # STEP 2: If we found sales data, create and display the chart SECOND
                if sales_data:
                    print(f"📊 Detected sales data, creating chart...")
                    try:
                        # Create DataFrame
                        df = pd.DataFrame(sales_data)
                        
                        # Create Plotly bar chart - let Plotly choose colors automatically
                        fig = go.Figure(data=[
                            go.Bar(
                                x=df['Product'],
                                y=df['Sales'],
                                marker=dict(
                                    color=df.index,  # Color by index to get different colors per bar
                                    colorscale='Viridis',  # Use Plotly's color scale
                                    showscale=False
                                ),
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
                        
                        # Increment counter for unique ID
                        counter = chart_counter.get()
                        chart_counter.set(counter + 1)
                        chart_id = f"sales_chart_{counter}"
                        
                        # Create the render function with the figure
                        @render_widget
                        def make_chart():
                            return fig
                        
                        # Append chart to chat using output_widget
                        await chat.append_message(
                            ui.div(
                                output_widget(chart_id),
                                class_="my-3"
                            )
                        )
                        
                        # Register the output
                        output(id=chart_id)(make_chart)
                            
                        print(f"✅ Chart created with ID: {chart_id}")
                    except Exception as chart_error:
                        print(f"⚠️  Failed to create chart: {chart_error}")
                        import traceback
                        print(traceback.format_exc())
                
                # STEP 3: Finally, append the model's text response LAST
                await chat.append_message(full_text)
                
                print(f"✅ Message completed")
                
            except Exception as e:
                print(f"❌ LLM failed: {e}")
                import traceback
                print(f"🔍 DEBUG: Full traceback:\n{traceback.format_exc()}")
                await chat.append_message(f"Sorry, I encountered an error: {str(e)}")
        else:
            print("⚠️ No LLM available")
            await chat.append_message("Sorry, the LLM is not available. Please check the configuration.")
        
        # Record bot response time
        bot_time = datetime.datetime.now().strftime("%H:%M:%S")
        times = message_times.get()
        times.append(bot_time)
        message_times.set(times)
    
    @reactive.effect
    @reactive.event(input.clear_chat)
    async def _():
        """Clear all chat messages"""
        await chat.clear_messages()
        message_times.set([])
        # Add welcome message back
        await chat.append_message("Hello! 👋 I'm your friendly chatbot. How can I help you today?")
    
    @output
    @render.text
    def message_count():
        """Display total message count"""
        messages = chat.messages()
        return f"Total messages: {len(messages)}"
    
    @output
    @render.text
    def last_message_time():
        """Display last message time"""
        times = message_times.get()
        if times:
            return f"Last message: {times[-1]}"
        return "No messages yet"

# Create the app
app = App(app_ui, server)
