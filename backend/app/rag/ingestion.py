import os
import uuid
import logging
import re
import numpy as np
from pathlib import Path
from pypdf import PdfReader
from app.rag.database import get_qdrant_client, COLLECTION_NAME
from app.config import (
    CHUNKING_STRATEGY,
    SEMANTIC_SPLIT_THRESHOLD_PERCENTILE,
    CHUNK_MIN_SIZE,
    CHUNK_MAX_SIZE
)

logger = logging.getLogger(__name__)

_embedding_model = None

def get_embedding_model():
    """
    Lazy-loads local FastEmbed TextEmbedding model (BAAI/bge-small-en-v1.5).
    """
    global _embedding_model
    if _embedding_model is None:
        from fastembed import TextEmbedding
        logger.info("Initializing local FastEmbed embedding model (BAAI/bge-small-en-v1.5) for semantic chunking...")
        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _embedding_model

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Computes cosine similarity between two vectors.
    """
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return float(dot_product / (norm_v1 * norm_v2))

def split_into_sentences(text: str) -> list[str]:
    """
    Splits text into individual sentences using an abbreviation-aware regex heuristic.
    """
    # Clean up whitespace but preserve basic punctuation splits
    cleaned_text = re.sub(r'\s+', ' ', text).strip()
    
    abbreviations = [
        "e.g.", "i.e.", "u.s.", "u.k.", "dr.", "mr.", "mrs.", "ms.", "inc.", "corp.", "co.", "ltd.", "approx.", "vs.",
        "jan.", "feb.", "mar.", "apr.", "jun.", "jul.", "aug.", "sep.", "oct.", "nov.", "dec.", "vol.", "ed.", "pp."
    ]
    
    # Split on period, exclamation, or question mark followed by whitespace and a capital letter/digit
    raw_splits = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', cleaned_text)
    
    sentences = []
    temp_sentence = ""
    for s in raw_splits:
        s = s.strip()
        if not s:
            continue
        if temp_sentence:
            temp_sentence += " " + s
        else:
            temp_sentence = s
            
        words = temp_sentence.split()
        if words:
            last_word = words[-1].lower().rstrip('.!?') + '.'
            # Check for known abbreviation or single-letter capital initial (e.g. A. Smith)
            if last_word in abbreviations or (len(words[-1]) <= 2 and words[-1].endswith('.') and words[-1][:-1].isalpha() and words[-1][:-1].isupper()):
                continue
        
        sentences.append(temp_sentence)
        temp_sentence = ""
        
    if temp_sentence:
        sentences.append(temp_sentence)
        
    return [s for s in sentences if s.strip()]

def semantic_chunk_text(pages_data: list[dict]) -> list[dict]:
    """
    Segments PDF text page-by-page into semantically cohesive chunks.
    Uses sentence embeddings and cosine similarity drop analysis.
    """
    logger.info("Executing Semantic Chunking algorithm...")
    
    # 1. Flatten all text into sentences and track page origins
    all_sentences = []
    for page_info in pages_data:
        page_num = page_info["page"]
        text = page_info["text"]
        sentences = split_into_sentences(text)
        for s in sentences:
            all_sentences.append({
                "text": s,
                "page": page_num
            })
            
    if not all_sentences:
        return []
        
    # If we have only 1 or 2 sentences, return them as a single chunk
    if len(all_sentences) <= 2:
        combined_text = " ".join([s["text"] for s in all_sentences])
        return [{
            "content": combined_text,
            "page": all_sentences[0]["page"]
        }]
        
    # 2. Embed sentences
    texts = [s["text"] for s in all_sentences]
    model = get_embedding_model()
    embeddings = list(model.embed(texts))
    
    # 3. Calculate cosine similarities between consecutive sentences
    similarities = []
    for i in range(len(embeddings) - 1):
        sim = cosine_similarity(embeddings[i], embeddings[i+1])
        similarities.append(sim)
        
    # 4. Calculate splitting threshold based on distance percentiles
    distances = [1.0 - sim for sim in similarities]
    threshold = float(np.percentile(distances, SEMANTIC_SPLIT_THRESHOLD_PERCENTILE))
    logger.info(f"Calculated semantic similarity distance threshold: {threshold:.4f} "
                f"({SEMANTIC_SPLIT_THRESHOLD_PERCENTILE}th percentile of distance drops)")
    
    # 5. Assemble chunks respecting min/max bounds and semantic valleys
    chunks = []
    current_chunk_text = ""
    current_chunk_pages = []
    
    for i, sent_info in enumerate(all_sentences):
        text = sent_info["text"]
        page = sent_info["page"]
        
        if current_chunk_text:
            current_chunk_text += " " + text
        else:
            current_chunk_text = text
            
        if page not in current_chunk_pages:
            current_chunk_pages.append(page)
            
        # Decide whether to split after this sentence
        should_split = False
        
        if i < len(all_sentences) - 1:
            distance = 1.0 - similarities[i]
            # Split if similarity drop exceeds threshold
            if distance >= threshold:
                should_split = True
                
            # Or split if adding the next sentence exceeds maximum allowed chunk size
            next_len = len(all_sentences[i+1]["text"])
            if len(current_chunk_text) + 1 + next_len > CHUNK_MAX_SIZE:
                should_split = True
                
            # Do NOT split if current chunk size is below minimum allowed chunk size
            if should_split and len(current_chunk_text) < CHUNK_MIN_SIZE:
                should_split = False
                
        # Split on boundary, or at the end of the document
        if should_split or i == len(all_sentences) - 1:
            chunks.append({
                "content": current_chunk_text.strip(),
                "page": current_chunk_pages[0] if current_chunk_pages else page
            })
            current_chunk_text = ""
            current_chunk_pages = []
            
    logger.info(f"Semantic Chunking complete. Created {len(chunks)} chunks.")
    return chunks

def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extracts text page-by-page from a PDF file.
    Returns a list of dicts: [{"page": 1, "text": "..."}]
    """
    pages_data = []
    try:
        reader = PdfReader(pdf_path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages_data.append({
                    "page": i + 1,
                    "text": text.strip()
                })
    except Exception as e:
        logger.error(f"Error reading PDF {pdf_path}: {e}")
        raise e
    return pages_data

def chunk_text(pages_data: list[dict], chunk_size: int = 1000, chunk_overlap: int = 200) -> list[dict]:
    """
    Splits text into chunks with overlap, tracking page numbers.
    """
    chunks = []
    
    for page_info in pages_data:
        text = page_info["text"]
        page_num = page_info["page"]
        
        # Simple character-based chunking with overlap
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_content = text[start:end]
            
            chunks.append({
                "content": chunk_content,
                "page": page_num
            })
            
            start += chunk_size - chunk_overlap
            
    return chunks

def call_ollama_ingest_sync(prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
    """
    Submits prompt to local Ollama synchronously.
    """
    import httpx
    from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
    
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
        }
    }
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()["response"].strip()
    except Exception as e:
        logger.error(f"Ollama call failed during ingestion: {e}")
        return ""

