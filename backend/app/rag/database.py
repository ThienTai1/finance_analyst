import logging
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.config import (
    QDRANT_PATH,
    HYBRID_SEARCH_ENABLED,
    SPARSE_EMBEDDING_MODEL,
    QDRANT_HNSW_M,
    QDRANT_HNSW_EF_CONSTRUCT
)

logger = logging.getLogger(__name__)

_client = None
COLLECTION_NAME = "financial_reports"

def get_qdrant_client() -> QdrantClient:
    """
    Returns a persistent local QdrantClient instance (disk-based, no Docker required!).
    Automatically initializes FastEmbed dense and sparse integrations.
    """
    global _client
    if _client is None:
        logger.info(f"Initializing local Qdrant database at: {QDRANT_PATH}")
        _client = QdrantClient(path=QDRANT_PATH)
        
        # Set up default local embedding model (runs 100% locally using ONNX runtime)
        # BAAI/bge-small-en-v1.5 is fast, accurate, and lightweight
        _client.set_model("BAAI/bge-small-en-v1.5")
        
        # Set up default local sparse embedding model for Hybrid Search if enabled
        if HYBRID_SEARCH_ENABLED:
            logger.info(f"Configuring local FastEmbed sparse embedding model: {SPARSE_EMBEDDING_MODEL} for Hybrid Search")
            _client.set_sparse_model(SPARSE_EMBEDDING_MODEL)
            
        # Ensure the collection exists and is configured correctly
        try:
            should_create = False
            
            if not _client.collection_exists(COLLECTION_NAME):
                logger.info(f"Collection {COLLECTION_NAME} does not exist. Will create it.")
                should_create = True
            else:
                # If collection exists, inspect it to see if it supports sparse vectors if hybrid is enabled
                coll_info = _client.get_collection(COLLECTION_NAME)
                has_sparse = coll_info.config.params.sparse_vectors is not None
                
                if HYBRID_SEARCH_ENABLED and not has_sparse:
                    logger.warning("Existing Qdrant collection does not have sparse vectors configured, but hybrid search is enabled. Recreating...")
                    _client.delete_collection(COLLECTION_NAME)
                    should_create = True
                elif not HYBRID_SEARCH_ENABLED and has_sparse:
                    logger.warning("Existing Qdrant collection has sparse vectors configured, but hybrid search is disabled. Recreating...")
                    _client.delete_collection(COLLECTION_NAME)
                    should_create = True
                    
            if should_create:
                logger.info(f"Creating vector collection: {COLLECTION_NAME} "
                            f"(Hybrid Search: {HYBRID_SEARCH_ENABLED}, HNSW M: {QDRANT_HNSW_M}, EF Construct: {QDRANT_HNSW_EF_CONSTRUCT})")
                
                # Setup custom HNSW parameters
                hnsw_diff = models.HnswConfigDiff(
                    m=QDRANT_HNSW_M,
                    ef_construct=QDRANT_HNSW_EF_CONSTRUCT
                )
                
                _client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=_client.get_fastembed_vector_params(),
                    sparse_vectors_config=_client.get_fastembed_sparse_vector_params() if HYBRID_SEARCH_ENABLED else None,
                    hnsw_config=hnsw_diff
                )
        except Exception as e:
            logger.error(f"Error checking/creating/recreating Qdrant collection: {e}")
            
    return _client
