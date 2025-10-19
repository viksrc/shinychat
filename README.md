# Python Shiny Chat App 🚀

A beautiful, interactive chat application built with Python Shiny featuring real-time messaging, LLM integration with ChatLas, MCP server for data, and inline Plotly charts.

## Table of Contents

- [Quick Start](#quick-start)
- [Features](#features)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Running Tests](#running-tests)
- [How to Use](#how-to-use)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Technical Details](#technical-details)
- [Customization](#customization)
- [Contributing](#contributing)
- [License](#license)

---

## Quick Start

```bash
# Setup
git clone https://github.com/viksrc/shinychat.git
cd shinychat
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the app
./start_app.sh

# Run tests
python test_mcp_median.py
```

## Features

- 💬 **Interactive Chat Interface**: Clean, modern chat UI with `ui.Chat` component
- 🤖 **LLM Integration**: ChatLas integration with OpenAI for intelligent responses
- 📊 **MCP Data Server**: Model Context Protocol server providing sales data as DataFrames
- � **Inline Plotly Charts**: Interactive charts embedded directly in chat messages using TagList
- 🎨 **Beautiful Styling**: Gradient headers, rounded corners, and smooth animations
- 📱 **Responsive Design**: Works great on desktop and mobile
- 🧹 **Clear Chat**: One-click chat history clearing
- ⌨️ **Keyboard Support**: Send messages with Enter key

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/viksrc/shinychat.git
   cd shinychat
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up API keys**:
   
   For the Shiny app (OpenRouter):
   ```bash
   export OPENROUTER_API_KEY="your-openrouter-api-key-here"
   ```
   
   Or use the provided start script (see below).

## Running the Application

### Quick Start

Use the provided start script that includes the API key:
```bash
chmod +x start_app.sh
./start_app.sh
```

### Manual Start

```bash
source .venv/bin/activate
shiny run app.py --reload
```

Then open your browser to `http://127.0.0.1:8000`

### Stopping the Application

Press `Ctrl+C` in the terminal, or:
```bash
pkill -f "shiny run"
```

## Running Tests

### Latency Comparison Tests

Test multiple LLM models for tool-calling performance:

**Full test suite** (7 models, 3 runs each, ~30 seconds):
```bash
source .venv/bin/activate
python test_mcp_median.py
```

**Clean output** (filters async cleanup errors):
```bash
chmod +x test_mcp_median_clean.sh
./test_mcp_median_clean.sh
```

**Test specific model**:
```bash
python test_gpt_oss_only.py  # Tests only openai/gpt-oss-120b
```

### Other Test Scripts

**Validate API keys**:
```bash
python test_api_keys.py
```

**Quick MCP test**:
```bash
python test_mcp_quick.py
```

**Inspect MCP functionality**:
```bash
python test_mcp_inspect.py
```

**Debug specific models**:
```bash
python debug_deepseek_failure.py  # DeepSeek reliability analysis
python debug_qwen_failure.py      # Qwen JSON generation issues
```

### Test Results

Current model performance (median latency, success rate):

| Rank | Model | Latency | Success |
|------|-------|---------|---------|
| 🥇 | openai/gpt-4o | 2.2s | 3/3 (100%) |
| 🥈 | openai/gpt-oss-120b | 3.3s | 3/3 (100%) |
| 🥉 | openai/gpt-4.1 | 3.8s | 3/3 (100%) |
| | anthropic/claude-sonnet-4 | 4.8s | 3/3 (100%) |
| | deepseek/deepseek-chat-v3.1 | 6.0s | 2/3 (67%) |
| | qwen/qwen3-30b-a3b | 9.0s | 0/3 (0%) |
| | qwen/qwen3-30b-a3b-thinking | 10.7s | 1/3 (33%) |

**Note**: Async generator cleanup errors in parallel tests are cosmetic only. See `MCP_CLEANUP_ISSUE.md` for details.

## How to Use

1. **Type a message** in the input field at the bottom
2. **Ask for charts** by typing "bar", "chart", or "plot"
3. **View responses** from the LLM or chatbot in real-time
4. **Interact with charts** embedded inline in the chat
5. **Clear chat** anytime using the Clear button below the input
6. **Monitor statistics** at the bottom of the screen

## Architecture

### ChatLas Integration
- Uses ChatLas library to interface with OpenAI's GPT models
- Provides intelligent, context-aware responses
- Falls back to keyword-based responses if no API key is set

### MCP Server
- Model Context Protocol server (`mcp_sales_server.py`)
- Provides sales data as pandas DataFrames
- Fast, efficient data retrieval
- Tools available:
  - `get_sales_data`: Returns random sales data for products

### Inline Chart Rendering
- Charts appear directly in chat messages using `TagList`
- Each chart gets a unique ID for independent rendering
- Dynamic widget registration with `output_widget()` and `render_widget()`
- Full Plotly interactivity (hover, zoom, pan) preserved

## Chat Features

### LLM Responses (with API key)
- Natural language understanding
- Context-aware conversations
- Sales data analysis and insights

### Fallback Responses (without API key)
The bot responds to various keywords:
- Greetings: "hello", "hi"
- Questions: "how are you", "help"
- Technology: "python", "shiny"
- Charts: "bar", "chart", "plot"

### Chart Features
- **Data Source**: MCP server provides DataFrame
- **Visualization**: Plotly bar charts with gradient colors
- **Interactivity**: Hover tooltips, zoom, pan, reset
- **Inline Display**: Charts embedded directly in chat flow
- **Statistics**: Total sales, product count, timestamp

## Project Structure

```
shiny/
├── app.py                          # Main Shiny application
├── start_app.sh                    # Script to start app with API key
│
├── mcp_sales_server.py             # MCP server for sales data
├── mcp_sales_server_no_args.py     # Simplified MCP server
│
├── test_mcp_median.py              # Parallel latency tests (7 models)
├── test_mcp_median_clean.sh        # Filtered output wrapper
├── test_gpt_oss_only.py            # Single model test
├── test_mcp_quick.py               # Quick MCP functionality test
├── test_mcp_inspect.py             # MCP inspection tool
├── test_openrouter_mcp.py          # OpenRouter MCP integration test
├── test_api_keys.py                # API key validator
│
├── debug_deepseek_failure.py       # DeepSeek reliability analysis
├── debug_qwen_failure.py           # Qwen JSON error debugging
├── debug_tool_calling.py           # Tool calling inspector
│
├── README.md                       # This documentation
├── MCP_README.md                   # MCP server documentation
├── MCP_CLEANUP_ISSUE.md            # Async cleanup error explanation
├── QUICKSTART.md                   # Quick start guide
├── TEST_FRAMEWORK_README.md        # Testing framework docs
├── SOLUTION_SUMMARY.md             # Technical solution summary
│
└── requirements.txt                # Python dependencies
```

## Technical Details

- **Framework**: Python Shiny with ui.Chat component
- **LLM**: ChatLas with OpenAI GPT-4o-mini
- **Data**: MCP server with pandas DataFrames
- **Charts**: Plotly with shinywidgets integration
- **Styling**: Custom CSS with Bootstrap classes
- **State Management**: Reactive values for real-time updates
- **UI Components**: TagList for rich inline content

## Customization

### Modify Chart Types
Edit the `handle_user_input` function to create different Plotly charts:
- Line charts, scatter plots, pie charts, etc.
- Customize colors, layouts, and interactivity

### Change LLM Model
Modify the ChatLas initialization:
```python
llm = ChatOpenAI(model="gpt-4")  # Use GPT-4 instead
```

### Extend MCP Server
Add more tools to `mcp_sales_server.py`:
- Different data types (inventory, customers, etc.)
- Data filtering and aggregation
- Real database connections

## Contributing

Feel free to fork this project and submit pull requests for improvements!

## License

This project is open source and available under the MIT License.