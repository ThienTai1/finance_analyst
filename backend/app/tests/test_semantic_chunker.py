import os
import sys

# Ensure backend/ directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.rag.ingestion import split_into_sentences, semantic_chunk_text

def test_sentence_splitting():
    text = (
        "Apple Inc. reported outstanding financial results for Q3 2026. "
        "The company's revenue reached $95.5 billion, representing an 8% growth year-over-year. "
        "We are also seeing incredible growth in Services. "
        "Furthermore, Dr. Arthur Levinson commented that key indicators remain strong in the U.S. and Europe."
    )
    sentences = split_into_sentences(text)
    
    print("\n--- Test Sentence Splitting ---")
    for i, s in enumerate(sentences):
        print(f"Sentence {i+1}: {s}")
        
    # Check that Inc. and U.S. and Dr. did not cause premature splitting
    assert len(sentences) == 4, f"Expected 4 sentences, got {len(sentences)}"
    assert "Apple Inc." in sentences[0]
    assert "U.S. and Europe." in sentences[3]
    print("✓ Sentence splitting tests passed successfully!")

def test_semantic_chunker():
    # Process text consisting of two distinct thematic parts
    pages_data = [
        {
            "page": 1,
            "text": (
                "Apple Inc. designs, manufactures and markets smartphones, personal computers, tablets, wearables and accessories. "
                "The Company also sells various related services. "
                "Its principal products include iPhone, Mac, iPad, and Wearables. "
                "Services include Advertising, AppleCare, Cloud Services, Digital Content, and Payment Services. "
                "The corporate headquarters is located in Cupertino, California."
            )
        },
        {
            "page": 2,
            "text": (
                "Global climate change represents a significant long-term risk to supply chain logistics and infrastructure. "
                "Extreme weather patterns can disrupt manufacturing sites and freight transportation systems. "
                "Companies are increasingly adopting carbon reduction initiatives and switching to renewable energy sources. "
                "Sustainability reporting has become a standard practice for Fortune 500 enterprises. "
                "Greenhouse gas emissions must be curbed to achieve carbon neutrality goals."
            )
        }
    ]
    
    print("\n--- Test Semantic Chunking ---")
    chunks = semantic_chunk_text(pages_data)
    
    for idx, chunk in enumerate(chunks):
        print(f"\nChunk {idx + 1} (Page {chunk['page']}):")
        print(chunk["content"])
        
    assert len(chunks) > 0, "Should have created chunks"
    
    # We expect separate chunks because page 1 is corporate info, page 2 is climate change
    print("✓ Semantic chunking tests passed successfully!")

if __name__ == "__main__":
    try:
        test_sentence_splitting()
        test_semantic_chunker()
        print("\nAll Phase 1 tests passed successfully!")
    except Exception as e:
        print(f"\nAssertion failed: {e}")
        sys.exit(1)
