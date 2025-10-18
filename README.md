# Python Shiny Chat App 🚀

A beautiful, interactive chat application built with Python Shiny featuring real-time messaging, LLM integration with ChatLas, MCP server for data, and inline Plotly charts.

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

1. Make sure you have Python 3.7+ installed
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Set your OpenAI API key for LLM features:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

## Running the App

1. Navigate to the project directory
2. Run the application:
   ```bash
   shiny run app.py --reload
   ```
3. Open your browser and go to `http://127.0.0.1:8000`

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
├── app.py                  # Main Shiny application
├── mcp_sales_server.py    # MCP server for sales data
├── MCP_README.md          # MCP server documentation
├── README.md              # This documentation
└── requirements.txt       # Python dependencies
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