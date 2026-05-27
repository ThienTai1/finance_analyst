import logging
import yfinance as yf
from qdrant_client import QdrantClient
from qdrant_client.http import models
from duckduckgo_search import DDGS
from app.rag.database import get_qdrant_client, COLLECTION_NAME

logger = logging.getLogger(__name__)

_reranker = None

def get_reranker():
    """
    Lazy-loads local Cross-Encoder TextCrossEncoder (BAAI/bge-reranker-base).
    ONNX runtime runs this 100% locally on CPU.
    """
    global _reranker
    if _reranker is None:
        logger.info("Initializing local Cross-Encoder TextCrossEncoder (BAAI/bge-reranker-base)...")
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        _reranker = TextCrossEncoder(model_name="BAAI/bge-reranker-base")
    return _reranker

def vector_search(query: str, limit: int = 5) -> str:
    """
    Search the local Qdrant Vector DB for matching financial report segments.
    Applies Advanced RAG: Retrieves 15 candidates and reranks them locally using Cross-Encoder.
    """
    logger.info(f"Tool VectorSearch called with query: '{query}'")
    try:
        client = get_qdrant_client()
        
        # 1. Hybrid Candidate Retrieval: Get 15 chunks semantically
        candidates_limit = 15
        results = client.query(
            collection_name=COLLECTION_NAME,
            query_text=query,
            limit=candidates_limit
        )
        
        if not results:
            return "No matching financial records found in the database. Please upload a PDF report first."
            
        # 2. Local Cross-Encoder Reranking
        try:
            reranker = get_reranker()
            docs = [res.document for res in results]
            
            # Compute rerank scores
            rerank_results = list(reranker.rerank(query, docs))
            
            # Map original results and sort by new Cross-Encoder score descending
            scored_results = []
            for idx, score in enumerate(rerank_results):
                original_res = results[idx]
                scored_results.append({
                    "res": original_res,
                    "rerank_score": score
                })
                
            scored_results.sort(key=lambda x: x["rerank_score"], reverse=True)
            
            # Keep only the top 5 chunks
            final_results = scored_results[:limit]
            
            formatted_results = []
            for item in final_results:
                res = item["res"]
                score = item["rerank_score"]
                meta = res.metadata
                filename = meta.get("source", "Unknown PDF")
                page = meta.get("page", "?")
                formatted_results.append(
                    f"[Source: {filename}, Page: {page}] (Cross-Encoder Rerank Score: {score:.4f})\nContent: {res.document}"
                )
                
            logger.info("Successfully reranked candidate chunks using local Cross-Encoder.")
            return "\n\n---\n\n".join(formatted_results)
            
        except Exception as re_err:
            logger.warning(f"Reranking failed, falling back to standard vector similarity: {re_err}")
            # Fallback to top-5 standard semantic similarity
            formatted_results = []
            for res in results[:limit]:
                meta = res.metadata
                filename = meta.get("source", "Unknown PDF")
                page = meta.get("page", "?")
                formatted_results.append(
                    f"[Source: {filename}, Page: {page}] (Similarity Score: {res.score:.4f})\nContent: {res.document}"
                )
            return "\n\n---\n\n".join(formatted_results)
            
    except Exception as e:
        logger.error(f"Error in VectorSearch: {e}")
        return f"Error executing VectorSearch: {str(e)}"

