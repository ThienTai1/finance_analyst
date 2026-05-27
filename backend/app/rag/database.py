import logging
from qdrant_client import QdrantClient
from app.config import QDRANT_PATH

logger = logging.getLogger(__name__)

_client = None
COLLECTION_NAME = "financial_reports"

def get_qdrant_client() -> QdrantClient:
    """
    Returns a persistent local QdrantClient instance (disk-based, no Docker required!).
    Automatically initializes FastEmbed integration.
    """
    global _client
    if _client is None:
        logger.info(f"Initializing local Qdrant database at: {QDRANT_PATH}")
        _client = QdrantClient(path=QDRANT_PATH)
        
        # Set up default local embedding model (runs 100% locally using ONNX runtime)
        # BAAI/bge-small-en-v1.5 is fast, accurate, and lightweight
        _client.set_model("BAAI/bge-small-en-v1.5")
        
        # Ensure the collection exists
        try:
            if not _client.collection_exists(COLLECTION_NAME):
                logger.info(f"Creating vector collection: {COLLECTION_NAME}")
                # Creating collection using fastembed automatically configures vector size
                _client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=_client.get_fastembed_vector_params(),
                )
        except Exception as e:
            logger.error(f"Error checking/creating Qdrant collection: {e}")
            
    return _client
