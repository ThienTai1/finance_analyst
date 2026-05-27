import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2, Sparkles, Download, AlertCircle } from "lucide-react";
import { AgentTrace } from "./AgentTrace";
import type { AgentStep } from "./AgentTrace";

export interface Message {
  role: "user" | "assistant";
  content: string;
  steps?: AgentStep[];
}

interface ChatInterfaceProps {
  messages: Message[];
  onSendMessage: (query: string, newMessages: Message[]) => Promise<void>;
  isGenerating: boolean;
  activeSteps: AgentStep[];
  errorMsg: string | null;
}

// Custom Premium Markdown Formatter in React (Diaflow Clean Light-Theme Adapted)
export const MarkdownRenderer: React.FC<{ text: string }> = ({ text }) => {
  if (!text) return null;

  const lines = text.split("\n");
  let inTable = false;
  let tableHeaders: string[] = [];
  let tableRows: string[][] = [];
  const renderedElements: React.ReactNode[] = [];

  const parseInlineMarkdown = (content: string) => {
    // Bold parsing
    const boldRegex = /\*\*(.*?)\*\*/g;
    let match;
    
    // Simple inline parser for portfolios
    let formattedText: React.ReactNode[] = [];
    let currentIdx = 0;
    
    // Reset regex
    boldRegex.lastIndex = 0;
    
    while ((match = boldRegex.exec(content)) !== null) {
      const matchStart = match.index;
      const matchEnd = boldRegex.lastIndex;
      
      if (matchStart > currentIdx) {
        formattedText.push(content.substring(currentIdx, matchStart));
      }
      
      // Adapted to HSL text color for high contrast light mode!
      formattedText.push(<strong key={`b-${matchStart}`} style={{ color: "hsl(var(--text-primary))", fontWeight: 700 }}>{match[1]}</strong>);
      currentIdx = matchEnd;
    }
    
    if (currentIdx < content.length) {
      formattedText.push(content.substring(currentIdx));
    }
    
    if (formattedText.length === 0) return content;
    
    // Inline code parsing on the output
    return formattedText.map((item, i) => {
      if (typeof item === "string") {
        const codeRegex = /`(.*?)`/g;
        let cMatch;
        let cParts: React.ReactNode[] = [];
        let cIdx = 0;
        
        while ((cMatch = codeRegex.exec(item)) !== null) {
          if (cMatch.index > cIdx) {
            cParts.push(item.substring(cIdx, cMatch.index));
          }
          // Premium light-theme inline code style!
          cParts.push(
            <code key={`c-${cMatch.index}`} style={{ fontFamily: "var(--font-mono)", background: "hsl(var(--bg-base))", padding: "2px 6px", borderRadius: "4px", fontSize: "0.85em", color: "hsl(var(--accent))", border: "1px solid hsl(var(--border))" }}>
              {cMatch[1]}
            </code>
          );
          cIdx = codeRegex.lastIndex;
        }
        
        if (cIdx < item.length) {
          cParts.push(item.substring(cIdx));
        }
        return cParts.length > 0 ? <React.Fragment key={i}>{cParts}</React.Fragment> : item;
      }
      return item;
    });
  };

  const renderTable = (headers: string[], rows: string[][], key: number) => {
    return (
      <div key={`table-${key}`} style={{ overflowX: "auto", margin: "16px 0", width: "100%" }} className="markdown-body">
        <table>
          <thead>
            <tr>
              {headers.map((h, i) => <th key={i}>{h.trim()}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr key={ri}>
                {row.map((cell, ci) => <td key={ci}>{parseInlineMarkdown(cell.trim())}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    // Table boundary parsing
    if (trimmed.startsWith("|")) {
      const parts = trimmed.split("|").slice(1, -1);
      
      if (!inTable) {
        inTable = true;
        tableHeaders = parts;
        tableRows = [];
      } else {
        // Check if this is a separator line like |---|---|
        const isSeparator = parts.every(p => p.trim().startsWith("-"));
        if (!isSeparator) {
          tableRows.push(parts);
        }
      }
      return;
    } else {
      if (inTable) {
        renderedElements.push(renderTable(tableHeaders, tableRows, index));
        inTable = false;
        tableHeaders = [];
        tableRows = [];
      }
    }

    // Horizontal Rule
    if (trimmed === "---") {
      renderedElements.push(<hr key={index} style={{ border: "0", borderTop: "1px solid hsl(var(--border))", margin: "20px 0" }} />);
      return;
    }

    // Headers (High contrast slate text!)
    if (trimmed.startsWith("### ")) {
      renderedElements.push(<h3 key={index} style={{ fontSize: "1.05rem", marginTop: "18px", marginBottom: "8px", color: "hsl(var(--text-primary))", fontWeight: 700 }}>{parseInlineMarkdown(trimmed.substring(4))}</h3>);
      return;
    }
    if (trimmed.startsWith("## ")) {
      renderedElements.push(<h2 key={index} style={{ fontSize: "1.2rem", marginTop: "24px", marginBottom: "12px", color: "hsl(var(--text-primary))", fontWeight: 700, borderBottom: "1px solid hsl(var(--border))", paddingBottom: "6px" }}>{parseInlineMarkdown(trimmed.substring(3))}</h2>);
      return;
    }
    if (trimmed.startsWith("# ")) {
      renderedElements.push(<h1 key={index} style={{ fontSize: "1.5rem", marginTop: "28px", marginBottom: "16px", color: "hsl(var(--text-primary))", fontWeight: 800 }}>{parseInlineMarkdown(trimmed.substring(2))}</h1>);
      return;
    }

    // Bullet List Items
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      renderedElements.push(
        <li key={index} style={{ marginLeft: "20px", marginBottom: "4px", fontSize: "0.92rem", color: "hsl(var(--text-secondary))" }}>
          {parseInlineMarkdown(trimmed.substring(2))}
        </li>
      );
      return;
    }

    // Numbered List Items
    const numMatch = trimmed.match(/^(\d+)\.\s(.*)/);
    if (numMatch) {
      renderedElements.push(
        <li key={index} style={{ marginLeft: "20px", marginBottom: "4px", listStyleType: "decimal", fontSize: "0.92rem", color: "hsl(var(--text-secondary))" }}>
          {parseInlineMarkdown(numMatch[2])}
        </li>
      );
      return;
    }

    // Blockquotes
    if (trimmed.startsWith("> ")) {
      renderedElements.push(
        <blockquote key={index} style={{ borderLeft: "3.5px solid hsl(var(--accent))", paddingLeft: "16px", margin: "12px 0", color: "hsl(var(--text-secondary))", fontStyle: "italic", backgroundColor: "hsl(var(--bg-base))", paddingTop: "6px", paddingBottom: "6px", borderRadius: "0 var(--radius-sm) var(--radius-sm) 0" }}>
          {parseInlineMarkdown(trimmed.substring(2))}
        </blockquote>
      );
      return;
    }

    // Empty Lines
    if (!trimmed) {
      renderedElements.push(<div key={index} style={{ height: "6px" }} />);
      return;
    }

    // Standard Paragraphs
    renderedElements.push(
      <p key={index} style={{ fontSize: "0.92rem", lineHeight: "1.6", color: "hsl(var(--text-secondary))", marginBottom: "12px" }}>
        {parseInlineMarkdown(line)}
      </p>
    );
  });

  // Flush remaining table
  if (inTable) {
    renderedElements.push(renderTable(tableHeaders, tableRows, lines.length));
  }

  return <div className="markdown-body">{renderedElements}</div>;
};

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  messages,
  onSendMessage,
  isGenerating,
  activeSteps,
  errorMsg
}) => {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, activeSteps]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isGenerating) return;

    const query = input;
    setInput("");

    const newMessages: Message[] = [
      ...messages,
      { role: "user", content: query }
    ];

    await onSendMessage(query, newMessages);
  };

  const handleExportMarkdown = (msgContent: string) => {
    const element = document.createElement("a");
    const file = new Blob([msgContent], { type: "text/markdown" });
    element.href = URL.createObjectURL(file);
    element.download = "Financial_Analysis_Report.md";
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="glass-panel chat-container" style={{ border: "1px solid hsl(var(--border))" }}>
      {/* Header */}
      <div className="chat-header">
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Bot size={18} style={{ color: "hsl(var(--accent))" }} />
          <div>
            <h3 style={{ fontSize: "0.9rem", fontWeight: 700 }}>Financial Analyst Workstation</h3>
            <span style={{ fontSize: "0.72rem", color: "hsl(var(--text-muted))" }}>Custom ReAct Loop + Local LLM RAG</span>
          </div>
        </div>
        <Sparkles size={15} className={isGenerating ? "animate-pulse" : ""} style={{ color: "hsl(var(--accent))", opacity: isGenerating ? 1 : 0.4 }} />
      </div>

      {/* Messages Window */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", gap: "12px", textAlign: "center", color: "hsl(var(--text-muted))" }}>
            <Sparkles size={28} style={{ color: "hsl(var(--accent))", marginBottom: "4px" }} />
            <h4 style={{ color: "hsl(var(--text-primary))", fontWeight: 700 }}>Financial Agentic RAG Orchestrator</h4>
            <p style={{ fontSize: "0.82rem", maxWidth: "340px", lineHeight: 1.5, color: "hsl(var(--text-secondary))" }}>
              Welcome! I can inspect real-time historical market valuations, parse uploaded financial reports, and execute web queries to aggregate the latest macroeconomic sentiments.
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "8px", marginTop: "12px" }}>
              <span className="logo-badge" style={{ cursor: "pointer", textTransform: "none", borderRadius: "6px" }} onClick={() => setInput("Analyze Tesla's financial performance from the last quarter")}>Tesla Quarterly Analysis</span>
              <span className="logo-badge" style={{ cursor: "pointer", textTransform: "none", borderRadius: "6px" }} onClick={() => setInput("Compare the P/E and revenue growth of AAPL and MSFT")}>Compare P/E Ratios</span>
              <span className="logo-badge" style={{ cursor: "pointer", textTransform: "none", borderRadius: "6px" }} onClick={() => setInput("What is the latest market sentiment regarding Nvidia (NVDA)?")}>NVDA Market News</span>
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="message-avatar">
                {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
              </div>
              <div className="message-content">
                <div className="message-bubble">
                  {msg.role === "user" ? (
                    <span style={{ whiteSpace: "pre-line" }}>{msg.content}</span>
                  ) : (
                    <>
                      {/* Accordion steps (Reasoning Trace) if present */}
                      {msg.steps && msg.steps.length > 0 && (
                        <div style={{ marginBottom: "14px" }}>
                          <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "hsl(var(--text-muted))", textTransform: "uppercase", letterSpacing: "0.05em", display: "block", marginBottom: "8px" }}>
                            Agent Reasoning Trace:
                          </span>
                          {msg.steps.map((step) => (
                            <AgentTrace key={step.step} step={step} />
                          ))}
                        </div>
                      )}
                      
                      {/* Markdown Final Answer Body */}
                      <MarkdownRenderer text={msg.content} />
                      
                      {/* Actions footer (Export/Save) */}
                      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "12px", borderTop: "1px solid hsl(var(--border))", paddingTop: "8px" }}>
                        <button 
                          onClick={() => handleExportMarkdown(msg.content)}
                          style={{ background: "transparent", border: "none", color: "hsl(var(--text-muted))", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px", fontSize: "0.72rem", padding: "4px 8px", borderRadius: "4px", transition: "all var(--transition-fast)" }}
                          title="Download report (.md)"
                          className="logo-badge"
                        >
                          <Download size={11} />
                          Export Report
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))
        )}

        {/* Live Reasoning steps streaming in real time */}
        {isGenerating && activeSteps.length > 0 && (
          <div className="message assistant">
            <div className="message-avatar">
              <Bot size={16} />
            </div>
            <div className="message-content" style={{ width: "100%" }}>
              <div className="message-bubble" style={{ width: "100%" }}>
                <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "hsl(var(--text-muted))", textTransform: "uppercase", letterSpacing: "0.05em", display: "block", marginBottom: "8px" }}>
                  Agent Executing (Latency depends on CPU):
                </span>
                {activeSteps.map((step) => (
                  <AgentTrace key={step.step} step={step} />
                ))}
                <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "hsl(var(--accent))", fontSize: "0.78rem", marginTop: "8px" }}>
                  <Loader2 className="animate-spin" size={13} />
                  <span>Aggregating observations and formulating next steps...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Error notification */}
        {errorMsg && (
          <div className="glass-panel" style={{ display: "flex", gap: "10px", padding: "12px 16px", borderColor: "rgba(225, 29, 72, 0.2)", background: "rgba(225, 29, 72, 0.03)", color: "hsl(var(--error))", borderRadius: "var(--radius-md)", margin: "10px 0" }}>
            <AlertCircle size={15} style={{ flexShrink: 0, marginTop: "2px" }} />
            <div style={{ fontSize: "0.78rem" }}>
              <strong>System Error:</strong> {errorMsg}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Tray */}
      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={isGenerating ? "Agent is reasoning, please wait..." : "Ask about uploaded financial sheets or enter a stock ticker..."}
          className="chat-input"
          disabled={isGenerating}
        />
        <button
          type="submit"
          className="chat-send-btn"
          disabled={!input.trim() || isGenerating}
        >
          {isGenerating ? (
            <Loader2 className="animate-spin" size={16} />
          ) : (
            <Send size={16} />
          )}
        </button>
      </form>
    </div>
  );
};
