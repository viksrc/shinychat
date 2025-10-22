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
import time
from sales_chart import create_sales_chart

# Read suggested prompts from file
def load_suggested_prompts():
    """Load suggested prompts from the markdown file"""
    prompts_path = Path(__file__).parent / "suggested-prompts.md"
    try:
        with open(prompts_path, 'r') as f:
            lines = f.readlines()
        # Skip the header line and empty lines, strip whitespace
        prompts = [line.strip() for line in lines[1:] if line.strip()]
        return prompts
    except Exception as e:
        print(f"⚠️ Failed to load suggested prompts: {e}")
        return []
        

# Load all suggested prompts
all_suggested_prompts = load_suggested_prompts()

# Create welcome message with first 5 suggestions
welcome_suggestions = "\n".join([
    f"* <span class=\"suggestion submit\">{prompt}</span>"
    for prompt in all_suggested_prompts[:5]
])

welcome = f"""
**Welcome to Sales Analytics!** How can I assist you with your sales data today?

Here are some suggestions:

{welcome_suggestions}
"""


# Define the UI
app_ui = ui.page_fillable(
    ui.layout_sidebar(
        ui.sidebar(
            ui.h5("Chat History"),
            ui.input_action_button(
                "new_chat", 
                "New Chat",
                class_="btn-primary w-100 mb-3"
            ),
            ui.output_ui("chat_history"),
            id="sidebar_left",
            open="desktop",
        ),
        ui.card(
            ui.card_header(
                ui.h4("Sales Analytics Copilot", class_="m-0"),
                class_="bg-primary text-white"
            ),
            ui.chat_ui(
                id="chat",
                messages=[welcome],
            ),
            ui.card_footer(
                ui.layout_columns(
                    ui.input_select("model_select", "Select LLM", choices=[
                        "anthropic/claude-sonnet-4",
                        "openai/gpt-4o",
                        "openai/gpt-4.1",
                        "openai/gpt-oss-120b",
                        "qwen/qwen3-30b-a3b",
                        "qwen/qwen3-30b-a3b-thinking-2507",
                        "deepseek/deepseek-chat-v3.1",
                    ]),
                    ui.input_select("prompt_select", "Select Prompt", choices=all_suggested_prompts),
                    ui.input_switch("display_func_calls", "Display Func Calls", value=True),
                    ui.input_switch("disable_plots", "Disable Plots", value=False),
                    col_widths=[3, 5, 2, 2]
                ),
                class_="bg-light p-2"
            ),
            full_screen=True,
            fill=True,
            height="100%"
        ),
        fillable=True
    )
)

