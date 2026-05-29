import os
import sys

# Ensure backend/ directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.rag.database import get_qdrant_client, COLLECTION_NAME
from app.agent.tools import vector_search

def test_hybrid_search_pipeline():
    print("\n--- Test Hybrid Search & Index Tuning Pipeline ---")
    
    # 1. Initialize Client (forces sparse model initialization and collection recreation if needed)
    print("Initializing Qdrant client and checking/recreating collection...")
    client = get_qdrant_client()
    
    # Verify collection state
    coll_info = client.get_collection(COLLECTION_NAME)
    print(f"Collection: '{COLLECTION_NAME}'")
    print(f"Vectors Config: {coll_info.config.params.vectors}")
    print(f"Sparse Vectors Config: {coll_info.config.params.sparse_vectors}")
    print(f"HNSW Config (M): {coll_info.config.hnsw_config.m}")
    print(f"HNSW Config (EF Construct): {coll_info.config.hnsw_config.ef_construct}")
    
    # Assert collection configurations match config.py values
    assert coll_info.config.params.sparse_vectors is not None, "Sparse vectors must be configured"
    assert coll_info.config.hnsw_config.m == 16, f"Expected HNSW M=16, got {coll_info.config.hnsw_config.m}"
    
    # 2. Upload dummy documents to check insertion
    print("\nIndexing test documents...")
    documents = [
        "Goldman Sachs announced a record-breaking net revenue of $12.5 billion for the second quarter.",
        "Renewable energy investments saw a massive 45% increase in global market funding this fiscal year.",
        "Under the leadership of CEO Jane Doe, the organization is pivoting heavily towards zero-emission logistics."
    ]
    metadata = [
        {"source": "report_gs.pdf", "page": 1, "chunk_idx": 0},
        {"source": "report_energy.pdf", "page": 2, "chunk_idx": 0},
        {"source": "report_logistics.pdf", "page": 5, "chunk_idx": 0}
    ]
    ids = [
        1,
        2,
        3
    ]
    
    client.add(
        collection_name=COLLECTION_NAME,
        documents=documents,
        metadata=metadata,
        ids=ids
    )
    print("Indexed 3 test documents successfully.")
    
    # 3. Perform a keyword-heavy hybrid query
    # "Goldman Sachs" should hit the first document strongly via sparse matching
    print("\nExecuting VectorSearch for: 'Goldman Sachs revenue'...")
    search_result = vector_search("Goldman Sachs revenue")
    
    print("\nSearch results:")
    print(search_result)
    
    assert "Goldman Sachs" in search_result, "Should have retrieved Goldman Sachs document"
    print("\n✓ Hybrid Search integration tests passed successfully!")

if __name__ == "__main__":
    try:
        test_hybrid_search_pipeline()
        print("\nAll Phase 2 tests passed successfully!")
    except Exception as e:
        print(f"\nAssertion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
