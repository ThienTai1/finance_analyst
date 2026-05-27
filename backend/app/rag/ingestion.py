import os
import uuid
import logging
from pathlib import Path
from pypdf import PdfReader
from app.rag.database import get_qdrant_client, COLLECTION_NAME

logger = logging.getLogger(__name__)

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

def ingest_pdf(pdf_path: str, filename: str) -> dict:
    """
    Full ingestion pipeline:
    1. Parse PDF
    2. Chunk pages
    3. Generate IDs and Metadata
    4. Save to local Qdrant Vector DB
    """
    logger.info(f"Starting ingestion for: {filename}")
    
    # 1. Parse
    pages_data = extract_text_from_pdf(pdf_path)
    if not pages_data:
        raise ValueError(f"No readable text found in PDF: {filename}")
        
    # 2. Chunk
    chunks = chunk_text(pages_data)
    logger.info(f"Split PDF into {len(chunks)} chunks.")
    
    # 3. Formulate inputs for Qdrant client
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
        
    # 4. Insert into Qdrant using local FastEmbed pipeline
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
