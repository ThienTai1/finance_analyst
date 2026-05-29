import json
import re
import logging
import httpx
import numpy as np
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from app.rag.ingestion import get_embedding_model, cosine_similarity

logger = logging.getLogger(__name__)

async def call_judge_llm(prompt: str, system_prompt: str = "You are an objective, precise AI Judge.") -> str:
    """
    Submits evaluation prompts to local Ollama judge model.
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.0, # Zero temperature for objective metrics
        }
    }
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()["response"].strip()

async def extract_claims(answer: str) -> list[str]:
    """
    Extracts individual factual claims from final agent answer.
    """
    prompt = (
        "Analyze the following text and break it down into a list of independent, single-sentence factual claims.\n"
        "Output ONLY a valid JSON list of strings, for example: [\"Claim 1\", \"Claim 2\"].\n"
        "Do not write any introductory or explanatory text. Return ONLY the JSON codeblock.\n\n"
        f"Text to evaluate:\n{answer}"
    )
    
    try:
        response = await call_judge_llm(prompt)
        # Clean JSON markdown if wrapped
        clean_json = re.sub(r"^```json\s*", "", response)
        clean_json = re.sub(r"\s*```$", "", clean_json).strip()
        
        claims = json.loads(clean_json)
        if isinstance(claims, list):
            return [str(c).strip() for c in claims if str(c).strip()]
    except Exception as e:
        logger.warning(f"Could not parse LLM claims as JSON. Executing line-splitting fallback. Error: {e}")
        
    # Line-splitting fallback: match standard list item formats
    claims = []
    for line in response.split("\n"):
        line = re.sub(r"^(\d+\.|\-|\*)\s*", "", line).strip()
        line = line.strip("[]\",'")
        if line and len(line) > 10:
            claims.append(line)
            
    return claims

async def evaluate_claim(claim: str, context: str) -> bool:
    """
    Verifies if a specific claim is correct/supported based ONLY on retrieved context.
    """
    prompt = (
        f"Retrieved Context:\n{context}\n\n"
        f"Claim to verify:\n{claim}\n\n"
        "Is the claim fully supported and correct based ONLY on the retrieved context above?\n"
        "Respond with EXACTLY 'TRUE' or 'FALSE'. Do not explain or add comments."
    )
    
    try:
        response = await call_judge_llm(prompt)
        response_cleaned = response.upper().replace(".", "").strip()
        if "TRUE" in response_cleaned:
            return True
        return False
    except Exception as e:
        logger.error(f"Error evaluating claim '{claim}': {e}")
        return False

async def generate_hypothesis_question(answer: str) -> str:
    """
    Reconstructs user question based ONLY on the final agent response.
    """
    prompt = (
        "Read the following answer text carefully and reconstruct the original user question that led to this answer.\n"
        "Output ONLY the reconstructed question itself. Do not explain, do not add introductory words (like 'Question:'), just output the exact question string.\n\n"
        f"Answer text:\n{answer}"
    )
    
    try:
        guessed_q = await call_judge_llm(prompt)
        # Strip prefixes like "Question: " or "Guessed question: "
        guessed_q = re.sub(r"^(Question|Guessed question|User question):\s*", "", guessed_q, flags=re.IGNORECASE)
        return guessed_q.strip()
    except Exception as e:
        logger.error(f"Error generating hypothesis question: {e}")
        return ""

def calculate_relevance_score(guessed_q: str, original_q: str) -> float:
    """
    Measures cosine embedding similarity between the guessed question and original query.
    """
    if not guessed_q or not original_q:
        return 0.0
        
    try:
        model = get_embedding_model()
        embeddings = list(model.embed([guessed_q, original_q]))
        
        sim = cosine_similarity(embeddings[0], embeddings[1])
        return max(0.0, min(1.0, float(sim)))
    except Exception as e:
        logger.error(f"Error calculating relevance score: {e}")
        return 0.0
