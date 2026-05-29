import os
import sys
import logging

# Configure logging to see graph extraction logs in stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Ensure backend/ directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.rag.graph import extract_entities_and_relations_sync, index_graph_relations, graph_search
from app.agent.tools import vector_search
from app.rag.database import get_qdrant_client, COLLECTION_NAME

def test_graph_rag_pipeline():
    print("\n--- Test GraphRAG Entity-Relation Ingestion & Fusion ---")
    
    # 1. Test Entity Relationship Extraction
    test_text = (
        "Apple Inc. was founded by Steve Jobs and Steve Wozniak. The corporate overview indicates "
        "that Services revenue grew to $95.5 billion in fiscal year 2026 under CEO Tim Cook."
    )
    
    print("\nExecuting entity-relation extraction on test text...")
    relations = extract_entities_and_relations_sync(test_text)
    print(f"Extracted relations:\n{json_dumps(relations)}")
    
    assert isinstance(relations, list), "Extraction should return a list of triples"
    assert len(relations) > 0, "Should extract at least one relationship triple"
    
    # 2. Index relationships under a stable test chunk ID
    import uuid
    test_chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "test_chunk_apple_999"))
    print(f"\nIndexing relations under chunk ID: {test_chunk_id}...")
    index_graph_relations(test_chunk_id, relations)
    
    # 3. Test Graph Search lookup
    search_query = "What is Apple Inc.'s services revenue?"
    print(f"\nExecuting graph_search for: '{search_query}'...")
    graph_facts = graph_search(search_query)
    print("\nGraphRAG retrieved facts:")
    print(graph_facts)
    print("-------------------------")
    
    assert "Apple" in graph_facts or "Tim Cook" in graph_facts or "$95.5" in graph_facts, "Should retrieve relevant relational facts from the graph"
    
    # 4. Seed Qdrant Vector DB to check hybrid fusion
    print("\nSeeding Qdrant vector store with test chunk to check hybrid search fusion...")
    client = get_qdrant_client()
    client.add(
        collection_name=COLLECTION_NAME,
        documents=[test_text],
        metadata=[{"source": "apple_news.pdf", "page": 1, "chunk_idx": 0}],
        ids=[test_chunk_id]
    )
    print("Vector document seeded successfully.")
    
    # 5. Execute vector_search and check Hybrid Fusion format
    print(f"\nExecuting hybrid VectorSearch for: '{search_query}'...")
    fused_results = vector_search(search_query)
    print("\nFused Hybrid Search output:")
    print(fused_results)
    print("---------------------------")
    
    assert "Knowledge Graph Relational Facts" in fused_results, "Should include GraphRAG relational section"
    assert "Financial Report Segments" in fused_results, "Should include standard Vector Search section"
    assert "Apple Inc." in fused_results, "Should retrieve indexed Apple data"
    
    print("\n✓ GraphRAG Entity-Relation Ingestion & Fusion pipeline verified successfully!")

def json_dumps(obj):
    import json
    return json.dumps(obj, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    try:
        test_graph_rag_pipeline()
        print("\nAll Phase 7 tests passed successfully!")
    except Exception as e:
        print(f"\nAssertion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
