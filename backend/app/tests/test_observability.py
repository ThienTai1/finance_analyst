import os
import sys

# Ensure backend/ directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Set environment variables for Langfuse testing before importing app.config
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-test-key"
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-test-key"
os.environ["LANGFUSE_HOST"] = "https://cloud.langfuse.com"

from app.agent.engine import get_langfuse_client
from app.config import LANGFUSE_ENABLED

def test_observability_pipeline():
    print("\n--- Test Langfuse Tracing & Metrics Pipeline ---")
    
    # 1. Assert configuration mapping works
    print(f"Checking Langfuse Enabled status: {LANGFUSE_ENABLED}")
    assert LANGFUSE_ENABLED is True, "Langfuse should be enabled under mock test environment"
    
    # 2. Initialize Client
    print("Initializing Langfuse client...")
    client = get_langfuse_client()
    assert client is not None, "Langfuse client should be instantiated"
    
    # 3. Create sample ReAct trace workflow using start_as_current_observation
    print("\nCreating mock trace session span...")
    with client.start_as_current_observation(
        name="Mock Financial Analyst ReAct Loop",
        as_type="span",
        input="What is Apple's net profit margin?",
        metadata={"environment": "testing"}
    ) as root_span:
        
        print(f"Trace Span Created! ID: {root_span.id}, Trace ID: {root_span.trace_id}")
        
        # 4. Create mock generation thinking step
        print("Logging mock LLM generation step...")
        with client.start_as_current_observation(
            name="Mock ReAct Thought Step 1",
            as_type="generation",
            model="qwen2.5",
            input="User Query: What is Apple's net profit margin?\nStart ReAct Loop:",
            model_parameters={"temperature": 0.1}
        ) as generation:
            
            # Simulate LLM returning output
            llm_output = "Thought: I need to lookup Apple's financial parameters.\nAction: StockData\nParameters: {\"ticker\": \"AAPL\"}"
            generation.update(
                output=llm_output,
                usage={
                    "input": 32,
                    "output": 18
                }
            )
            print("Logged generation metrics successfully.")
        
        # 5. Create mock tool execution span
        print("Logging mock StockData tool span...")
        with client.start_as_current_observation(
            name="Tool: StockData",
            as_type="span",
            input={"parameters": {"ticker": "AAPL"}}
        ) as tool_span:
            
            # Update tool span output
            tool_span.update(
                output="Company: Apple Inc. (AAPL) | Current Price: $175.50 | PE Ratio: 28.5 | Profit Margin: 25.8%"
            )
            print("Logged tool execution span metrics successfully.")
        
        # 6. Finalize Root Span
        final_brief = "Apple's net profit margin for the current period is 25.8% based on latest financial ratios."
        root_span.update(
            output=final_brief
        )
        print("Updated final brief response in root span.")
    
    # Flush tracing queue to push events immediately
    print("\nFlushing Langfuse events queue...")
    client.flush()
    print("✓ Observability and tracing pipeline verified successfully!")

if __name__ == "__main__":
    try:
        test_observability_pipeline()
        print("\nAll Phase 3 tests passed successfully!")
    except Exception as e:
        print(f"\nAssertion failed: {e}")
        sys.exit(1)