def server(input, output, session):
    # Create chat instance (async mode)
            
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
            
            # Read system prompt from file
            system_prompt_path = Path(__file__).parent / "system-prompt.md"
            with open(system_prompt_path, 'r') as f:
                system_prompt = f.read().strip()
            
            llm = ChatOpenRouter(
                model=model_name,
                api_key=api_key,
                system_prompt=system_prompt
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
    
    # Persisted chat sessions (history) that survive new chats
    chat_sessions = reactive.value([])
    
    # Track message timestamps
    message_times = reactive.value([])
    
    # Counter for unique chart IDs (non-reactive)
    # Using a list to make it mutable in nested scopes
    chart_counter = [0]
    
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

    # React to prompt selection changes
    @reactive.effect
    @reactive.event(input.prompt_select)
    def _on_prompt_select():
        """Handle prompt selection changes by setting the chat input"""
        selected_prompt = input.prompt_select()
        if selected_prompt:
            # Update the chat input value
            chat.update_user_input(value=selected_prompt)


    @reactive.effect
    @reactive.event(input.new_chat)
    async def _handle_new_chat():
        """Create a new LLM instance and clear the chat UI when New Chat is clicked."""
        selected_model = input.model_select()
        print(f"✨ New Chat requested; creating new LLM: {selected_model}")

        # Before creating the new LLM, capture a short summary of the current chat
        try:
            msgs = chat.messages()
            first_user_msg = None
            if msgs:
                for m in msgs:
                    if isinstance(m, str):
                        if m.strip():
                            first_user_msg = m
                            break
                    else:
                        try:
                            role = getattr(m, 'role', None) if not isinstance(m, dict) else m.get('role')
                            content = getattr(m, 'content', None) if not isinstance(m, dict) else m.get('content')
                            if role and role == 'user' and content:
                                first_user_msg = content
                                break
                            if content and not role:
                                first_user_msg = content
                                break
                        except Exception:
                            s = str(m)
                            if s.strip():
                                first_user_msg = s
                                break

            if first_user_msg and not first_user_msg.startswith("**Welcome"):
                display_text = first_user_msg if isinstance(first_user_msg, str) else str(first_user_msg)
                short = (display_text[:200] + '...') if len(display_text) > 200 else display_text
                sessions = chat_sessions.get() or []
                sessions.insert(0, {"summary": short, "model": selected_model, "time": datetime.datetime.now().isoformat()})
                chat_sessions.set(sessions)
        except Exception as e:
            print(f"ℹ️ Could not capture prior chat for history: {e}")

        # Create new LLM instance
        new_llm = create_llm(selected_model)
        if not new_llm:
            await chat.append_message(f"⚠️ Failed to create new LLM: {selected_model}")
            return

        # Replace the current LLM and reset MCP registration so tools will be re-registered
        current_llm.set(new_llm)
        mcp_ready.set(False)

        # Reset UI/chat state: clear messages and re-append the welcome prompt
        try:
            await chat.clear_messages()
            await chat.append_message(welcome)
            # Reset any non-reactive counters (charts)
            try:
                chart_counter[0] = 0
            except Exception:
                pass
            print("✅ New chat started and UI cleared.")
        except Exception as e:
            print(f"⚠️ Failed to clear or initialize chat UI: {e}")
            import traceback
            print(traceback.format_exc())

    

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
            
            # Read reactive values before extended task
            disable_plots = input.disable_plots()
            
            # Process the streaming response
            full_text = ""
            message_id = None
            
            # Create a generator function to handle the streaming
            async def chunk_generator(disable_plots):
                """Generator that processes chunks from the async stream"""
                chart_to_show = None
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
                            if not disable_plots:
                                try:
                                    # Create the chart but don't yield yet - save it to show after stream completes
                                    current_counter = chart_counter[0]
                                    chartchunk =  create_sales_chart(output, sales_data, current_counter)
                                    chart_counter[0] += 1
                                    print(f"📊 _create_sales_chart returned: {chartchunk}")
                                    if chartchunk:
                                        chart_to_show = chartchunk
                                except Exception as e_chart:
                                    print(f"⚠️ Failed to render sales chart: {e_chart}")
                            else:
                                print("📊 Plots disabled, skipping chart creation")
                
                # After all chunks, yield the chart if we created one
                if chart_to_show is not None:
                    print(f"📊 Yielding chart after stream completed")
                    yield chart_to_show
                    
                                    
            # Pass the generator directly to append_message_stream
            await chat.append_message_stream(chunk_generator(disable_plots))
            
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

    @render.ui
    def chat_history():
        """Render chat history into the left sidebar"""
        # Force reactive dependencies so this output reruns when new messages arrive
        times = message_times.get()
        sessions_list = chat_sessions.get()
        
        # Combine persisted sessions (from chat_sessions) and the current chat's first user message
        sessions = sessions_list or []

        # Compute first user message from current chat (if any)
        current_first = None
        try:
            msgs = chat.messages()
        except Exception:
            msgs = []
        
        if msgs:
            for m in msgs:
                if isinstance(m, str):
                    if not m.startswith("**Welcome") and m.strip():
                        current_first = m
                        break
                else:
                    try:
                        role = getattr(m, 'role', None) if not isinstance(m, dict) else m.get('role')
                        content = getattr(m, 'content', None) if not isinstance(m, dict) else m.get('content')
                        if role and role == 'user' and content:
                            current_first = content
                            break
                        if content and not role:
                            current_first = content
                            break
                    except Exception:
                        s = str(m)
                        if s.strip():
                            current_first = s
                            break

        # Build UI: show current chat first (if exists), then previous sessions
        children = []
        if current_first:
            display_text = current_first if isinstance(current_first, str) else str(current_first)
            short = (display_text[:200] + '...') if len(display_text) > 200 else display_text
            children.append(ui.p(short, class_="sidebar-msg"))
            children.append(ui.tags.hr(class_="sidebar-sep"))

        if sessions:
            # Render a small list of previous chats
            for s in sessions:
                # Each session dict contains: summary, model, time
                label = f"{s.get('summary')}" if s.get('summary') else "(no summary)"
                model = s.get('model', '')
                children.append(ui.p(f"{label} ", class_="sidebar-msg"))
                children.append(ui.tags.hr(class_="sidebar-sep"))

        # Return children if we have any, otherwise show "no history" message
        if children:
            return ui.div(*children)
        
        return ui.div(ui.p("No chat history yet.", class_="sidebar-msg"))
    

# Create the app
app = App(app_ui, server)
