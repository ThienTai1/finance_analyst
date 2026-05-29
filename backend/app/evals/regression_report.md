# RAG Regression Evaluation Report

**Date**: 41.150997 (Execution Time Reference)
**Total Benchmarks**: 3
**Success Rate**: 2 / 3

## Overall Metrics Summary
| Metric | Target | Score | Pass Status |
| :--- | :--- | :--- | :--- |
| **Claims Correctness** | >=0.65 | **1.0000** | ✅ PASS |
| **Query Relevance** | >=0.65 | **0.9051** | ✅ PASS |
| **Keyword Recall** | >=0.65 | **0.8750** | ✅ PASS |

## Detailed Benchmarking Cases

### Case 1: According to the uploaded documents, what is Goldman Sachs' net revenue for Q2 2026?
*   **Correctness Score**: 1.0000
*   **Relevance Score**: 0.9475
*   **Keyword Recall**: 1.0000 (Hits: Goldman Sachs, revenue, 12.5 billion, second quarter)
*   **Guessed Question**: *"What was Goldman Sachs' net revenue for the second quarter of fiscal year 2026 according to the uploaded financial report?"*

#### Claims Fact-Check Detail:
*   [✅ Supported] Goldman Sachs reported a record-breaking net revenue of $12.5 billion for the second quarter of fiscal year 2026.
*   [✅ Supported] The figure indicates strong performance and growth within the company during that period.

---

### Case 2: Based on the indexed reports, how much did renewable energy investments increase this fiscal year?
*   **Correctness Score**: 1.0000
*   **Relevance Score**: 0.8626
*   **Keyword Recall**: 0.7500 (Hits: renewable energy, investments, 45%)
*   **Guessed Question**: *"What was the percentage increase in renewable energy investments this fiscal year, and what does it indicate about the sector?"*

#### Claims Fact-Check Detail:
*   [✅ Supported] Renewable energy investments saw a significant increase of 45% this fiscal year
*   [✅ Supported] This growth highlights the strong momentum and investment trends in the renewable energy sector during the current financial period

---

### Case 3: According to the database, who is the CEO driving zero-emission logistics, and what is their strategy?
❌ **Execution Failed**: Agent failed to output a final answer.

