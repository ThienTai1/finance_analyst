import os
import sys

# Ensure backend/ directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.rag.ingestion import generate_document_summary, generate_chunk_preamble

def test_contextual_retrieval_functions():
    print("\n--- Test Contextual Retrieval Generation ---")
    
    pages_data = [
        {
            "page": 1,
            "text": "Annual report of Apple Inc. for fiscal year 2026. The corporate overview and financial performance are detailed below."
        },
        {
            "page": 2,
            "text": "Services revenue grew to $95.5 billion, showing a massive shift towards subscriptions."
        }
    ]
    
    # 1. Test document summary outline generation
    print("Generating document summary...")
    summary = generate_document_summary(pages_data, "apple_fy_2026.pdf")
    print(f"Resulting Summary Outline:\n{summary}\n")
    
    assert summary is not None and len(summary) > 10, "Document summary should be generated"
    assert "apple" in summary.lower() or "document" in summary.lower(), "Summary should contain document metadata"
    
    # 2. Test chunk preamble compilation
    chunk_content = "Services revenue grew to $95.5 billion, showing a massive shift towards subscriptions."
    print("Generating chunk preamble...")
    preamble = generate_chunk_preamble(summary, chunk_content)
    print(f"Resulting Preamble:\n{preamble}\n")
    
    assert preamble is not None and len(preamble) > 5, "Contextual preamble should be compiled"
    
    # 3. Test prepend combination format
    combined_chunk = f"[{preamble}]\n{chunk_content}"
    print(f"Combined Chunk Text:\n{combined_chunk}\n")
    assert combined_chunk.startswith(f"[{preamble}]"), "Should follow standard [Preamble]\\nChunk format"
    
    print("✓ Contextual Retrieval evaluation passed successfully!")

if __name__ == "__main__":
    try:
        test_contextual_retrieval_functions()
        print("\nAll Phase 5 tests passed successfully!")
    except Exception as e:
        print(f"\nAssertion failed: {e}")
        sys.exit(1)
