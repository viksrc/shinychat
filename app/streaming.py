"""Streaming helper: chunk_generator extracted from app.app to centralize stream parsing."""

import json
import traceback
from sales_chart import create_sales_chart

def _ensure_buf(obj):
    if not hasattr(_ensure_buf, 'buf'):
        _ensure_buf.buf = ''
    return _ensure_buf

async def chunk_generator(llm, user_input, output, chart_counter, disable_plots=False):
    """Generator that processes chunks from the async LLM stream.

    Parameters:
    - llm: Chat instance with stream_async
    - user_input: str user prompt
    - output: shiny output object used by create_sales_chart
    - chart_counter: a mutable container (list) holding an int counter at index 0
    - disable_plots: bool whether to skip creating charts
    """
    chart_to_show = None
    try:
        stream = await llm.stream_async(user_input, content="all")
        async for chunk in stream:
            yield chunk

            # Check for ContentToolResult-like chunks
            try:
                if hasattr(chunk, '__class__') and 'ContentToolResult' in str(chunk.__class__):
                    tool_name = getattr(chunk, 'name', None)
                    # Debug
                    # print(f"📊 Found ContentToolResult: {tool_name}")

                    if tool_name == 'get_sales_data':
                        tool_value = getattr(chunk, 'value', chunk)

                        # Initialize buffer helper on module-level
                        buf_holder = _ensure_buf(None)

                        # If already structured, accept directly
                        if isinstance(tool_value, (list, dict)):
                            sales_data = tool_value
                        elif isinstance(tool_value, str):
                            buf_holder.buf += tool_value
                            buf = buf_holder.buf

                            def try_parse_candidate(s):
                                try:
                                    return json.loads(s)
                                except Exception:
                                    return None

                            parsed = None

                            # Try find balanced JSON array
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
                                                buf_holder.buf = buf[idx+1:]
                                            break

                            # Try object if array not found
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
                                                    buf_holder.buf = buf[idx+1:]
                                                break

                            # Last resort: parse whole buffer
                            if parsed is None:
                                whole = try_parse_candidate(buf)
                                if whole is not None and isinstance(whole, (list, dict)):
                                    sales_data = whole
                                    buf_holder.buf = ''
                                else:
                                    sales_data = None
                        else:
                            sales_data = None

                        if 'sales_data' in locals() and sales_data is not None:
                            # create chart if allowed and yield it immediately so the UI
                            # can display each chart as soon as its tool result arrives.
                            if not disable_plots:
                                try:
                                    current_counter = chart_counter[0]
                                    chartchunk = create_sales_chart(output, sales_data, current_counter)
                                    chart_counter[0] += 1
                                    if chartchunk:
                                        # Yield the chart UI element right away
                                        yield chartchunk
                                except Exception:
                                    # Do not fail the stream on chart creation
                                    print("⚠️ Failed to render sales chart:\n" + traceback.format_exc())
                            else:
                                # Plots disabled; nothing to yield for this tool result
                                pass
            except Exception:
                # Ignore chunk parsing errors but continue streaming
                print("⚠️ Error while processing stream chunk:\n" + traceback.format_exc())

    except Exception:
        print("❌ Error in streaming.chunk_generator:\n" + traceback.format_exc())

    # After stream finished, yield the chart if created
    if chart_to_show is not None:
        yield chart_to_show
