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

welcome = """
**Welcome to Sales Analytics!** How can I assist you with your sales data today?

Here are some suggestions:

* <span class="suggestion submit">Show me sales by region</span>
* <span class="suggestion submit">What's the best performing product?</span>
* <span class="suggestion submit">Generate a sales report for Q3</span>
* <span class="suggestion submit">Compare this month's sales to last month</span>
* <span class="suggestion submit">Show me the sales trend for the past 6 months</span>
"""


# Define the UI
app_ui = ui.page_fluid(
    # Custom CSS for styling
    ui.tags.head(
        ui.tags.style("""
            .sidebar {
                border-right: 1px solid #ddd;
                padding: 15px;
                height: 100%;
                overflow-y: auto;
            }
            .chat-header {
                background-color: #f8f9fa;
                padding: 15px;
                border-bottom: 1px solid #ddd;
                text-align: center;
            }
            .chat-container {
                height: 500px;
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 10px;
                margin-bottom: 20px;
                overflow-y: auto;
            }
            .chat-footer {
                position: sticky;
                bottom: 0;
                background: white;
                padding: 8px 12px;
                border-top: 1px solid #e9ecef;
            }
            .suggestion {
                display: inline-block;
                color: #007bff;
                text-decoration: underline;
                cursor: pointer;
                font-size: 0.9em;
                margin: 2px;
            }
            .suggestion:hover {
                color: #0056b3;
            }
            /* Sidebar chat history styling */
            .sidebar-msg {
                font-weight: 600; /* bold */
                padding: 6px 0;
                margin: 0;
            }
            .sidebar-sep {
                border: none;
                border-top: 1px solid #f0f0f0; /* very light gray */
                margin: 6px 0;
            }
        """
    )),
    
    # Layout with a left sidebar using Shiny's layout_sidebar
    ui.layout_sidebar(
        ui.sidebar(
            ui.h5("Chat History"),
            ui.div(ui.input_action_button("new_chat", "New Chat"), class_="mb-3"),
            ui.output_ui("chat_history"),
            id="sidebar_left",
            open="desktop",
        ),

        # Main chat area
        ui.div(
            ui.div(
                ui.div(
                    ui.h4("ST Trader Copilot", class_="mb-2"),
                    ui.p("Hello! How can I help you with pretrade trading cost estimates and posttrade realized transaction cost analytics (TCA)?", class_="mb-3"),
                    class_="chat-header"
                ),
                ui.div(
                    ui.chat_ui(
                        id="chat",
                        messages=["**Welcome to Sales Analytics!** How can I assist you with your sales data today?"],
                    ),
                    class_="chat-container"
                ),
                ui.div(
                    ui.div(ui.input_select("model_select", "Select LLM", choices=[
                        "anthropic/claude-sonnet-4",
                        "openai/gpt-4o",
                        "openai/gpt-4.1",
                        "openai/gpt-oss-120b",
                        "qwen/qwen3-30b-a3b",
                        "qwen/qwen3-30b-a3b-thinking-2507",
                        "deepseek/deepseek-chat-v3.1",
                    ]), class_="ms-2"),
                    ui.div(ui.input_select("prompt_select", "Select Prompt", choices=["What is the cost to buy 10000 shares of AAPL?", "Generate a sales report for Q3"]), class_="ms-2"),
                    ui.div(ui.input_switch("display_func_calls", "Display Func Calls", value=True), class_="ms-2"),
                    class_="chat-footer d-flex align-items-center"
                )
            )
        )
    )
)

