import os
import sys
import logging

# Configure logging to see self-correction logs in stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Ensure backend/ directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.rag.database import get_qdrant_client, COLLECTION_NAME
from app.agent.tools import vector_search
from app.config import AGENTIC_QUERY_REWRITE_ENABLED, RERANK_MIN_PASSING_SCORE

def test_self_correction_pipeline():
    print("\n--- Test Agentic Query Self-Correction Loop ---")
    print(f"AGENTIC_QUERY_REWRITE_ENABLED: {AGENTIC_QUERY_REWRITE_ENABLED}")
    print(f"RERANK_MIN_PASSING_SCORE: {RERANK_MIN_PASSING_SCORE}")
    
    # 1. Initialize Client and Seed Documents
    print("Initializing Qdrant client and seeding test documents...")
    client = get_qdrant_client()
    
    documents = [
        "Goldman Sachs announced a record-breaking net revenue of $12.5 billion for the second quarter of fiscal year 2026.",
        "Renewable energy investments saw a massive 45% increase in global market funding this fiscal year.",
        "Under the leadership of CEO Jane Doe, the organization is pivoting heavily towards zero-emission logistics."
    ]
    metadata = [
        {"source": "report_gs.pdf", "page": 1, "chunk_idx": 0},
        {"source": "report_energy.pdf", "page": 2, "chunk_idx": 0},
        {"source": "report_logistics.pdf", "page": 5, "chunk_idx": 0}
    ]
    ids = [
        101,
        102,
        103
    ]
    
    client.add(
        collection_name=COLLECTION_NAME,
        documents=documents,
        metadata=metadata,
        ids=ids
    )
    print("Indexed test documents successfully.")
    
    # 2. Perform a vague query that will return no/poor results initially
    # We use a query string containing nonsense/unrelated terms but provide a rich original_query
    failed_query = "xyzonlinemacroeconomicnonsense profits"
    original_query = "What is Goldman Sachs' net revenue for Q2?"
    
    print(f"\nExecuting VectorSearch with failed query: '{failed_query}' and original goal: '{original_query}'")
    search_result = vector_search(failed_query, original_query=original_query)
    
    print("\n--- Search Results ---")
    print(search_result)
    print("----------------------")
    
    # Verification assertions
    assert "Goldman Sachs" in search_result, "Should have triggered reformulation and successfully retrieved Goldman Sachs document!"
    assert "$12.5 billion" in search_result, "Should retrieve the exact content from the seeded Goldman Sachs record."
    
    print("\n✓ Agentic Query Self-Correction test passed successfully!")

if __name__ == "__main__":
    try:
        test_self_correction_pipeline()
        print("\nAll Phase 6 tests passed successfully!")
    except Exception as e:
        print(f"\nAssertion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
