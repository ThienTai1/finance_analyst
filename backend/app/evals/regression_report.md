# RAG Regression Evaluation Report

**Date**: 38.057918875 (Execution Time Reference)
**Total Benchmarks**: 3
**Success Rate**: 3 / 3

## Overall Metrics Summary
| Metric | Target | Score | Pass Status |
| :--- | :--- | :--- | :--- |
| **Claims Correctness** | >=0.65 | **0.7500** | ✅ PASS |
| **Query Relevance** | >=0.65 | **0.8644** | ✅ PASS |
| **Keyword Recall** | >=0.65 | **1.0000** | ✅ PASS |

## Detailed Benchmarking Cases

### Case 1: According to the uploaded documents, what is Goldman Sachs' net revenue for Q2 2026?
*   **Correctness Score**: 0.5000
*   **Relevance Score**: 0.9460
*   **Keyword Recall**: 1.0000 (Hits: Goldman Sachs, revenue, 12.5 billion, second quarter)
*   **Guessed Question**: *"What was Goldman Sachs' net revenue for the second quarter of 2026 according to the uploaded financial report?"*

#### Claims Fact-Check Detail:
*   [✅ Supported] Goldman Sachs announced a record-breaking net revenue of $12.5 billion for the second quarter of 2026.
*   [❌ Hallucinated/Unsupported] This figure represents a significant achievement.

---

### Case 2: Based on the indexed reports, how much did renewable energy investments increase this fiscal year?
*   **Correctness Score**: 1.0000
*   **Relevance Score**: 0.8739
*   **Keyword Recall**: 1.0000 (Hits: renewable energy, investments, 45%, funding)
*   **Guessed Question**: *"What was the trend in renewable energy investments globally according to the recent indexed reports?"*

#### Claims Fact-Check Detail:
*   [✅ Supported] Renewable energy investments saw a significant increase of 45% in global market funding during this fiscal year
*   [✅ Supported] This growth highlights the rising interest and investment trends towards sustainable energy solutions

---

### Case 3: According to the database, who is the CEO driving zero-emission logistics, and what is their strategy?
*   **Correctness Score**: 0.7500
*   **Relevance Score**: 0.7732
*   **Keyword Recall**: 1.0000 (Hits: Jane Doe, CEO, zero-emission, logistics)
*   **Guessed Question**: *"What is Jane Doe's strategy for driving zero-emission logistics at her company?"*

#### Claims Fact-Check Detail:
*   [✅ Supported] Jane Doe is the CEO.
*   [✅ Supported] The company she leads focuses on zero-emission logistics.
*   [✅ Supported] No explicit strategy regarding zero-emission logistics has been mentioned in the available reports.
*   [❌ Hallucinated/Unsupported] Further research through recent news articles and press releases would provide more insights into her strategy.

---

