import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Ollama Settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5")

# Vector DB & Storage
QDRANT_PATH = os.getenv("QDRANT_PATH", str(BASE_DIR / "qdrant_db"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))

# Ensure directories exist
Path(QDRANT_PATH).mkdir(parents=True, exist_ok=True)
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

# App Settings
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

# Chunking configurations
CHUNKING_STRATEGY = os.getenv("CHUNKING_STRATEGY", "semantic").lower()
SEMANTIC_SPLIT_THRESHOLD_PERCENTILE = int(os.getenv("SEMANTIC_SPLIT_THRESHOLD_PERCENTILE", "85"))
CHUNK_MIN_SIZE = int(os.getenv("CHUNK_MIN_SIZE", "200"))
CHUNK_MAX_SIZE = int(os.getenv("CHUNK_MAX_SIZE", "1500"))

# Hybrid Search configurations
HYBRID_SEARCH_ENABLED = os.getenv("HYBRID_SEARCH_ENABLED", "true").lower() == "true"
SPARSE_EMBEDDING_MODEL = os.getenv("SPARSE_EMBEDDING_MODEL", "Qdrant/bm25")

# HNSW Vector Index configurations
QDRANT_HNSW_M = int(os.getenv("QDRANT_HNSW_M", "16"))
QDRANT_HNSW_EF_CONSTRUCT = int(os.getenv("QDRANT_HNSW_EF_CONSTRUCT", "100"))
QDRANT_SEARCH_EF = os.getenv("QDRANT_SEARCH_EF")
if QDRANT_SEARCH_EF is not None:
    QDRANT_SEARCH_EF = int(QDRANT_SEARCH_EF)

# Langfuse Observability configurations
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
LANGFUSE_ENABLED = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)

# Contextual Retrieval configurations
CONTEXTUAL_RETRIEVAL_ENABLED = os.getenv("CONTEXTUAL_RETRIEVAL_ENABLED", "true").lower() == "true"

# Agentic Query Rewrite configurations
AGENTIC_QUERY_REWRITE_ENABLED = os.getenv("AGENTIC_QUERY_REWRITE_ENABLED", "true").lower() == "true"
RERANK_MIN_PASSING_SCORE = float(os.getenv("RERANK_MIN_PASSING_SCORE", "0.0"))





