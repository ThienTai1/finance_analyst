# 📊 Advanced RAG Benchmark Report

This document reports empirical performance and accuracy metrics comparing our **Baseline Naive RAG** (Standard bi-encoder similarity search) against our **Advanced RAG** system (Candidates Pooling + Cross-Encoder Reranking using `BAAI/bge-reranker-base`).

---

## 📈 Performance & Latency Comparison

The benchmarks were executed locally on standard CPU hardware with ONNX Runtime optimizations enabled:

| Query / Topic | Baseline Latency (Naive RAG) | Advanced Latency (Cross-Encoder) | Semantic Score (Naive) | Cross-Encoder Relevance (Reranked) |
| :--- | :---: | :---: | :---: | :---: |
| *"What is Tesla's Q3 2025 revenue and how much did it grow?"* | 29.90 ms | 164.50 ms | 0.8579 | 8.7142 |
| *"How much does Apple spend on R&D and custom Silicon chips?"* | 7.53 ms | 165.64 ms | 0.7712 | 4.9121 |
| *"What percentage of Nvidia's Q3 revenue growth was driven by Blackwell?"* | 8.03 ms | 154.39 ms | 0.7920 | 4.7130 |
| *"Impact of AI investments on Tesla's capital expenditures CapEx"* | 5.68 ms | 147.51 ms | 0.7815 | 4.6296 |
| **AVERAGE / MEAN** | **12.78 ms** | **158.01 ms** | — | — |

---

## 💡 Key Architectural Insights

1. **The Latency Trade-Off**:
   * **Naive RAG** takes only **~12.78 ms** because it queries a single dense vector projection from the database.
   * **Advanced RAG** takes **~158.01 ms** (an addition of ~145.23 ms). This is extremely fast for CPU execution and falls well within the standard product threshold of <200ms.
   
2. **Relevance Quality (Why it's worth it)**:
   * Standard semantic search uses a **Bi-Encoder** architecture which maps query and document separately to embeddings, sometimes missing exact figures, percentages, or complex phrasing matching.
   * Cross-Encoder Rerankers analyze the **joint attention** of the query and context document *together* at a token level. This filters out weak candidates and bubbles up the absolute most precise context to the LLM agent, reducing hallucinations and maximizing answering accuracy.
   
3. **Empirical Document Matching Examples**:

### Q1: "What is Tesla's Q3 2025 revenue and how much did it grow?"

*   **Standard Vector Top Match** (Score: `0.8579`):
    > "Tesla, Inc. (TSLA) reported total revenue of $25.17 billion in Q3 2025, representing an increase of 8% year-over-year. N..."

*   **Cross-Encoder Reranked Top Match** (Rerank Score: `8.7142`):
    > "Tesla, Inc. (TSLA) reported total revenue of $25.17 billion in Q3 2025, representing an increase of 8% year-over-year. N..."

---

### Q2: "How much does Apple spend on R&D and custom Silicon chips?"

*   **Standard Vector Top Match** (Score: `0.7712`):
    > "Apple's research and development (R&D) expenses reached a record $7.85 billion in Q4 2025, driven heavily by engineering..."

*   **Cross-Encoder Reranked Top Match** (Rerank Score: `4.9121`):
    > "Apple's research and development (R&D) expenses reached a record $7.85 billion in Q4 2025, driven heavily by engineering..."

---

### Q3: "What percentage of Nvidia's Q3 revenue growth was driven by Blackwell?"

*   **Standard Vector Top Match** (Score: `0.7920`):
    > "NVIDIA Corporation (NVDA) reported record-breaking quarterly revenue of $35.08 billion for its third quarter of fiscal 2..."

*   **Cross-Encoder Reranked Top Match** (Rerank Score: `4.7130`):
    > "NVIDIA's massive growth was primarily fueled by continuous scaling in Data Center infrastructure, where revenues reached..."

---

### Q4: "Impact of AI investments on Tesla's capital expenditures CapEx"

*   **Standard Vector Top Match** (Score: `0.7815`):
    > "Tesla's capital expenditures (CapEx) rose significantly to $2.58 billion in Q3 2025 as the company aggressively expanded..."

*   **Cross-Encoder Reranked Top Match** (Rerank Score: `4.6296`):
    > "Tesla's capital expenditures (CapEx) rose significantly to $2.58 billion in Q3 2025 as the company aggressively expanded..."

---

