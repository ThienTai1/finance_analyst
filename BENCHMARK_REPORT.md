# 📊 Advanced RAG Benchmark Report

This document reports empirical performance and accuracy metrics comparing our **Baseline Naive RAG** (Standard bi-encoder similarity search) against our **Advanced RAG** system (Candidates Pooling + Cross-Encoder Reranking using `BAAI/bge-reranker-base`).

---

## 📈 Performance & Latency Comparison

The benchmarks were executed locally on standard CPU hardware with ONNX Runtime optimizations enabled:

| Query / Đề tài | Baseline Latency (Naive RAG) | Advanced Latency (Cross-Encoder) | Semantic Score (Naive) | Cross-Encoder Relevance (Reranked) |
| :--- | :---: | :---: | :---: | :---: |
| *"Doanh thu Tesla quý 3 2025 là bao nhiêu và tăng trưởng thế nào?"* | 6.92 ms | 175.31 ms | 0.6380 | 6.7966 |
| *"Apple chi bao nhiêu tiền cho nghiên cứu phát triển R&D và chip Silicon?"* | 6.84 ms | 156.85 ms | 0.6328 | 5.5349 |
| *"Doanh thu Nvidia quý 3 tăng trưởng bao nhiêu phần trăm nhờ chip Blackwell?"* | 7.38 ms | 142.30 ms | 0.6341 | 2.7101 |
| *"Tác động của đầu tư AI vào chi phí vốn CapEx của Tesla"* | 6.54 ms | 140.50 ms | 0.6122 | 2.2574 |
| **AVERAGE / TRUNG BÌNH** | **6.92 ms** | **153.74 ms** | — | — |

---

## 💡 Key Architectural Insights

1. **The Latency Trade-Off**:
   * **Naive RAG** takes only **~6.92 ms** because it queries a single dense vector projection from the database.
   * **Advanced RAG** takes **~153.74 ms** (an addition of ~146.82 ms). This is extremely fast for CPU execution and falls well within the standard product threshold of <200ms.
   
2. **Relevance Quality (Why it's worth it)**:
   * Standard semantic search uses a **Bi-Encoder** architecture which maps query and document separately to embeddings, sometimes missing exact figures, percentages, or complex phrasing matching.
   * Cross-Encoder Rerankers analyze the **joint attention** of the query and context document *together* at a token level. This filters out weak candidates and bubbles up the absolute most precise context to the LLM agent, reducing hallucinations and maximizing answering accuracy.
   
3. **Empirical Document Matching Examples**:

### Q1: "Doanh thu Tesla quý 3 2025 là bao nhiêu và tăng trưởng thế nào?"

*   **Standard Vector Top Match** (Score: `0.6380`):
    > "Tesla, Inc. (TSLA) reported total revenue of $25.17 billion in Q3 2025, representing an increase of 8% year-over-year. N..."

*   **Cross-Encoder Reranked Top Match** (Rerank Score: `6.7966`):
    > "Tesla, Inc. (TSLA) reported total revenue of $25.17 billion in Q3 2025, representing an increase of 8% year-over-year. N..."

---

### Q2: "Apple chi bao nhiêu tiền cho nghiên cứu phát triển R&D và chip Silicon?"

*   **Standard Vector Top Match** (Score: `0.6328`):
    > "Apple Inc. (AAPL) announced financial results for its fiscal 2025 fourth quarter ended September 28, 2025. The company p..."

*   **Cross-Encoder Reranked Top Match** (Rerank Score: `5.5349`):
    > "Apple's research and development (R&D) expenses reached a record $7.85 billion in Q4 2025, driven heavily by engineering..."

---

### Q3: "Doanh thu Nvidia quý 3 tăng trưởng bao nhiêu phần trăm nhờ chip Blackwell?"

*   **Standard Vector Top Match** (Score: `0.6341`):
    > "NVIDIA Corporation (NVDA) reported record-breaking quarterly revenue of $35.08 billion for its third quarter of fiscal 2..."

*   **Cross-Encoder Reranked Top Match** (Rerank Score: `2.7101`):
    > "NVIDIA's massive growth was primarily fueled by continuous scaling in Data Center infrastructure, where revenues reached..."

---

### Q4: "Tác động của đầu tư AI vào chi phí vốn CapEx của Tesla"

*   **Standard Vector Top Match** (Score: `0.6122`):
    > "Tesla, Inc. (TSLA) reported total revenue of $25.17 billion in Q3 2025, representing an increase of 8% year-over-year. N..."

*   **Cross-Encoder Reranked Top Match** (Rerank Score: `2.2574`):
    > "Tesla's capital expenditures (CapEx) rose significantly to $2.58 billion in Q3 2025 as the company aggressively expanded..."

---

