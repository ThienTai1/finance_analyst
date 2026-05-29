import os
import sys
import json
import asyncio
import logging

# Ensure backend/ directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.agent.engine import run_agent_workflow
from app.evals.judge import extract_claims, evaluate_claim, generate_hypothesis_question, calculate_relevance_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("regression_runner")

GOLDEN_DATASET_PATH = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "regression_report.md")
MIN_ACCEPTABLE_SCORE = 0.65 # Safety threshold for production

async def run_benchmark_for_query(item: dict) -> dict:
    query = item["query"]
    ref_q = item["reference_question"]
    expected_keywords = item["expected_keywords"]
    
    print(f"\n[Benchmarking Query]: '{query}'")
    
    # 1. Execute agent ReAct workflow asynchronously
    final_answer = ""
    compiled_contexts = []
    
    try:
        async for event_str in run_agent_workflow(query):
            event = json.loads(event_str.strip())
            if event["type"] == "final_answer":
                final_answer = event["output"]
            elif event["type"] == "observation" and event["action"] in ["VectorSearch", "StockData", "WebSearch"]:
                compiled_contexts.append(f"[{event['action']} observation]:\n{event['output']}")
    except Exception as e:
        logger.error(f"Failed to execute agent workflow for query '{query}': {e}")
        return {
            "query": query,
            "success": False,
            "error": str(e)
        }
        
    context = "\n\n".join(compiled_contexts)
    if not final_answer:
        return {
            "query": query,
            "success": False,
            "error": "Agent failed to output a final answer."
        }
        
    # 2. Evaluate Correctness (claims validation against context)
    print("Extracting claims from agent's response...")
    claims = await extract_claims(final_answer)
    print(f"Extracted {len(claims)} factual claims.")
    
    correct_count = 0
    claim_details = []
    if claims:
        for idx, claim in enumerate(claims):
            is_correct = await evaluate_claim(claim, context)
            if is_correct:
                correct_count += 1
            claim_details.append({"claim": claim, "supported": is_correct})
            print(f"  Claim {idx+1}: [{'PASS' if is_correct else 'FAIL'}] - {claim[:70]}...")
        correctness_score = float(correct_count / len(claims))
    else:
        correctness_score = 1.0 # If no claims were extracted, default to 1.0
        
    # 3. Evaluate Relevance (hypothesis similarity check)
    print("Reconstructing user query from final answer...")
    guessed_q = await generate_hypothesis_question(final_answer)
    print(f"Guessed question: '{guessed_q}'")
    relevance_score = calculate_relevance_score(guessed_q, ref_q)
    print(f"Relevance Score (Cosine Similarity): {relevance_score:.4f}")
    
    # 4. Lexical keyword overlap check
    keyword_hits = [k for k in expected_keywords if k.lower() in final_answer.lower()]
    keyword_recall = float(len(keyword_hits) / len(expected_keywords))
    
    return {
        "query": query,
        "success": True,
        "final_answer": final_answer,
        "claims_count": len(claims),
        "correctness_score": correctness_score,
        "relevance_score": relevance_score,
        "keyword_recall": keyword_recall,
        "keyword_hits": keyword_hits,
        "guessed_q": guessed_q,
        "claim_details": claim_details
    }