def generate_document_summary(pages_data: list[dict], filename: str) -> str:
    """
    Generates a concise 2-sentence summary/outline of the PDF document.
    """
    if not pages_data:
        return f"This document is named {filename}."
        
    # Combine text from the first 2 pages (or 1 page if only 1 exists)
    sample_text = ""
    for page in pages_data[:2]:
        sample_text += page["text"] + "\n"
        
    # Limit sample text length to keep prompt size small (approx 3000 chars)
    sample_text = sample_text[:3000]
    
    prompt = (
        f"Analyze the following excerpt from the beginning of a document named '{filename}':\n\n"
        f"--- Excerpt ---\n{sample_text}\n---------------\n\n"
        "Provide a concise, 1-2 sentence description explaining what this document is (e.g., company, year, report type, main topics).\n"
        "Output ONLY the description. Do not add introductory words or explanations."
    )
    
    logger.info(f"Generating document summary outline for: {filename}...")
    summary = call_ollama_ingest_sync(prompt, "You are a professional document classifier.")
    if not summary:
        summary = f"This document is named {filename} containing financial data."
    logger.info(f"Document Summary Generated: {summary}")
    return summary

def generate_chunk_preamble(doc_summary: str, chunk_text: str) -> str:
    """
    Generates a 1-sentence contextual description of a specific chunk relative to the document summary.
    """
    prompt = (
        f"Document Context Summary: {doc_summary}\n\n"
        f"Chunk Content to place in context:\n{chunk_text}\n\n"
        "Please write a short, 1-sentence preamble that explains the context of this chunk relative to the document.\n"
        "Example output: 'This segment is from Apple's FY 2026 report, detailing Services revenue trends.'\n"
        "Output ONLY the 1-sentence preamble. Do not add introductory words or explain."
    )
    
    preamble = call_ollama_ingest_sync(prompt, "You are a technical context-aware RAG assistant.")
    return preamble.strip()

