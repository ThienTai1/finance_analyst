import os
import re
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
GRAPH_PATH = str(BASE_DIR / "data" / "knowledge_graph.json")

# Ensure data directory exists
Path(GRAPH_PATH).parent.mkdir(parents=True, exist_ok=True)

def call_ollama_graph_sync(prompt: str, system_prompt: str) -> str:
    """
    Synchronous Ollama client wrapper using httpx.Client to perform extraction.
    """
    from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
    import httpx
    
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.0
        }
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            res_json = response.json()
            return res_json.get("response", "").strip()
    except Exception as e:
        logger.error(f"Error calling Ollama in call_ollama_graph_sync: {e}")
        return ""

def parse_json_safe(text: str) -> list:
    """
    Robustly parses JSON array lists from LLM outputs.
    """
    text = text.strip()
    # Remove markdown codeblock wrappers if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except Exception:
        try:
            # Fallback regex search for JSON array block
            match = re.search(r"(\[.*\])", text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []

def extract_entities_and_relations_sync(text: str) -> list:
    """
    Extracts key entity-relation triples from a financial text segment using Ollama.
    """
    logger.info("Extracting graph triples via Ollama...")
    system_prompt = (
        "You are an expert financial knowledge extraction system. "
        "Your task is to analyze the provided financial text segment and extract key corporate entities, "
        "financial items, metrics, and executives, alongside their explicit relationships. "
        "Return ONLY a clean JSON list of triples. Each triple must have keys: 'source', 'relation', and 'target'.\n\n"
        "Example Output format:\n"
        "[\n"
        "  {\"source\": \"Apple Inc.\", \"relation\": \"reported services revenue of\", \"target\": \"$95.5 billion\"},\n"
        "  {\"source\": \"Goldman Sachs\", \"relation\": \"achieved net revenue of\", \"target\": \"$12.5 billion\"}\n"
        "]\n"
        "Do not explain, do not add introductory text, return ONLY the raw JSON array."
    )
    prompt = (
        f"Analyze this financial text and extract key entity relations:\n\n"
        f"Text:\n{text}\n\n"
        f"JSON list:"
    )
    
    response = call_ollama_graph_sync(prompt, system_prompt)
    triples = parse_json_safe(response)
    logger.info(f"Successfully extracted {len(triples)} graph relations.")
    return triples

def index_graph_relations(chunk_id: str, relations: list):
    """
    Saves a set of relations under a unique chunk ID in local knowledge_graph.json database.
    """
    if not relations:
        return
        
    try:
        graph_data = {}
        if os.path.exists(GRAPH_PATH):
            try:
                with open(GRAPH_PATH, "r", encoding="utf-8") as f:
                    graph_data = json.load(f)
            except Exception:
                logger.warning("Could not read existing knowledge graph. Initializing clean file.")
                
        graph_data[chunk_id] = relations
        
        with open(GRAPH_PATH, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Indexed {len(relations)} relations for chunk {chunk_id} in knowledge graph.")
    except Exception as e:
        logger.error(f"Error indexing graph relations: {e}")

def extract_query_entities_sync(query: str) -> list[str]:
    """
    Extracts key entity keywords from query to look up in graph.
    """
    system_prompt = (
        "You are an expert entity extractor. Extract the 1 or 2 main corporate or financial entity names "
        "from the user search query as a clean, comma-separated list of keywords. Return ONLY the keywords.\n"
        "Example Query: 'What is Apple's revenue?' -> Apple\n"
        "Example Query: 'How much did Goldman Sachs make?' -> Goldman Sachs"
    )
    prompt = f"Query: '{query}'\nKeywords:"
    
    response = call_ollama_graph_sync(prompt, system_prompt)
    if response:
        keywords = [kw.strip().lower() for kw in response.split(",") if kw.strip()]
        return keywords
    return []

def graph_search(query: str) -> str:
    """
    Traverses on-disk Graph database using keywords extracted from the search query.
    Returns formatted relational facts suitable for appending to RAG prompt context.
    """
    logger.info(f"Graph Search called with query: '{query}'")
    if not os.path.exists(GRAPH_PATH):
        return ""
        
    try:
        with open(GRAPH_PATH, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading knowledge graph file: {e}")
        return ""
        
    # Extract search terms
    search_keywords = extract_query_entities_sync(query)
    
    # Fallback to simple split if LLM returned nothing or errored
    if not search_keywords:
        # Simple stopword filter fallback
        stopwords = {"what", "is", "for", "how", "much", "did", "the", "in", "a", "of", "and", "to", "who", "their", "strategy"}
        search_keywords = [word.strip(",.?!'\"").lower() for word in query.split() if word.lower() not in stopwords and len(word) > 2]
        
    logger.info(f"Using search keywords for GraphRAG matching: {search_keywords}")
    
    matched_triples = []
    seen = set() # Prevent duplicate triples
    
    for chunk_id, relations in graph_data.items():
        for r in relations:
            source = r.get("source", "")
            relation = r.get("relation", "")
            target = r.get("target", "")
            
            if not source or not target:
                continue
                
            # Match keywords in source, relation or target
            triple_str = f"{source} -> {relation} -> {target}"
            if triple_str in seen:
                continue
                
            for kw in search_keywords:
                if kw in source.lower() or kw in target.lower():
                    matched_triples.append(f"- {source} [{relation}] -> {target}")
                    seen.add(triple_str)
                    break
                    
    if not matched_triples:
        logger.info("GraphRAG search returned 0 relational facts.")
        return ""
        
    logger.info(f"GraphRAG search matched {len(matched_triples)} facts.")
    # Return formatted knowledge graph facts
    return "\n".join(matched_triples[:12]) # Cap at top 12 relational facts