async def main():
    print("====================================================")
    print("🚀 Running Golden Dataset RAG Regression Benchmark CLI")
    print("====================================================")
    
    if not os.path.exists(GOLDEN_DATASET_PATH):
        print(f"Error: Golden dataset not found at {GOLDEN_DATASET_PATH}")
        sys.exit(1)
        
    with open(GOLDEN_DATASET_PATH, "r") as f:
        dataset = json.load(f)
        
    print(f"Loaded {len(dataset)} benchmarking test cases.")
    
    results = []
    for item in dataset:
        res = await run_benchmark_for_query(item)
        results.append(res)
        
    # Compile metrics
    successful_runs = [r for r in results if r.get("success")]
    
    avg_correctness = 0.0
    avg_relevance = 0.0
    avg_keyword_recall = 0.0
    
    if successful_runs:
        avg_correctness = sum(r["correctness_score"] for r in successful_runs) / len(successful_runs)
        avg_relevance = sum(r["relevance_score"] for r in successful_runs) / len(successful_runs)
        avg_keyword_recall = sum(r["keyword_recall"] for r in successful_runs) / len(successful_runs)
        
    # Generate Markdown Report
    report_md = (
        "# RAG Regression Evaluation Report\n\n"
        f"**Date**: {asyncio.get_event_loop().time()} (Execution Time Reference)\n"
        f"**Total Benchmarks**: {len(dataset)}\n"
        f"**Success Rate**: {len(successful_runs)} / {len(dataset)}\n\n"
        "## Overall Metrics Summary\n"
        "| Metric | Target | Score | Pass Status |\n"
        "| :--- | :--- | :--- | :--- |\n"
        f"| **Claims Correctness** | >={MIN_ACCEPTABLE_SCORE:.2f} | **{avg_correctness:.4f}** | {'✅ PASS' if avg_correctness >= MIN_ACCEPTABLE_SCORE else '❌ FAIL'} |\n"
        f"| **Query Relevance** | >={MIN_ACCEPTABLE_SCORE:.2f} | **{avg_relevance:.4f}** | {'✅ PASS' if avg_relevance >= MIN_ACCEPTABLE_SCORE else '❌ FAIL'} |\n"
        f"| **Keyword Recall** | >={MIN_ACCEPTABLE_SCORE:.2f} | **{avg_keyword_recall:.4f}** | {'✅ PASS' if avg_keyword_recall >= MIN_ACCEPTABLE_SCORE else '❌ FAIL'} |\n\n"
        "## Detailed Benchmarking Cases\n\n"
    )
    
    for idx, r in enumerate(results):
        report_md += f"### Case {idx+1}: {r['query']}\n"
        if not r.get("success"):
            report_md += f"❌ **Execution Failed**: {r.get('error')}\n\n"
            continue
            
        report_md += (
            f"*   **Correctness Score**: {r['correctness_score']:.4f}\n"
            f"*   **Relevance Score**: {r['relevance_score']:.4f}\n"
            f"*   **Keyword Recall**: {r['keyword_recall']:.4f} (Hits: {', '.join(r['keyword_hits'])})\n"
            f"*   **Guessed Question**: *\"{r['guessed_q']}\"*\n\n"
            "#### Claims Fact-Check Detail:\n"
        )
        
        for claim in r["claim_details"]:
            status = "✅ Supported" if claim["supported"] else "❌ Hallucinated/Unsupported"
            report_md += f"*   [{status}] {claim['claim']}\n"
            
        report_md += "\n---\n\n"
        
    with open(REPORT_PATH, "w") as f:
        f.write(report_md)
        
    print("\n====================================================")
    print("📊 Regression Benchmark Results Summary")
    print("====================================================")
    print(f"Average Correctness: {avg_correctness:.4f} (Threshold: {MIN_ACCEPTABLE_SCORE})")
    print(f"Average Relevance  : {avg_relevance:.4f} (Threshold: {MIN_ACCEPTABLE_SCORE})")
    print(f"Average Key Recall : {avg_keyword_recall:.4f}")
    print(f"Report saved to: {REPORT_PATH}")
    print("====================================================")
    
    # Exits with 1 if quality boundaries are violated (breaks CI/CD)
    if avg_correctness < MIN_ACCEPTABLE_SCORE or avg_relevance < MIN_ACCEPTABLE_SCORE:
        print("❌ FAILED: RAG performance has regressed below threshold boundaries!")
        sys.exit(1)
    else:
        print("✅ PASSED: RAG performance matches overall quality guidelines!")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
