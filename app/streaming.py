"""Streaming helper: chunk_generator extracted from app.app to centralize stream parsing."""

import json
import traceback
import time
from itertools import count

from faicons import icon_svg
from sales_chart import create_sales_chart
from shiny import reactive, ui

# Use chatlas token snapshot API for reliable cumulative usage
try:
    from chatlas._tokens import token_usage
except Exception:
    token_usage = None


def _token_usage_totals():
    """Return cumulative token usage aggregated across providers."""
    try:
        if token_usage is None:
            return None

        usage = token_usage()
        if not usage:
            return None

        total_input = 0
        total_output = 0
        total_cached = 0

        for entry in usage:
            # Expected keys: name, input, output, cost. Some providers may
            # expose cached tokens; prefer them if present.
            total_input += int(entry.get('input', 0) or 0)
            total_output += int(entry.get('output', 0) or 0)

            cached_value = None
            for key in (
                'cached_input',
                'cached',
                'cache',
                'cached_tokens',
                'cached_output',
            ):
                if key in entry and entry[key] not in (None, ''):
                    cached_value = entry[key]
                    break

            if cached_value is not None:
                try:
                    # Some providers may return strings/floats; convert to int tokens.
                    total_cached += int(float(cached_value))
                except Exception:
                    # ignore malformed cached values
                    pass

        return {'input': total_input, 'output': total_output, 'cached': total_cached}
    except Exception:
        return None


def _format_token_metrics(start_snapshot, end_snapshot):
    """Format delta token usage between two snapshots for display."""
    if end_snapshot is None:
        return "Tokens Input: N/A Cached: N/A Output: N/A"

    start_snapshot = start_snapshot or {'input': 0, 'output': 0, 'cached': 0}

    delta_input = max(int(end_snapshot.get('input', 0) - start_snapshot.get('input', 0)), 0)
    delta_output = max(int(end_snapshot.get('output', 0) - start_snapshot.get('output', 0)), 0)
    delta_cached_raw = max(end_snapshot.get('cached', 0) - start_snapshot.get('cached', 0), 0)
    delta_cached = str(int(delta_cached_raw))

    return f"Tokens Input: {delta_input} Cached: {delta_cached} Output: {delta_output}"


def _register_copy_button_handler(session, button_id):
    """Register a reactive handler that swaps the copy icon to a checkmark."""
    if session is None:
        return

    handlers = getattr(session, "_copy_button_handlers", None)
    if handlers is None:
        handlers = set()
        setattr(session, "_copy_button_handlers", handlers)
    if button_id in handlers:
        return

    def _ensure_handler():
        handlers = getattr(session, "_copy_button_handlers", set())
        if button_id in handlers:
            return

        try:
            button_input = session.input[button_id]
        except KeyError:
            session.on_flushed(_ensure_handler, once=True)
            return

        if button_input is None:
            session.on_flushed(_ensure_handler, once=True)
            return

        @reactive.effect
        @reactive.event(button_input)
        def _():
            ui.update_action_button(
                button_id,
                icon=_fa_icon("check", style="regular", width="0.75rem", height="0.75rem"),
            )

        handlers.add(button_id)
        setattr(session, "_copy_button_handlers", handlers)

    session.on_flushed(_ensure_handler, once=True)


def _metrics_footer(tool_calls, token_text, elapsed, session=None):
    """Build the metrics footer UI with feedback buttons."""
    metrics_line = f"Time: {elapsed:.2f}s {token_text} Tool Calls: {tool_calls}"

    button_suffix = next(_METRICS_BUTTON_COUNTER)
    copy_button_id = f"copy_button_{button_suffix}"

    _register_copy_button_handler(session, copy_button_id)

    actions = ui.div(
        ui.input_action_button(
            f"thumbs_up_{button_suffix}",
            "",
            icon=_fa_icon("thumbs-up", style="regular", width="0.75rem", height="0.75rem"),
            class_="btn btn-outline-secondary me-2",
            style="padding: 4px 8px; font-size: 12px;",
            title="Thumbs Up"
        ),
        ui.input_action_button(
            f"thumbs_down_{button_suffix}", 
            "",
            icon=_fa_icon("thumbs-down", style="regular", width="0.75rem", height="0.75rem"),
            class_="btn btn-outline-secondary me-2",
            style="padding: 4px 8px; font-size: 12px;",
            title="Thumbs Down"
        ),
        ui.input_action_button(
            copy_button_id,
            "",
            icon=_fa_icon("copy", style="regular", width="0.75rem", height="0.75rem"),
            class_="btn btn-outline-secondary",
            style="padding: 4px 8px; font-size: 12px;",
            title="Copy"
        ),
        class_="d-flex align-items-center mb-3"
    )

    footer = ui.div(
        actions,
        ui.tags.span(metrics_line, class_="small text-muted"),
        class_="d-flex flex-column"
    )

    return footer

def _ensure_buf(obj):
    if not hasattr(_ensure_buf, 'buf'):
        _ensure_buf.buf = ''
    return _ensure_buf