def stock_data(ticker: str, period: str = "3mo") -> dict:
    """
    Fetch comprehensive market data, stock history, and financial metrics using yfinance.
    Returns a dictionary suitable for frontend charting and LLM digestion.
    """
    logger.info(f"Tool StockData called for: {ticker} (period: {period})")
    ticker = ticker.strip().upper()
    try:
        stock = yf.Ticker(ticker)
        
        # 1. Fetch historical prices (for frontend charts)
        hist = stock.history(period=period)
        chart_data = []
        if not hist.empty:
            for index, row in hist.iterrows():
                chart_data.append({
                    "date": index.strftime("%Y-%m-%d"),
                    "open": round(float(row["Open"]), 2) if "Open" in row else None,
                    "high": round(float(row["High"]), 2) if "High" in row else None,
                    "low": round(float(row["Low"]), 2) if "Low" in row else None,
                    "close": round(float(row["Close"]), 2) if "Close" in row else None,
                    "volume": int(row["Volume"]) if "Volume" in row else None
                })
        
        # 2. Fetch key fundamental indicators
        info = stock.info
        
        # Clean & extract metrics (handle keys that might be missing)
        fundamentals = {
            "name": info.get("longName", ticker),
            "ticker": ticker,
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "price": round(float(info.get("currentPrice", info.get("navPrice", 0.0))), 2),
            "currency": info.get("financialCurrency", "USD"),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pe_ratio_formatted": f"{info.get('trailingPE'):.2f}" if info.get('trailingPE') else "N/A",
            "dividend_yield": f"{info.get('dividendYield', 0) * 100:.2f}%" if info.get('dividendYield') else "N/A",
            "debt_to_equity": f"{info.get('debtToEquity'):.2f}" if info.get('debtToEquity') else "N/A",
            "profit_margin": f"{info.get('profitMargins', 0) * 100:.2f}%" if info.get('profitMargins') else "N/A",
            "revenue_growth": f"{info.get('revenueGrowth', 0) * 100:.2f}%" if info.get('revenueGrowth') else "N/A",
            "ebitda": info.get("ebitda", 0),
            "summary": info.get("longBusinessSummary", "")
        }
        
        # Compile response
        return {
            "status": "success",
            "fundamentals": fundamentals,
            "chart_data": chart_data,
            "llm_summary": (
                f"Company: {fundamentals['name']} ({ticker})\n"
                f"Sector: {fundamentals['sector']} | Industry: {fundamentals['industry']}\n"
                f"Current Price: {fundamentals['price']} {fundamentals['currency']}\n"
                f"Market Cap: {fundamentals['market_cap']:,} {fundamentals['currency']}\n"
                f"P/E Ratio: {fundamentals['pe_ratio_formatted']} | Forward P/E: {fundamentals['forward_pe']}\n"
                f"Profit Margin: {fundamentals['profit_margin']} | Revenue Growth (YoY): {fundamentals['revenue_growth']}\n"
                f"Debt/Equity: {fundamentals['debt_to_equity']}\n"
                f"Data covers historical prices for period: {period}."
            )
        }
    except Exception as e:
        logger.error(f"Error in StockData for {ticker}: {e}")
        return {
            "status": "error",
            "message": f"Error fetching stock data for {ticker}: {str(e)}",
            "llm_summary": f"Could not fetch stock data for {ticker}. Error: {str(e)}"
        }

def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for real-time market updates, financial news, or general questions.
    """
    logger.info(f"Tool WebSearch called with query: '{query}'")
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}"
                )
        
        if not results:
            return f"Web search returned no results for query: '{query}'"
            
        return "\n\n---\n\n".join(results)
    except Exception as e:
        logger.error(f"Error in WebSearch: {e}")
        # Graceful fallback: return a notice so the agent knows we couldn't fetch web data
        return f"Error executing WebSearch (DuckDuckGo rate limit or connectivity issue): {str(e)}"

# Register tools mapping for easy execution in agent loop
ALL_TOOLS = {
    "VectorSearch": vector_search,
    "StockData": stock_data,
    "WebSearch": web_search
}

TOOLS_METADATA = [
    {
        "name": "VectorSearch",
        "description": "Searches the uploaded PDF financial reports and returns relevant segments. Use this tool when you need to answer specific questions about company numbers, annual/quarterly performance, financial statements, or internal details from uploaded documents.",
        "parameters": {
            "query": "The search terms or question related to the uploaded document contents."
        }
    },
    {
        "name": "StockData",
        "description": "Fetches current stock price, essential financial ratios, margins, market capitalization, and historical stock chart numbers. Use this tool when the user asks about stock prices, valuations, margins, historical stock movements, or comparative stock analysis.",
        "parameters": {
            "ticker": "The stock ticker symbol (e.g. AAPL, NVDA, TSLA, MSFT).",
            "period": "Optional. The duration of history: '1mo', '3mo', '6mo', '1y' (default: '3mo')."
        }
    },
    {
        "name": "WebSearch",
        "description": "Searches the internet for real-time stock news, market sentiments, macroeconomics, or general online knowledge. Use this tool when the user asks about recent breaking news, industry trends, or events that happened after the date of the uploaded document.",
        "parameters": {
            "query": "The search query query to run."
        }
    }
]