def ingest_pdf(pdf_path: str, filename: str) -> dict:
    """
    Full ingestion pipeline:
    1. Parse PDF
    2. Chunk pages (semantic or character-based)
    3. Contextual Retrieval preamble generation (if enabled)
    4. Generate IDs and Metadata
    5. Save to local Qdrant Vector DB
    """
    logger.info(f"Starting ingestion for: {filename}")
    
    # 1. Parse
    pages_data = extract_text_from_pdf(pdf_path)
    if not pages_data:
        raise ValueError(f"No readable text found in PDF: {filename}")
        
    # 2. Chunk
    if CHUNKING_STRATEGY == "semantic":
        chunks = semantic_chunk_text(pages_data)
    else:
        chunks = chunk_text(pages_data)
        
    logger.info(f"Split PDF into {len(chunks)} chunks using strategy '{CHUNKING_STRATEGY}'.")
    
    # 3. Contextual Retrieval Preprocessing
    from app.config import CONTEXTUAL_RETRIEVAL_ENABLED
    if CONTEXTUAL_RETRIEVAL_ENABLED:
        try:
            doc_summary = generate_document_summary(pages_data, filename)
            logger.info("Compiling contextual preambles for each chunk...")
            for idx, chunk in enumerate(chunks):
                preamble = generate_chunk_preamble(doc_summary, chunk["content"])
                if preamble:
                    # Prepend preamble to chunk content
                    chunk["content"] = f"[{preamble}]\n{chunk['content']}"
                if (idx + 1) % 5 == 0:
                    logger.info(f"  Processed {idx + 1}/{len(chunks)} preambles...")
            logger.info("Compiled all contextual preambles successfully!")
        except Exception as e:
            logger.error(f"Contextual Retrieval generation failed, falling back to standard text: {e}")
            
    # 4. Formulate inputs for Qdrant client
    documents = []
    metadata = []
    ids = []
    
    for idx, chunk in enumerate(chunks):
        documents.append(chunk["content"])
        metadata.append({
            "source": filename,
            "page": chunk["page"],
            "chunk_idx": idx
        })
        # Generate stable UUID for chunks based on filename and index
        # This prevents duplicate inserts if the same file is uploaded twice
        chunk_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{filename}_chunk_{idx}"))
        ids.append(chunk_uuid)
        
        # Extract and index entity relationships for GraphRAG
        try:
            from app.rag.graph import extract_entities_and_relations_sync, index_graph_relations
            relations = extract_entities_and_relations_sync(chunk["content"])
            index_graph_relations(chunk_uuid, relations)
        except Exception as graph_err:
            logger.error(f"Failed to extract relationships for chunk {idx} inside GraphRAG: {graph_err}")
        
    # 5. Insert into Qdrant using local FastEmbed pipeline
    client = get_qdrant_client()
    client.add(
        collection_name=COLLECTION_NAME,
        documents=documents,
        metadata=metadata,
        ids=ids
    )
    
    logger.info(f"Ingested {len(documents)} chunks for '{filename}' into Qdrant successfully.")
    return {
        "filename": filename,
        "chunks_count": len(documents),
        "status": "success"
    }

def delete_pdf_from_store(filename: str):
    """
    Removes all chunks associated with a specific filename from Qdrant.
    """
    from qdrant_client.http import models
    client = get_qdrant_client()
    
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.Filter(
            must=[
                models.FieldCondition(
                    key="source",
                    match=models.MatchValue(value=filename)
                )
            ]
        )
    )
    logger.info(f"Deleted all vectors for source: {filename} from Qdrant.")