async def chunk_generator(llm, user_input, output, chart_counter, disable_plots=False, session=None):
    """Generator that processes chunks from the async LLM stream.

    Parameters:
    - llm: Chat instance with stream_async
    - user_input: str user prompt
    - output: shiny output object used by create_sales_chart
    - chart_counter: a mutable container (list) holding an int counter at index 0
    - disable_plots: bool whether to skip creating charts
    """
    # Metrics to show for each assistant response
    tool_calls = 0
    # Start char_count with the user's input so tokens aren't zero when a prompt was sent
    char_count = len(user_input) if isinstance(user_input, str) else 0
    start_time = time.time()
    metrics_sent = False
    usage_start = _token_usage_totals()
    try:
        stream = await llm.stream_async(user_input, content="all")
        async for chunk in stream:
            # Forward the raw chunk to the chat UI
            yield chunk

            # Collect simple metrics: try several common locations for streamed text
            try:
                text = None
                # common attributes used by different clients
                if hasattr(chunk, 'text'):
                    text = getattr(chunk, 'text')
                elif hasattr(chunk, 'content'):
                    text = getattr(chunk, 'content')
                elif hasattr(chunk, 'delta'):
                    delta = getattr(chunk, 'delta')
                    if isinstance(delta, dict):
                        # e.g. {'content': '...'} or {'message': {...}}
                        text = delta.get('content') or delta.get('message')
                elif hasattr(chunk, 'message'):
                    msg = getattr(chunk, 'message')
                    if isinstance(msg, dict):
                        if 'content' in msg and isinstance(msg['content'], str):
                            text = msg['content']
                        elif 'content' in msg and isinstance(msg['content'], list):
                            parts = []
                            for item in msg['content']:
                                if isinstance(item, dict):
                                    parts.append(item.get('text', ''))
                                else:
                                    parts.append(str(item))
                            text = ''.join(parts)

                # fallback: inspect __dict__ for plain dict-like chunks
                if text is None:
                    try:
                        # look for a bytes/str chunk directly
                        if isinstance(chunk, (str, bytes)):
                            text = chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk
                        else:
                            d = getattr(chunk, '__dict__', None)
                            if isinstance(d, dict):
                                for k in ('text', 'content', 'message'):
                                    v = d.get(k)
                                    if isinstance(v, str):
                                        text = v
                                        break
                                    if isinstance(v, dict):
                                        # possibly nested content
                                        for kk in ('content', 'text'):
                                            if kk in v and isinstance(v[kk], str):
                                                text = v[kk]
                                                break
                                        if text is not None:
                                            break
                                    if isinstance(v, list):
                                        parts = []
                                        for item in v:
                                            if isinstance(item, dict):
                                                parts.append(item.get('text', '') or item.get('content', ''))
                                            else:
                                                parts.append(str(item))
                                        if any(parts):
                                            text = ''.join(parts)
                                            break
                    except Exception:
                        pass

                if isinstance(text, str) and text:
                    char_count += len(text)
            except Exception:
                pass

            # Check for ContentToolResult-like chunks
            try:
                if hasattr(chunk, '__class__') and 'ContentToolResult' in str(chunk.__class__):
                    tool_name = getattr(chunk, 'name', None)
                    # Debug
                    # print(f"📊 Found ContentToolResult: {tool_name}")

                    # Count tool calls for metrics
                    tool_calls += 1

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

    except Exception as e:
        # Log server-side and yield a user-visible error message
        tb = traceback.format_exc()
        print("❌ Error in streaming.chunk_generator:\n" + tb)
        # Create a small UI element that shows the error to the user in the chat
        try:
            err_text = f"Error talking to LLM/tool: {str(e)}"
            # Include short traceback tail for debugging
            tail = '\n'.join(tb.splitlines()[-5:])
            err_div = ui.div(
                ui.tags.p("⚠️ An error occurred while processing your request."),
                ui.tags.pre(err_text + "\n" + tail, style="white-space: pre-wrap; background:#fff3cd; padding:8px; border-radius:4px;"),
            )
            # Also add metrics if available
            try:
                elapsed = time.time() - start_time
                usage_end = _token_usage_totals()
                token_text = _format_token_metrics(usage_start, usage_end)
                metrics_div = _metrics_footer(tool_calls, token_text, elapsed, session=session)
                yield ui.div(err_div, metrics_div)
                metrics_sent = True
            except Exception:
                yield err_div
        except Exception:
            # If UI creation fails, just suppress and end
            print("Failed to yield error UI:\n" + traceback.format_exc())

    # After stream finished, yield final metrics
    try:
        elapsed = time.time() - start_time
        usage_end = _token_usage_totals()
        token_text = _format_token_metrics(usage_start, usage_end)
        if not metrics_sent:
            metrics_div = _metrics_footer(tool_calls, token_text, elapsed, session=session)
            yield metrics_div
    except Exception:
        # Ignore metrics rendering errors
        print("⚠️ Failed to yield final metrics UI:\n" + traceback.format_exc())
_METRICS_BUTTON_COUNTER = count(1)
def _fa_icon(name: str, style: str = "regular", **kwargs):
    """Return an icon, falling back to other styles if the requested style is unavailable."""
    candidates = [style, "solid", None]
    seen = set()
    base_kwargs = dict(kwargs)
    base_kwargs.pop("style", None)
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        options = dict(base_kwargs)
        try:
            if candidate is None:
                return icon_svg(name, **options)
            return icon_svg(name, style=candidate, **options)
        except ValueError:
            continue
    # If we reach here, re-raise with original style to surface the error
    return icon_svg(name, style=style, **base_kwargs)
