import os
import shutil
import logging
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict

from app.config import UPLOAD_DIR, PORT, HOST, OLLAMA_BASE_URL, OLLAMA_MODEL
from app.rag.ingestion import ingest_pdf, delete_pdf_from_store
from app.agent.tools import stock_data
from app.agent.engine import run_agent_workflow

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Financial Analyst Agentic RAG API",
    description="Backend API for local document ingestion and custom ReAct Agent research.",
    version="1.0.0"
)

# CORS Setup for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local convenience, can restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic schemas
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    query: str
    history: Optional[List[ChatMessage]] = []

@app.get("/api/health")
async def health_check():
    """
    Check backend state and verify if local dependencies (Ollama) are accessible.
    """
    import httpx
    ollama_ok = False
    model_ok = False
    
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                ollama_ok = True
                models = [m["name"] for m in resp.json().get("models", [])]
                # Check if configured model is pulled (matches name or name:latest)
                model_ok = any(OLLAMA_MODEL in m for m in models)
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        
    return {
        "status": "healthy" if ollama_ok else "degraded",
        "ollama_connected": ollama_ok,
        "ollama_model": OLLAMA_MODEL,
        "model_pulled": model_ok,
        "upload_directory": UPLOAD_DIR
    }

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a financial PDF and ingest it into the local Qdrant Vector database.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents are supported.")
        
    safe_filename = Path(file.filename).name
    save_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    try:
        logger.info(f"Saving uploaded file to {save_path}")
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Run synchronous ingestion (small files)
        result = ingest_pdf(save_path, safe_filename)
        return result
    except Exception as e:
        logger.error(f"Failed to ingest PDF {safe_filename}: {e}")
        # Clean up file on failure
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.get("/api/documents")
async def list_documents():
    """
    List all uploaded and indexed PDF reports.
    """
    docs = []
    if os.path.exists(UPLOAD_DIR):
        for name in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, name)
            if os.path.isfile(file_path) and name.endswith(".pdf"):
                stat = os.stat(file_path)
                docs.append({
                    "filename": name,
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "path": file_path
                })
    return docs

@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    """
    Remove an uploaded file from disk and delete its vectors from the Qdrant DB.
    """
    safe_filename = Path(filename).name
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found on disk.")
        
    try:
        # Delete from Qdrant vectors
        delete_pdf_from_store(safe_filename)
        
        # Delete from local filesystem
        os.remove(file_path)
        return {"status": "success", "message": f"Successfully deleted '{safe_filename}'."}
    except Exception as e:
        logger.error(f"Error deleting file {safe_filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@app.post("/api/chat")
async def chat_agent(request: ChatRequest):
    """
    Core AI Chat endpoint streaming the Custom Agent Loop's ReAct steps
    and observations in real time using Server-Sent Events (SSE).
    """
    try:
        history_list = [{"role": msg.role, "content": msg.content} for msg in request.history]
        
        # We return a StreamingResponse that yields JSON lines
        async def event_generator():
            async for event in run_agent_workflow(request.query, history_list):
                yield event
                
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"API Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock/{ticker}")
async def get_ticker_data(ticker: str, period: Optional[str] = "3mo"):
    """
    Fetch market pricing and valuation details for charting.
    """
    res = stock_data(ticker, period)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return res

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting FastAPI backend server on {HOST}:{PORT}")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
