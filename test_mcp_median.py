#!/usr/bin/env python3
"""
MCP Tool Testing - Median Latency Analysis
Tests each model 3 times and reports median latency

NOTE: You will see async generator cleanup errors after tests complete.
These are cosmetic only - see MCP_CLEANUP_ISSUE.md for details.
Use ./test_mcp_median_clean.sh for filtered output.
"""

import asyncio
import time
import statistics
import sys
import os
import warnings
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from chatlas import ChatOpenRouter

# Suppress async generator cleanup warnings (known MCP stdio issue in parallel contexts)
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*async_generator.*")
warnings.filterwarnings("ignore", message=".*coroutine.*was never awaited.*")

# Set OpenRouter API key (from start_app.sh - verified working)
os.environ["OPENROUTER_API_KEY"] = "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"

# All models to test (7 models - added GPT-4o)
MODELS_TO_TEST = [
    "anthropic/claude-sonnet-4",
    "openai/gpt-4o",
    "openai/gpt-4.1",
    "openai/gpt-oss-120b",
    "qwen/qwen3-30b-a3b",
    "qwen/qwen3-30b-a3b-thinking-2507",
    "deepseek/deepseek-chat-v3.1",
]

@dataclass
class TestRun:
    """Single test run result"""
    model: str
    run_number: int
    latency_ms: float
    success: bool
    tool_called: bool
    error: Optional[str] = None

class MCPMedianTester:
    def __init__(self):
        self.results = []
        self.server_path = str(Path(__file__).with_name("mcp_sales_server.py"))

    async def run_single_test(self, model: str, run_number: int) -> TestRun:
        """Run a single test and measure latency"""
        print(f"    Run {run_number}/3...", end=" ", flush=True)
        
        start_time = time.time()
        success = False
        tool_called = False
        error_msg = None
        llm = None
        
        try:
            # Create LLM
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable not set")
            llm = ChatOpenRouter(model=model, api_key=api_key)
            
            # Register MCP tools using the proper method
            await llm.register_mcp_tools_stdio_async(
                command=sys.executable,
                args=["-u", self.server_path],
                name="sales_mcp",
                include_tools=("get_sales_data",),
            )
            
            # Simple test: ask for sales data
            response = await llm.stream_async("Get me the sales data")
            
            # Consume the stream (may fail for some models with bad JSON)
            try:
                async for chunk in response:
                    pass
                success = True
            except ValueError as stream_error:
                # Some models (like Qwen) generate invalid JSON but still call tools
                error_msg = str(stream_error)[:100]
                # Don't mark as complete success, but check if tool was called anyway
                success = False
            
            # Check if tool was called - look for ContentToolRequest or ContentToolResult
            # This works even if streaming failed
            if llm:
                turns = llm.get_turns()
                for turn in turns:
                    if hasattr(turn, 'contents'):
                        for content in turn.contents:
                            content_type = type(content).__name__
                            if content_type in ('ContentToolRequest', 'ContentToolResult'):
                                tool_called = True
                                break
                    if tool_called:
                        break
                    
        except Exception as e:
            error_msg = str(e)[:100]
        finally:
            # Cleanup: Give async generators time to close properly
            if llm:
                # Clear the MCP tools to trigger cleanup
                try:
                    llm._tools = {}  # Clear registered tools
                except:
                    pass
                del llm
                # Small delay to allow async cleanup to complete
                await asyncio.sleep(0.1)
        
        latency_ms = (time.time() - start_time) * 1000
        
        status = "✅" if success and tool_called else "❌"
        error_display = f" [{error_msg[:50]}]" if error_msg else ""
        print(f"{status} {latency_ms:.0f}ms{error_display}")
        
        return TestRun(
            model=model,
            run_number=run_number,
            latency_ms=latency_ms,
            success=success,
            tool_called=tool_called,
            error=error_msg
        )

    async def test_model_three_times(self, model: str):
        """Test a model 3 times and collect results"""
        print(f"\n{'='*80}")
        print(f"Testing: {model}")
        print(f"{'='*80}")
        
        runs = []
        for i in range(1, 4):
            result = await self.run_single_test(model, i)
            runs.append(result)
            self.results.append(result)
            
            # Small delay between runs
            if i < 3:
                await asyncio.sleep(1)
        
        return runs

    def calculate_median_latency(self, model: str) -> tuple[float, int, int]:
        """Calculate median latency for a model"""
        model_results = [r for r in self.results if r.model == model]
        latencies = [r.latency_ms for r in model_results]
        successful = sum(1 for r in model_results if r.success and r.tool_called)
        total = len(model_results)
        
        if not latencies:
            return 0.0, 0, 0
        
        median = statistics.median(latencies)
        return median, successful, total

    def print_results_table(self):
        """Print results in a formatted table"""
        print(f"\n\n{'='*80}")
        print("MEDIAN LATENCY ANALYSIS (3 runs per model)")
        print(f"{'='*80}\n")
        
        # Collect data for all models
        model_data = []
        for model in MODELS_TO_TEST:
            median, successful, total = self.calculate_median_latency(model)
            if total > 0:
                model_data.append({
                    'model': model,
                    'median': median,
                    'successful': successful,
                    'total': total
                })
        
        # Sort by median latency (fastest first)
        model_data.sort(key=lambda x: x['median'])
        
        # Print table header
        print(f"{'Rank':<6} {'Model':<45} {'Median Latency':<18} {'Success Rate'}")
        print(f"{'-'*6} {'-'*45} {'-'*18} {'-'*12}")
        
        # Print each model
        for i, data in enumerate(model_data, 1):
            model_name = data['model']
            median_ms = data['median']
            median_sec = median_ms / 1000
            success_rate = f"{data['successful']}/{data['total']}"
            
            # Add medal emoji for top 3
            rank_icon = ""
            if i == 1:
                rank_icon = "🥇"
            elif i == 2:
                rank_icon = "🥈"
            elif i == 3:
                rank_icon = "🥉"
            
            print(f"{rank_icon:<6} {model_name:<45} {median_ms:>8.0f}ms ({median_sec:>4.1f}s)  {success_rate}")
        
        print(f"\n{'='*80}\n")
        
        # Show fastest and slowest
        if model_data:
            fastest = model_data[0]
            slowest = model_data[-1]
            
            print(f"⚡ FASTEST: {fastest['model']}")
            print(f"   Median: {fastest['median']:.0f}ms ({fastest['median']/1000:.1f}s)")
            print()
            print(f"🐌 SLOWEST: {slowest['model']}")
            print(f"   Median: {slowest['median']:.0f}ms ({slowest['median']/1000:.1f}s)")
            print()
            
            if fastest['median'] > 0:
                speedup = slowest['median'] / fastest['median']
                print(f"📊 Speed Difference: {speedup:.1f}x slower")

async def main():
    tester = MCPMedianTester()
    
    print("🧪 MCP Median Latency Test (PARALLEL)")
    print("=" * 80)
    print(f"Testing {len(MODELS_TO_TEST)} models in parallel, 3 runs each...")
    print("This will be much faster than sequential testing!")
    print()
    
    # Test all models in parallel using asyncio.gather
    print("🚀 Starting parallel tests...")
    await asyncio.gather(*[
        tester.test_model_three_times(model) 
        for model in MODELS_TO_TEST
    ])
    
    # Print final results table
    print("\n" + "=" * 80)
    tester.print_results_table()

if __name__ == "__main__":
    asyncio.run(main())