def server(input, output, session):
    # Create chat instance (async mode)
    
    def _create_sales_chart(sales_data, chart_counter_value):
        """Create and display a sales chart from the provided data"""
        print(f"📊 Detected sales data, creating chart...")
        try:
            # Create DataFrame
            df = pd.DataFrame(sales_data)
            
            # Create a unique ID for the chart
            chart_id = f"sales_chart_{chart_counter_value}"
            
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
            
            # Use the provided counter value for unique ID
            chart_id = f"sales_chart_{chart_counter_value}"
            
            # Create the render function with the figure
            @render_widget
            def make_chart():
                return fig
            
             # Register the output
            output(id=chart_id)(make_chart)

            msg = ui.div(output_widget(chart_id),class_="my-3")
          
            return msg
            
        except Exception as chart_error:
            print(f"⚠️  Failed to create chart: {chart_error}")
            import traceback
            print(traceback.format_exc())
            return False

            
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
            # Preserve existing chat messages when switching models.
            # Do not clear or re-append the welcome message.
            print("ℹ️ Model switched; preserving existing chat messages.")
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
                # The MCP server script lives in the repo-level `scripts/` directory after reorganization.
                project_root = Path(__file__).resolve().parents[1]
                server_path = str(project_root / "scripts" / "mcp_sales_server.py")
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
    
    # Counter for unique chart IDs (non-reactive)
    # Using a list to make it mutable in nested scopes
    chart_counter = [0]
    
    # Removed the separate process_streaming_response method since we've inlined it

    @chat.on_user_submit
    async def _(user_input: str):
        """Handle user message submission and generate bot response"""
        
        # Record message time
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        times = message_times.get()
        times.append(current_time)
        message_times.set(times)
        
        # Get current LLM instance
        llm = current_llm.get()
        
        if not llm:
            print("⚠️ No LLM available")
            await chat.append_message("Sorry, the LLM is not available. Please check the configuration.")
            return

        try:
            # Ensure MCP tools are registered before first prompt
            if not mcp_ready.get():
                import asyncio
                for _ in range(10):  # wait up to ~2s
                    if mcp_ready.get():
                        break
                    await asyncio.sleep(0.2)
            
            selected_model = input.model_select()
            print(f"🤖 Using {selected_model} with async streaming...")
            
            # Process the streaming response
            full_text = ""
            message_id = None
            
            # Create a generator function to handle the streaming
            async def chunk_generator():
                """Generator that processes chunks from the async stream"""
                stream = await llm.stream_async(user_input, content="all")
                async for chunk in stream:
                    yield chunk
                    
                    # Check for ContentToolResult
                    if hasattr(chunk, '__class__') and 'ContentToolResult' in str(chunk.__class__):
                        tool_name = getattr(chunk, 'name', None)
                        print(f"📊 Found ContentToolResult: {tool_name}")
                        
                        if tool_name == 'get_sales_data':
                            # Get the structured value
                            tool_value = getattr(chunk, 'value', chunk)
                            print(f"🔍 Tool result type: {type(tool_value)}")
                            print(f"🔍 Tool result value: {tool_value[:200] if isinstance(tool_value, str) else tool_value}")

                            # Robust parsing for streamed/truncated JSON: accumulate text until we can
                            # extract a balanced JSON array/object and parse it. Avoid calling json.loads
                            # on partial strings which raises JSONDecodeError.
                            if not hasattr(chunk_generator, '_json_buf'):
                                chunk_generator._json_buf = ''

                            # If value is already structured (list/dict), use it directly
                            if isinstance(tool_value, (list, dict)):
                                sales_data = tool_value
                                print(f"✅ Received structured sales data ({len(sales_data)} items)")
                            elif isinstance(tool_value, str):
                                # Append to buffer and try to extract a JSON array or object
                                chunk_generator._json_buf += tool_value
                                buf = chunk_generator._json_buf

                                def try_parse_candidate(s):
                                    try:
                                        return json.loads(s)
                                    except Exception:
                                        return None

                                parsed = None

                                # First try to find a balanced JSON array starting at first '['
                                start = buf.find('[')
                                if start != -1:
                                    depth = 0
                                    for idx in range(start, len(buf)):
                                        ch = buf[idx]
                                        if ch == '[':
                                            depth += 1
                                        elif ch == ']':
                                            depth -= 1
                                            if depth == 0:
                                                candidate = buf[start:idx+1]
                                                parsed = try_parse_candidate(candidate)
                                                if parsed is not None:
                                                    sales_data = parsed
                                                    # remove consumed portion from buffer
                                                    chunk_generator._json_buf = buf[idx+1:]
                                                break

                                # If not found, try to find a balanced JSON object starting at first '{'
                                if parsed is None:
                                    start_obj = buf.find('{')
                                    if start_obj != -1:
                                        depth = 0
                                        for idx in range(start_obj, len(buf)):
                                            ch = buf[idx]
                                            if ch == '{':
                                                depth += 1
                                            elif ch == '}':
                                                depth -= 1
                                                if depth == 0:
                                                    candidate = buf[start_obj:idx+1]
                                                    parsed = try_parse_candidate(candidate)
                                                    if parsed is not None:
                                                        sales_data = parsed
                                                        chunk_generator._json_buf = buf[idx+1:]
                                                    break

                                # As a last resort, try parsing the whole buffer
                                if parsed is None:
                                    whole = try_parse_candidate(buf)
                                    if whole is not None and isinstance(whole, (list, dict)):
                                        sales_data = whole
                                        chunk_generator._json_buf = ''

                                if parsed is None and not isinstance(tool_value, (list, dict)):
                                    # Not enough data yet; wait for more chunks
                                    sales_data = None
                                        # No sales data available yet
                                    
                        if 'sales_data' in locals() and sales_data is not None:
                            print(f"✅ Extracted sales data: {len(sales_data)} products")
                            try:
                                # Create and display the sales chart
                                current_counter = chart_counter[0]
                                chartchunk = _create_sales_chart(sales_data, current_counter)
                                chart_counter[0] += 1
                                print(f"📊 _create_sales_chart returned: {chartchunk}")
                                if chartchunk:
                                    yield chartchunk
                            except Exception as e_chart:
                                print(f"⚠️ Failed to render sales chart: {e_chart}")
                    
                                    
            # Pass the generator directly to append_message_stream
            await chat.append_message_stream(chunk_generator())
            
            print(f"✅ Message completed")
            
        except Exception as e:
            print(f"❌ Error in handle_user_input: {e}")
            import traceback
            print(traceback.format_exc())
            await chat.append_message(f"Sorry, I encountered an error: {str(e)}")
        
        # Record bot response time
        bot_time = datetime.datetime.now().strftime("%H:%M:%S")
        times = message_times.get()
        times.append(bot_time)
        message_times.set(times)
    
    # Clear chat button and handler removed per UX update
    
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

    @output
    @render.ui
    def chat_history():
        """Render chat history into the left sidebar"""
        msgs = chat.messages()
        # If there is at least one user message, show it prominently at the top
        items = []
        first_user_msg = None
        if msgs:
            # Try to find the first message that appears to be from the user.
            # Messages may be strings or objects; handle both.
            for m in msgs:
                if isinstance(m, str):
                    # Use the first non-empty string
                    if m.strip():
                        first_user_msg = m
                        break
                else:
                    # If it's dict-like, look for common keys
                    try:
                        role = getattr(m, 'role', None) if not isinstance(m, dict) else m.get('role')
                        content = getattr(m, 'content', None) if not isinstance(m, dict) else m.get('content')
                        if role and role == 'user' and content:
                            first_user_msg = content
                            break
                        # fallback: if content exists and no role, take it
                        if content and not role:
                            first_user_msg = content
                            break
                    except Exception:
                        # last-resort string conversion
                        s = str(m)
                        if s.strip():
                            first_user_msg = s
                            break

        if first_user_msg:
            display_text = first_user_msg if isinstance(first_user_msg, str) else str(first_user_msg)
            short = (display_text[:200] + '...') if len(display_text) > 200 else display_text
            # Only display the first user message, bold, with a light separator below
            return ui.div(
                ui.p(short, class_="sidebar-msg"),
                ui.tags.hr(class_="sidebar-sep")
            )

        return ui.div(ui.p("No chat history yet.", class_="sidebar-msg"))
    

# Create the app
app = App(app_ui, server)
