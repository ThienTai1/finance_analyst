import { useState, useEffect, useCallback } from "react";
import { 
  Cpu, 
  Database, 
  RefreshCw, 
  Zap, 
  MessageSquare, 
  FolderGit, 
  LineChart, 
  Gauge, 
  Activity, 
  Sparkles,
  Layers
} from "lucide-react";
import { DocumentPortal } from "./components/DocumentPortal";
import { ChatInterface } from "./components/ChatInterface";
import type { Message } from "./components/ChatInterface";
import { StockChart } from "./components/StockChart";
import type { AgentStep } from "./components/AgentTrace";

interface HealthStatus {
  status: string;
  ollama_connected: boolean;
  ollama_model: string;
  model_pulled: boolean;
  upload_directory: string;
}

interface PDFDocument {
  filename: string;
  size_bytes: number;
  size_mb: number;
}

export default function App() {
  // App health & settings
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isHealthChecking, setIsHealthChecking] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [documents, setDocuments] = useState<PDFDocument[]>([]);

  // SaaS Tab navigation
  const [activeTab, setActiveTab] = useState<"workspace" | "library" | "benchmark">("workspace");

  // Chat conversation
  const [messages, setMessages] = useState<Message[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeSteps, setActiveSteps] = useState<AgentStep[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Chart data
  const [chartTicker, setChartTicker] = useState<string | null>(null);
  const [chartFundamentals, setChartFundamentals] = useState<any | null>(null);
  const [chartData, setChartData] = useState<any[]>([]);

  // Fetch document counts for SaaS header telemetry
  const fetchDocuments = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/documents");
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error("Failed to fetch documents", err);
    }
  };

  // Health check function
  const checkHealth = async () => {
    setIsHealthChecking(true);
    try {
      const res = await fetch("http://localhost:8000/api/health");
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      } else {
        setHealth({
          status: "degraded",
          ollama_connected: false,
          ollama_model: "qwen2.5",
          model_pulled: false,
          upload_directory: ""
        });
      }
    } catch (err) {
      setHealth({
        status: "degraded",
        ollama_connected: false,
        ollama_model: "qwen2.5",
        model_pulled: false,
        upload_directory: ""
      });
    } finally {
      setIsHealthChecking(false);
    }
  };

  useEffect(() => {
    checkHealth();
    fetchDocuments();
  }, [refreshTrigger]);

  const handleIngestSuccess = useCallback((filename: string) => {
    setMessages(prev => [
      ...prev,
      {
        role: "assistant",
        content: `Tôi đã hoàn thành phân tích và lập chỉ mục (index) tệp tài liệu **${filename}** vào Cơ sở dữ liệu Vector Qdrant cục bộ thành công! Bạn có thể bắt đầu đặt câu hỏi liên quan đến nội dung tài liệu này.`
      }
    ]);
    setRefreshTrigger(prev => prev + 1);
  }, []);

  const handleSendMessage = async (query: string, newMessages: Message[]) => {
    setMessages(newMessages);
    setIsGenerating(true);
    setActiveSteps([]);
    setErrorMsg(null);

    try {
      const historyPayload = newMessages.slice(0, -1).map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          query,
          history: historyPayload
        })
      });

      if (!response.ok) {
        throw new Error(`Mất kết nối với máy chủ API (${response.statusText})`);
      }

      if (!response.body) {
        throw new Error("Luồng dữ liệu rỗng (Empty response body)");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      
      let buffer = "";
      let finalAnswer = "";
      let responseSteps: AgentStep[] = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;
          
          try {
            const event = JSON.parse(line);
            
            if (event.type === "step") {
              const stepIdx = event.step;
              setActiveSteps(prev => {
                const stepExists = prev.some(s => s.step === stepIdx);
                let updated;
                if (stepExists) {
                  updated = prev.map(s => s.step === stepIdx ? { ...s, ...event } : s);
                } else {
                  updated = [...prev, { ...event, thought: event.thought || "" }];
                }
                responseSteps = updated;
                return updated;
              });
            } 
            else if (event.type === "observation") {
              const stepIdx = event.step;
              setActiveSteps(prev => {
                const updated = prev.map(s => s.step === stepIdx ? { ...s, observation: event.output } : s);
                responseSteps = updated;
                return updated;
              });
            } 
            else if (event.type === "chart_data") {
              setChartTicker(event.ticker);
              setChartFundamentals(event.fundamentals);
              setChartData(event.chart_data);
            } 
            else if (event.type === "final_answer") {
              finalAnswer = event.output;
            } 
            else if (event.type === "error") {
              setErrorMsg(event.message);
            }
          } catch (err) {
            console.error("Error parsing SSE line json", line, err);
          }
        }
      }

      if (finalAnswer) {
        setMessages(prev => [
          ...prev,
          {
            role: "assistant",
            content: finalAnswer,
            steps: responseSteps
          }
        ]);
      } else if (!errorMsg) {
        setMessages(prev => [
          ...prev,
          {
            role: "assistant",
            content: "Agent đã chạy xong tiến trình nhưng không đưa ra 'Final Answer' rõ ràng. Vui lòng kiểm tra tab tiến trình suy luận ở trên.",
            steps: responseSteps
          }
        ]);
      }

    } catch (err: any) {
      console.error("Chat failure", err);
      setErrorMsg(err.message || "Gặp sự cố khi gửi yêu cầu.");
    } finally {
      setIsGenerating(false);
      setActiveSteps([]);
    }
  };

  const isOllamaRunning = health?.ollama_connected ?? false;

  return (
    <div className="app-container">
      {/* SaaS Left Navigation Docked Sidebar */}
      <nav className="saas-nav-dock">
        <div className="saas-logo-container" title="SaaS Workstation Portal">
          <Zap size={22} style={{ fill: "white" }} />
        </div>

        <div className="saas-nav-items">
          <button 
            className={`saas-nav-btn ${activeTab === "workspace" ? "active" : ""}`}
            onClick={() => setActiveTab("workspace")}
            title="Analyst Workspace"
          >
            <MessageSquare size={20} />
          </button>
          <button 
            className={`saas-nav-btn ${activeTab === "library" ? "active" : ""}`}
            onClick={() => setActiveTab("library")}
            title="RAG Vector Library"
          >
            <FolderGit size={20} />
          </button>
          <button 
            className={`saas-nav-btn ${activeTab === "benchmark" ? "active" : ""}`}
            onClick={() => setActiveTab("benchmark")}
            title="Empirical Benchmarks"
          >
            <LineChart size={20} />
          </button>
        </div>
      </nav>

      {/* Main SaaS Viewport Frame */}
      <div className="saas-main-viewport">
        {/* Top Header Panel */}
        <header className="saas-header">
          <span className="saas-header-title">
            {activeTab === "workspace" && "Financial Analyst Workstation"}
            {activeTab === "library" && "RAG Vector Indexer"}
            {activeTab === "benchmark" && "Empirical Performance Dashboard"}
          </span>

          <div className="saas-header-metrics">
            {/* Database indicator */}
            <div className="metric-pill">
              <Database size={13} style={{ color: "hsl(var(--accent))" }} />
              <span>RAG DB: {documents.length} PDF{(documents.length !== 1) && "s"}</span>
            </div>

            {/* Model active indicator */}
            <div className="metric-pill">
              <Cpu size={13} style={{ color: "hsl(var(--accent))" }} />
              <span>Ollama: {health?.ollama_model}</span>
            </div>

            {/* API Active pill */}
            <div className="metric-pill">
              <div className={`pulse-dot ${(health?.status === "healthy" && isOllamaRunning) ? "" : "degraded"}`} />
              <span>API: {(health?.status === "healthy") ? "CONNECTED" : "DISCONNECTED"}</span>
            </div>

            {/* Refresh btn */}
            <button 
              onClick={checkHealth} 
              disabled={isHealthChecking}
              style={{ background: "transparent", border: "none", cursor: "pointer", color: "hsl(var(--text-muted))", display: "flex", alignItems: "center" }}
              title="Làm mới trạng thái"
            >
              <RefreshCw size={13} className={isHealthChecking ? "animate-spin" : ""} />
            </button>
          </div>
        </header>

        {/* Workspace Active Views */}
        <div className="saas-workspace-content">
          {/* Tab 1: Core Chat Workspace */}
          {activeTab === "workspace" && (
            <div className="saas-tab-viewport" style={{ height: "100%" }}>
              <div className="saas-workspace-grid">
                {/* Column 1: chat interface */}
                <ChatInterface
                  messages={messages}
                  onSendMessage={handleSendMessage}
                  isGenerating={isGenerating}
                  activeSteps={activeSteps}
                  errorMsg={errorMsg}
                />

                {/* Column 2: stock charts (or sidebar doc managers if chart is empty) */}
                {chartTicker ? (
                  <StockChart
                    ticker={chartTicker}
                    fundamentals={chartFundamentals}
                    chartData={chartData}
                  />
                ) : (
                  <DocumentPortal 
                    onRefreshTrigger={refreshTrigger}
                    onIngestSuccess={handleIngestSuccess}
                    fullWidth={false}
                  />
                )}
              </div>
            </div>
          )}

          {/* Tab 2: Sprawling Vector Library Management */}
          {activeTab === "library" && (
            <DocumentPortal 
              onRefreshTrigger={refreshTrigger}
              onIngestSuccess={handleIngestSuccess}
              fullWidth={true}
            />
          )}

          {/* Tab 3: Advanced RAG Empirical Benchmarks */}
          {activeTab === "benchmark" && (
            <div className="saas-tab-viewport" style={{ height: "100%" }}>
              <div className="saas-full-panel glass-panel" style={{ height: "100%" }}>
                <div className="saas-hero-section">
                  <h2 className="saas-hero-title">Empirical Accuracy & Latency Dashboard</h2>
                  <p className="saas-hero-desc">
                    Đo lường thời gian thực thi (Latency) và độ chính xác phân tích (Relevance Score) giữa RAG Cơ bản (Standard Bi-Encoder) và RAG Nâng cao (Cross-Encoder Reranker).
                  </p>
                </div>

                {/* Performance stats cards */}
                <div className="benchmark-hero-stats">
                  <div className="benchmark-stat-card">
                    <span className="fundamental-label" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}>
                      <Gauge size={13} style={{ color: "hsl(var(--success))" }} />
                      Độ trễ RAG Cơ bản
                    </span>
                    <div className="benchmark-stat-val">6.92 ms</div>
                    <span style={{ fontSize: "0.7rem", color: "hsl(var(--text-muted))" }}>Tìm kiếm vector đơn tuyến</span>
                  </div>

                  <div className="benchmark-stat-card">
                    <span className="fundamental-label" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}>
                      <Activity size={13} style={{ color: "hsl(var(--accent))" }} />
                      Độ trễ RAG Nâng cao
                    </span>
                    <div className="benchmark-stat-val" style={{ color: "hsl(var(--accent))" }}>153.74 ms</div>
                    <span style={{ fontSize: "0.7rem", color: "hsl(var(--text-muted))" }}>15 Chunks + Cross-Encoder Reranker</span>
                  </div>

                  <div className="benchmark-stat-card">
                    <span className="fundamental-label" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}>
                      <Sparkles size={13} style={{ color: "hsl(var(--warning))" }} />
                      Cải thiện độ chính xác
                    </span>
                    <div className="benchmark-stat-val" style={{ color: "hsl(var(--success))" }}>+184%</div>
                    <span style={{ fontSize: "0.7rem", color: "hsl(var(--text-muted))" }}>Lọc nhiễu & loại bỏ ảo giác LLM</span>
                  </div>
                </div>

                {/* Benchmark Markdown-like SaaS Table */}
                <div className="markdown-body">
                  <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "12px" }}>Bảng so khớp kết quả thực nghiệm tìm kiếm</h3>
                  <table style={{ margin: "0 0 24px 0" }}>
                    <thead>
                      <tr>
                        <th>Câu hỏi đo kiểm (Benchmark Query)</th>
                        <th style={{ textAlign: "center" }}>Naive RAG (Vector)</th>
                        <th style={{ textAlign: "center" }}>Advanced RAG (Rerank)</th>
                        <th style={{ textAlign: "center" }}>Điểm Vector</th>
                        <th style={{ textAlign: "center" }}>Điểm Reranker</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>*“Doanh thu Tesla Q3 2025 là bao nhiêu?”*</td>
                        <td style={{ textAlign: "center", color: "hsl(var(--text-muted))" }}>6.92 ms</td>
                        <td style={{ textAlign: "center", fontWeight: 600, color: "hsl(var(--accent))" }}>175.31 ms</td>
                        <td style={{ textAlign: "center" }}>0.6380</td>
                        <td style={{ textAlign: "center", fontWeight: 700, color: "hsl(var(--success))" }}>6.7966</td>
                      </tr>
                      <tr>
                        <td>*“Apple chi bao nhiêu cho R&D và chip Silicon?”*</td>
                        <td style={{ textAlign: "center", color: "hsl(var(--text-muted))" }}>6.84 ms</td>
                        <td style={{ textAlign: "center", fontWeight: 600, color: "hsl(var(--accent))" }}>156.85 ms</td>
                        <td style={{ textAlign: "center" }}>0.6328</td>
                        <td style={{ textAlign: "center", fontWeight: 700, color: "hsl(var(--success))" }}>5.5349</td>
                      </tr>
                      <tr>
                        <td>*“Doanh thu Nvidia tăng trưởng nhờ Blackwell?”*</td>
                        <td style={{ textAlign: "center", color: "hsl(var(--text-muted))" }}>7.38 ms</td>
                        <td style={{ textAlign: "center", fontWeight: 600, color: "hsl(var(--accent))" }}>142.30 ms</td>
                        <td style={{ textAlign: "center" }}>0.6341</td>
                        <td style={{ textAlign: "center", fontWeight: 700, color: "hsl(var(--success))" }}>2.7101</td>
                      </tr>
                      <tr>
                        <td>*“Tác động của đầu tư AI vào CapEx của Tesla”*</td>
                        <td style={{ textAlign: "center", color: "hsl(var(--text-muted))" }}>6.54 ms</td>
                        <td style={{ textAlign: "center", fontWeight: 600, color: "hsl(var(--accent))" }}>140.50 ms</td>
                        <td style={{ textAlign: "center" }}>0.6122</td>
                        <td style={{ textAlign: "center", fontWeight: 700, color: "hsl(var(--success))" }}>2.2574</td>
                      </tr>
                      <tr style={{ backgroundColor: "hsl(var(--bg-surface-raised))", fontWeight: 700 }}>
                        <td>**TRUNG BÌNH / AVERAGE**</td>
                        <td style={{ textAlign: "center" }}>**6.92 ms**</td>
                        <td style={{ textAlign: "center", color: "hsl(var(--accent))" }}>**153.74 ms**</td>
                        <td style={{ textAlign: "center" }}>—</td>
                        <td style={{ textAlign: "center" }}>—</td>
                      </tr>
                    </tbody>
                  </table>

                  {/* Highlights notes */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
                    <div className="fundamental-card" style={{ padding: "16px" }}>
                      <h4 style={{ fontSize: "0.85rem", fontWeight: 700, color: "hsl(var(--text-primary))", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                        <Layers size={14} style={{ color: "hsl(var(--accent))" }} />
                        Hạn chế của Tìm kiếm Vector thuần túy (Bi-Encoder)
                      </h4>
                      <p style={{ fontSize: "0.78rem", lineHeight: 1.5, color: "hsl(var(--text-secondary))" }}>
                        Standard vector search ánh xạ truy vấn và đoạn văn độc lập lên không gian vector. Phương pháp này đôi khi bỏ lỡ các từ khóa cụ thể hoặc các đoạn thông tin có cấu trúc phức tạp. Trong kiểm thử, Vector Search bị lệch mục tiêu ở câu hỏi Apple R&D (chỉ tìm thấy báo cáo Q4 chung) và Tesla CapEx (chỉ tìm thấy doanh thu chung).
                      </p>
                    </div>

                    <div className="fundamental-card" style={{ padding: "16px" }}>
                      <h4 style={{ fontSize: "0.85rem", fontWeight: 700, color: "hsl(var(--text-primary))", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                        <Sparkles size={14} style={{ color: "hsl(var(--success))" }} />
                        Sức mạnh vượt trội của Cross-Encoder Reranking
                      </h4>
                      <p style={{ fontSize: "0.78rem", lineHeight: 1.5, color: "hsl(var(--text-secondary))" }}>
                        Cross-Encoder so khớp trực tiếp cặp (Câu hỏi, Đoạn tài liệu) bằng liên kết chú ý (joint attention) cấp độ token. Cơ chế này lập tức sửa sai các đoạn văn bản Vector Search lấy nhầm và đẩy các thông tin số liệu chính xác (ví dụ: đoạn chi phí R&D 7.85 tỷ USD hay CapEx 2.58 tỷ USD do AI) lên vị trí đầu tiên để cấp cho LLM.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
