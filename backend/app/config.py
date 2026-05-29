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

