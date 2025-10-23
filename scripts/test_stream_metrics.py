#!/usr/bin/env python3
"""
Simple CLI tester for streaming metrics using chatlas.

Usage:
  python scripts/test_stream_metrics.py "Your prompt here"

Configure your provider credentials via environment variables as you do for the app
(e.g. OPENROUTER_API_KEY, OPENAI_API_KEY, etc.). This script tries to use the
chatlas Chat implementation used by the app (chatlas._chat.Chat). If your
project installs chatlas differently, adjust the import.

What it prints:
 - all streamed chunks (repr)
 - running char count for streamed text
 - final summary: tool calls, est. tokens (chars/4), total chars, elapsed seconds

This is intentionally minimal and defensive so you can run it in your project's
virtualenv used by the app.
"""

import sys
import asyncio
import time
import traceback

try:
    # chatlas internals are used in the app; this is a pragmatic import.
    from chatlas._chat import Chat
except Exception:
    Chat = None


def _extract_text_from_chunk(chunk):
    """Try several heuristics to extract textual content from a streamed chunk."""
    try:
        if chunk is None:
            return ''
        if isinstance(chunk, str):
            return chunk
        if isinstance(chunk, bytes):
            return chunk.decode('utf-8', errors='replace')
        # common attrs
        for attr in ('text', 'content', 'delta', 'message'):
            if hasattr(chunk, attr):
                val = getattr(chunk, attr)
                if isinstance(val, str):
                    return val
                if isinstance(val, dict):
                    # nested content possibilities
                    for k in ('content', 'text'):
                        if k in val and isinstance(val[k], str):
                            return val[k]
                    # join any list-like parts
                    parts = []
                    for v in val.values():
                        if isinstance(v, str):
                            parts.append(v)
                    if parts:
                        return ''.join(parts)
                if isinstance(val, list):
                    parts = []
                    for item in val:
                        if isinstance(item, str):
                            parts.append(item)
                        elif isinstance(item, dict) and 'text' in item:
                            parts.append(item.get('text') or '')
                    if parts:
                        return ''.join(parts)
        # finally try __dict__ inspection
        d = getattr(chunk, '__dict__', None)
        if isinstance(d, dict):
            for k in ('text', 'content'):
                v = d.get(k)
                if isinstance(v, str):
                    return v
        return ''
    except Exception:
        return ''


async def main_async(prompt, model=None):
    if Chat is None:
        print("ERROR: chatlas not found or can't import chatlas._chat.Chat.\n" \
              "Install your project's dependencies (pip install -r requirements.txt) and retry.")
        return 2

    # Instantiate Chat; keep minimal and let Chat pick defaults from env if possible
    try:
        chat = Chat(model=model) if model else Chat()
    except TypeError:
        # fallback: some versions may expect different constructor args
        try:
            chat = Chat()
        except Exception as e:
            print("Failed to construct Chat client:", e)
            traceback.print_exc()
            return 3

    char_count = len(prompt) if isinstance(prompt, str) else 0
    tool_calls = 0
    start = time.time()

    print(f"Sending prompt (len={len(prompt)}):\n{prompt}\n---\n")

    try:
        stream = await chat.stream_async(prompt, content='all')
    except Exception as e:
        print("Failed to start stream:", e)
        traceback.print_exc()
        return 4

    try:
        async for chunk in stream:
            # Print a compact representation so you can see progress
            print(repr(chunk))

            # accumulate characters found in the chunk
            text = _extract_text_from_chunk(chunk)
            if text:
                char_count += len(text)

            # detect ContentToolResult-like messages by class name
            try:
                cls = getattr(chunk, '__class__', None)
                if cls is not None and 'ContentToolResult' in str(cls):
                    tool_calls += 1
            except Exception:
                pass

        elapsed = time.time() - start
        est_tokens = int(char_count / 4)

        print("\n--- Summary ---")
        print(f"Tool calls: {tool_calls}")
        print(f"Total chars (incl. prompt): {char_count}")
        print(f"Est. tokens (chars/4): {est_tokens}")
        print(f"Elapsed: {elapsed:.2f}s")
        return 0
    except Exception as e:
        print("Error while streaming:", e)
        traceback.print_exc()
        return 5


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python scripts/test_stream_metrics.py \"Your prompt\" [--model MODEL]")
        return 1

    # allow optional --model flag
    model = None
    if argv and argv[0] == '--model':
        if len(argv) < 3:
            print("Usage: --model MODEL prompt")
            return 1
        model = argv[1]
        prompt = ' '.join(argv[2:])
    else:
        prompt = ' '.join(argv)

    return asyncio.run(main_async(prompt, model=model))


if __name__ == '__main__':
    raise SystemExit(main())
