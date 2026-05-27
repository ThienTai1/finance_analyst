import React, { useState } from "react";
import { ChevronDown, ChevronUp, Bot, Hammer, Eye, Lightbulb } from "lucide-react";

export interface AgentStep {
  step: number;
  thought: string;
  action: string;
  parameters: any;
  observation?: string;
}

interface AgentTraceProps {
  step: AgentStep;
}

export const AgentTrace: React.FC<AgentTraceProps> = ({ step }) => {
  const [isOpen, setIsOpen] = useState(false);

  const getToolDisplayName = (name: string) => {
    switch (name) {
      case "VectorSearch": return "Search PDF RAG Knowledge Base";
      case "StockData": return "Retrieve Stock Valuation (yfinance)";
      case "WebSearch": return "Execute Live Web Query (DuckDuckGo)";
      case "Hoàn thành": return "Formulate Final Investment Report";
      case "Finished": return "Formulate Final Investment Report";
      default: return name;
    }
  };

  const isCompleted = step.action === "Hoàn thành" || step.action === "Finished";

  return (
    <div className="agent-trace-box" style={{ borderStyle: isCompleted ? "solid" : "dashed", borderColor: isCompleted ? "rgba(16, 185, 129, 0.3)" : "rgba(6, 182, 212, 0.2)" }}>
      <div 
        className="trace-header" 
        onClick={() => setIsOpen(!isOpen)}
        style={{ backgroundColor: isCompleted ? "rgba(16, 185, 129, 0.05)" : "rgba(6, 182, 212, 0.06)" }}
      >
        <div className="trace-title" style={{ color: isCompleted ? "hsl(var(--success))" : "hsl(var(--accent))" }}>
          {isCompleted ? <Bot size={16} /> : <Hammer size={16} />}
          <span>Step {step.step}: {getToolDisplayName(step.action)}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span className="trace-status" style={{ backgroundColor: isCompleted ? "rgba(16, 185, 129, 0.15)" : "rgba(6, 182, 212, 0.1)", color: isCompleted ? "hsl(var(--success))" : "hsl(var(--accent))" }}>
            {isCompleted ? "Finished" : "Running..."}
          </span>
          {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {isOpen && (
        <div className="trace-content">
          {/* Thought */}
          {step.thought && (
            <div className="trace-section">
              <span className="trace-section-label" style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <Lightbulb size={12} style={{ color: "hsl(var(--warning))" }} />
                Agent Thoughts & Strategy
              </span>
              <div className="trace-section-value thought">
                {step.thought}
              </div>
            </div>
          )}

          {/* Action & Parameters */}
          {!isCompleted && step.action && (
            <div className="trace-section">
              <span className="trace-section-label" style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <Hammer size={12} style={{ color: "hsl(var(--primary))" }} />
                Execute Tool ({step.action})
              </span>
              <div className="trace-section-value code">
                {JSON.stringify(step.parameters, null, 2)}
              </div>
            </div>
          )}

          {/* Observation */}
          {step.observation && (
            <div className="trace-section">
              <span className="trace-section-label" style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <Eye size={12} style={{ color: "hsl(var(--accent))" }} />
                Received Observation
              </span>
              <div 
                className="trace-section-value code" 
                style={{ 
                  maxHeight: "180px", 
                  overflowY: "auto", 
                  whiteSpace: "pre-wrap", 
                  color: "#a9b1d6", 
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.75rem"
                }}
              >
                {step.observation}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
