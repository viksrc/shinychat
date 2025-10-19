"""
MCP Tool Testing with inspect.ai Framework
Tests sales data tool calling across multiple models with latency and accuracy metrics
"""
import asyncio
import time
import json
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from chatlas import ChatOpenRouter
import os
import sys
from pathlib import Path

# Model list to test (7 models - added GPT-4o)
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
class TestResult:
    """Store test results for a single test case"""
    model: str
    test_name: str
    success: bool
    latency_ms: float
    tool_called: bool
    correct_data: bool
    error: str = ""
    response_text: str = ""
    num_products: int = 0


class MCPToolTester:
    """Test MCP tool calling across different models"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.results: List[TestResult] = []
        
    async def setup_llm_with_mcp(self, model_name: str) -> ChatOpenRouter:
        """Create LLM instance and register MCP tools"""
        llm = ChatOpenRouter(
            model=model_name,
            api_key=self.api_key,
            system_prompt=(
                "You are a helpful assistant. When the user asks for sales data or sales figures, "
                "use the 'get_sales_data' tool to retrieve the information. Always use tools available "
                "to you when they can help answer the user's question."
            )
        )
        
        # Register MCP server
        server_path = str(Path(__file__).with_name("mcp_sales_server.py"))
        await llm.register_mcp_tools_stdio_async(
            command=sys.executable,
            args=["-u", server_path],
            name="sales_mcp",
            include_tools=("get_sales_data",),
        )
        
        return llm
    
    async def test_basic_tool_call(self, model_name: str) -> TestResult:
        """Test 1: Basic tool call with default parameters"""
        test_name = "basic_tool_call"
        start_time = time.time()
        
        try:
            llm = await self.setup_llm_with_mcp(model_name)
            
            # Make the request
            response = await llm.chat_async("Show me the sales data")
            response_text = await response.get_content()
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Check if tool was called
            from chatlas import ContentToolResult
            turns = llm.get_turns()
            tool_called = False
            correct_data = False
            num_products = 0
            
            for turn in turns[-3:]:
                if hasattr(turn, 'contents'):
                    for content in turn.contents:
                        if isinstance(content, ContentToolResult):
                            if content.name == 'get_sales_data':
                                tool_called = True
                                # Parse JSON to verify data structure
                                import re
                                tool_value = content.value
                                if isinstance(tool_value, str):
                                    json_match = re.search(r'JSON:\s*(\[.*?\])', tool_value, re.DOTALL)
                                    if json_match:
                                        try:
                                            sales_data = json.loads(' '.join(json_match.group(1).split()))
                                            num_products = len(sales_data)
                                            # Verify structure
                                            if all('Product' in item and 'Sales' in item for item in sales_data):
                                                correct_data = True
                                        except:
                                            pass
            
            return TestResult(
                model=model_name,
                test_name=test_name,
                success=tool_called and correct_data,
                latency_ms=latency_ms,
                tool_called=tool_called,
                correct_data=correct_data,
                response_text=response_text[:200],
                num_products=num_products
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return TestResult(
                model=model_name,
                test_name=test_name,
                success=False,
                latency_ms=latency_ms,
                tool_called=False,
                correct_data=False,
                error=str(e)
            )
    
    async def test_parameterized_call(self, model_name: str, num_products: int = 10) -> TestResult:
        """Test 2: Tool call with specific number of products"""
        test_name = f"parameterized_call_{num_products}products"
        start_time = time.time()
        
        try:
            llm = await self.setup_llm_with_mcp(model_name)
            
            # Make the request with parameter
            response = await llm.chat_async(f"Show me sales data for {num_products} products")
            response_text = await response.get_content()
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Check if tool was called with correct parameters
            from chatlas import ContentToolResult
            turns = llm.get_turns()
            tool_called = False
            correct_data = False
            actual_products = 0
            
            for turn in turns[-3:]:
                if hasattr(turn, 'contents'):
                    for content in turn.contents:
                        if isinstance(content, ContentToolResult):
                            if content.name == 'get_sales_data':
                                tool_called = True
                                import re
                                tool_value = content.value
                                if isinstance(tool_value, str):
                                    json_match = re.search(r'JSON:\s*(\[.*?\])', tool_value, re.DOTALL)
                                    if json_match:
                                        try:
                                            sales_data = json.loads(' '.join(json_match.group(1).split()))
                                            actual_products = len(sales_data)
                                            # Check if correct number of products
                                            if actual_products == num_products:
                                                correct_data = True
                                        except:
                                            pass
            
            return TestResult(
                model=model_name,
                test_name=test_name,
                success=tool_called and correct_data,
                latency_ms=latency_ms,
                tool_called=tool_called,
                correct_data=correct_data,
                response_text=response_text[:200],
                num_products=actual_products
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return TestResult(
                model=model_name,
                test_name=test_name,
                success=False,
                latency_ms=latency_ms,
                tool_called=False,
                correct_data=False,
                error=str(e)
            )
    
    async def test_implicit_tool_call(self, model_name: str) -> TestResult:
        """Test 3: Implicit tool call (asking for sales without explicit request)"""
        test_name = "implicit_tool_call"
        start_time = time.time()
        
        try:
            llm = await self.setup_llm_with_mcp(model_name)
            
            # Make an implicit request
            response = await llm.chat_async("What are the product sales numbers?")
            response_text = await response.get_content()
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Check if tool was called
            from chatlas import ContentToolResult
            turns = llm.get_turns()
            tool_called = False
            correct_data = False
            num_products = 0
            
            for turn in turns[-3:]:
                if hasattr(turn, 'contents'):
                    for content in turn.contents:
                        if isinstance(content, ContentToolResult):
                            if content.name == 'get_sales_data':
                                tool_called = True
                                import re
                                tool_value = content.value
                                if isinstance(tool_value, str):
                                    json_match = re.search(r'JSON:\s*(\[.*?\])', tool_value, re.DOTALL)
                                    if json_match:
                                        try:
                                            sales_data = json.loads(' '.join(json_match.group(1).split()))
                                            num_products = len(sales_data)
                                            if all('Product' in item and 'Sales' in item for item in sales_data):
                                                correct_data = True
                                        except:
                                            pass
            
            return TestResult(
                model=model_name,
                test_name=test_name,
                success=tool_called and correct_data,
                latency_ms=latency_ms,
                tool_called=tool_called,
                correct_data=correct_data,
                response_text=response_text[:200],
                num_products=num_products
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return TestResult(
                model=model_name,
                test_name=test_name,
                success=False,
                latency_ms=latency_ms,
                tool_called=False,
                correct_data=False,
                error=str(e)
            )
    
    async def test_multiple_calls(self, model_name: str) -> TestResult:
        """Test 4: Multiple sequential tool calls"""
        test_name = "multiple_sequential_calls"
        start_time = time.time()
        
        try:
            llm = await self.setup_llm_with_mcp(model_name)
            
            # First call
            await llm.chat_async("Show me sales data for 3 products")
            
            # Second call
            response = await llm.chat_async("Now show me sales data for 7 products")
            response_text = await response.get_content()
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Check if both tools were called
            from chatlas import ContentToolResult
            turns = llm.get_turns()
            tool_call_count = 0
            correct_data = False
            
            for turn in turns:
                if hasattr(turn, 'contents'):
                    for content in turn.contents:
                        if isinstance(content, ContentToolResult):
                            if content.name == 'get_sales_data':
                                tool_call_count += 1
            
            # Last call should have 7 products
            for turn in turns[-3:]:
                if hasattr(turn, 'contents'):
                    for content in turn.contents:
                        if isinstance(content, ContentToolResult):
                            if content.name == 'get_sales_data':
                                import re
                                tool_value = content.value
                                if isinstance(tool_value, str):
                                    json_match = re.search(r'JSON:\s*(\[.*?\])', tool_value, re.DOTALL)
                                    if json_match:
                                        try:
                                            sales_data = json.loads(' '.join(json_match.group(1).split()))
                                            if len(sales_data) == 7:
                                                correct_data = True
                                        except:
                                            pass
            
            return TestResult(
                model=model_name,
                test_name=test_name,
                success=tool_call_count >= 2 and correct_data,
                latency_ms=latency_ms,
                tool_called=tool_call_count >= 2,
                correct_data=correct_data,
                response_text=f"Tool called {tool_call_count} times",
                num_products=tool_call_count
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return TestResult(
                model=model_name,
                test_name=test_name,
                success=False,
                latency_ms=latency_ms,
                tool_called=False,
                correct_data=False,
                error=str(e)
            )
    
    async def run_all_tests_for_model(self, model_name: str):
        """Run all test cases for a single model"""
        print(f"\n{'='*80}")
        print(f"Testing model: {model_name}")
        print(f"{'='*80}")
        
        # Test 1: Basic tool call
        print(f"  Test 1: Basic tool call...")
        result1 = await self.test_basic_tool_call(model_name)
        self.results.append(result1)
        print(f"    ✅ Success: {result1.success}, Latency: {result1.latency_ms:.0f}ms")
        
        # Test 2: Parameterized call (10 products)
        print(f"  Test 2: Parameterized call (10 products)...")
        result2 = await self.test_parameterized_call(model_name, 10)
        self.results.append(result2)
        print(f"    ✅ Success: {result2.success}, Latency: {result2.latency_ms:.0f}ms")
        
        # Test 3: Implicit tool call
        print(f"  Test 3: Implicit tool call...")
        result3 = await self.test_implicit_tool_call(model_name)
        self.results.append(result3)
        print(f"    ✅ Success: {result3.success}, Latency: {result3.latency_ms:.0f}ms")
        
        # Test 4: Multiple sequential calls
        print(f"  Test 4: Multiple sequential calls...")
        result4 = await self.test_multiple_calls(model_name)
        self.results.append(result4)
        print(f"    ✅ Success: {result4.success}, Latency: {result4.latency_ms:.0f}ms")
    
    async def run_all_tests(self):
        """Run all tests for all models"""
        print("\n" + "="*80)
        print("MCP TOOL TESTING WITH INSPECT.AI FRAMEWORK")
        print("="*80)
        
        for model in MODELS_TO_TEST:
            try:
                await self.run_all_tests_for_model(model)
            except Exception as e:
                print(f"  ❌ Failed to test {model}: {e}")
        
        self.print_statistics()
        self.save_results()
    
    def print_statistics(self):
        """Print comprehensive statistics"""
        print("\n" + "="*80)
        print("COMPREHENSIVE STATISTICS")
        print("="*80)
        
        # Group results by model
        model_stats = {}
        for result in self.results:
            if result.model not in model_stats:
                model_stats[result.model] = {
                    'successes': 0,
                    'failures': 0,
                    'latencies': [],
                    'tool_calls': 0,
                    'correct_data': 0
                }
            
            stats = model_stats[result.model]
            if result.success:
                stats['successes'] += 1
            else:
                stats['failures'] += 1
            
            stats['latencies'].append(result.latency_ms)
            if result.tool_called:
                stats['tool_calls'] += 1
            if result.correct_data:
                stats['correct_data'] += 1
        
        # Print summary table
        print("\n📊 MODEL COMPARISON TABLE")
        print("-" * 120)
        print(f"{'Model':<40} {'Success Rate':<15} {'Avg Latency':<15} {'Tool Calls':<15} {'Accuracy':<15}")
        print("-" * 120)
        
        for model, stats in sorted(model_stats.items()):
            total_tests = stats['successes'] + stats['failures']
            success_rate = (stats['successes'] / total_tests * 100) if total_tests > 0 else 0
            avg_latency = statistics.mean(stats['latencies']) if stats['latencies'] else 0
            accuracy = (stats['correct_data'] / total_tests * 100) if total_tests > 0 else 0
            
            print(f"{model:<40} {success_rate:>6.1f}%        {avg_latency:>8.0f}ms      {stats['tool_calls']:>3}/{total_tests:<8} {accuracy:>6.1f}%")
        
        print("-" * 120)
        
        # Latency rankings
        print("\n⚡ LATENCY RANKINGS (Fastest to Slowest)")
        print("-" * 80)
        latency_ranking = []
        for model, stats in model_stats.items():
            avg_latency = statistics.mean(stats['latencies']) if stats['latencies'] else float('inf')
            latency_ranking.append((model, avg_latency))
        
        latency_ranking.sort(key=lambda x: x[1])
        for rank, (model, latency) in enumerate(latency_ranking, 1):
            print(f"  {rank}. {model:<45} {latency:>8.0f}ms")
        
        # Accuracy rankings
        print("\n🎯 ACCURACY RANKINGS (Most to Least Accurate)")
        print("-" * 80)
        accuracy_ranking = []
        for model, stats in model_stats.items():
            total_tests = stats['successes'] + stats['failures']
            accuracy = (stats['correct_data'] / total_tests * 100) if total_tests > 0 else 0
            accuracy_ranking.append((model, accuracy, stats['correct_data'], total_tests))
        
        accuracy_ranking.sort(key=lambda x: x[1], reverse=True)
        for rank, (model, accuracy, correct, total) in enumerate(accuracy_ranking, 1):
            print(f"  {rank}. {model:<45} {accuracy:>6.1f}% ({correct}/{total})")
        
        # Best overall
        print("\n🏆 BEST OVERALL MODEL")
        print("-" * 80)
        best_model = None
        best_score = -1
        
        for model, stats in model_stats.items():
            total_tests = stats['successes'] + stats['failures']
            if total_tests == 0:
                continue
            
            success_rate = stats['successes'] / total_tests
            avg_latency = statistics.mean(stats['latencies'])
            # Normalize latency (lower is better) and combine with success rate
            score = success_rate * 0.7 + (1 / (avg_latency / 1000)) * 0.3
            
            if score > best_score:
                best_score = score
                best_model = (model, success_rate * 100, avg_latency)
        
        if best_model:
            model, success_rate, latency = best_model
            print(f"  {model}")
            print(f"  Success Rate: {success_rate:.1f}%")
            print(f"  Avg Latency: {latency:.0f}ms")
    
    def save_results(self):
        """Save detailed results to JSON file"""
        results_data = {
            'test_run_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'models_tested': len(set(r.model for r in self.results)),
            'total_tests': len(self.results),
            'results': [asdict(r) for r in self.results]
        }
        
        output_file = 'mcp_test_results.json'
        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {output_file}")


async def main():
    """Main entry point"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY environment variable not set")
        return
    
    tester = MCPToolTester(api_key)
    await tester.run_all_tests()
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
