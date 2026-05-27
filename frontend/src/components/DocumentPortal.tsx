import React, { useState, useEffect, useRef } from "react";
import { Upload, FileText, Trash2, Loader2, Info, Database, CheckCircle2, ShieldCheck } from "lucide-react";

interface PDFDocument {
  filename: string;
  size_bytes: number;
  size_mb: number;
}

interface DocumentPortalProps {
  onRefreshTrigger?: number;
  onIngestSuccess?: (filename: string) => void;
  fullWidth?: boolean; // Enable sprawling SaaS admin layout!
}

export const DocumentPortal: React.FC<DocumentPortalProps> = ({
  onRefreshTrigger = 0,
  onIngestSuccess,
  fullWidth = false
}) => {
  const [documents, setDocuments] = useState<PDFDocument[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  useEffect(() => {
    fetchDocuments();
  }, [onRefreshTrigger]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      await uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file: File) => {
    if (!file.name.endsWith(".pdf")) {
      setError("Only PDF files (.pdf) are supported.");
      return;
    }
    
    setIsUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Upload failed");
      }

      await fetchDocuments();
      if (onIngestSuccess) {
        onIngestSuccess(file.name);
      }
    } catch (err: any) {
      setError(err.message || "File upload and processing error");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDelete = async (filename: string) => {
    if (!confirm(`Are you sure you want to delete the document '${filename}' from the database?`)) return;
    try {
      const res = await fetch(`http://localhost:8000/api/documents/${encodeURIComponent(filename)}`, {
        method: "DELETE",
      });

      if (res.ok) {
        setDocuments(documents.filter((doc) => doc.filename !== filename));
      }
    } catch (err) {
      setError("Could not delete the document.");
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  // 1. Sidebar narrow mode (default)
  if (!fullWidth) {
    return (
      <div className="glass-panel sidebar-panel">
        <div className="panel-header">
          <span className="panel-title">RAG Documents ({documents.length})</span>
        </div>

        <div
          className={`upload-zone ${dragActive ? "active" : ""}`}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={triggerFileInput}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInputChange}
            accept=".pdf"
            style={{ display: "none" }}
          />
          {isUploading ? (
            <>
              <Loader2 className="upload-icon animate-spin" size={20} style={{ color: "hsl(var(--accent))" }} />
              <span className="upload-text">Extracting & indexing...</span>
              <span className="upload-subtext">Running FastEmbed locally</span>
            </>
          ) : (
            <>
              <Upload className="upload-icon" size={20} />
              <span className="upload-text">Upload PDF Financial Report</span>
              <span className="upload-subtext">Click or drag & drop files here</span>
            </>
          )}
        </div>

        {error && (
          <div style={{ padding: "0 16px 12px 16px", color: "hsl(var(--error))", fontSize: "0.75rem", display: "flex", gap: "6px", alignItems: "center" }}>
            <Info size={14} />
            <span>{error}</span>
          </div>
        )}

        <div className="document-list">
          {documents.length === 0 ? (
            <div style={{ textAlign: "center", padding: "20px 0", color: "hsl(var(--text-muted))", fontSize: "0.78rem" }}>
              No RAG documents ingested yet.
            </div>
          ) : (
            documents.map((doc) => (
              <div key={doc.filename} className="document-item">
                <div className="document-info">
                  <FileText size={15} style={{ color: "hsl(var(--accent))", flexShrink: 0 }} />
                  <div style={{ overflow: "hidden" }}>
                    <div className="document-name" title={doc.filename}>{doc.filename}</div>
                    <div className="document-size">{doc.size_mb} MB</div>
                  </div>
                </div>
                <button
                  className="document-delete-btn"
                  onClick={() => handleDelete(doc.filename)}
                  title="Delete document"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    );
  }

  // 2. SaaS sprawling Full Width layout tab
  return (
    <div className="saas-tab-viewport">
      <div className="saas-full-panel glass-panel" style={{ height: "100%" }}>
        <div className="saas-hero-section">
          <h2 className="saas-hero-title">RAG Vector Storage Manager</h2>
          <p className="saas-hero-desc">
            Upload, manage, and inspect the metadata of financial documents indexed locally in the Qdrant database.
          </p>
        </div>

        <div className="benchmark-layout-grid" style={{ gridTemplateColumns: "1.2fr 1fr", gap: "32px", height: "auto" }}>
          {/* Left Column: Management */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>Indexed Reports Directory ({documents.length})</h3>
            </div>

            {/* Ingestion zone */}
            <div
              className={`upload-zone ${dragActive ? "active" : ""}`}
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={triggerFileInput}
              style={{ margin: "0 0 20px 0", padding: "40px 24px" }}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileInputChange}
                accept=".pdf"
                style={{ display: "none" }}
              />
              {isUploading ? (
                <>
                  <Loader2 className="upload-icon animate-spin" size={28} style={{ color: "hsl(var(--accent))" }} />
                  <span className="upload-text" style={{ fontSize: "0.9rem" }}>Executing RAG extraction and embeddings...</span>
                  <span className="upload-subtext">Running 100% locally using bge-small-en-v1.5 model via CPU</span>
                </>
              ) : (
                <>
                  <Upload className="upload-icon" size={28} style={{ color: "hsl(var(--accent))" }} />
                  <span className="upload-text" style={{ fontSize: "0.9rem" }}>Drag & drop PDF reports here to ingest into RAG</span>
                  <span className="upload-subtext">Supports quarterly/annual financial statement PDFs</span>
                </>
              )}
            </div>

            {error && (
              <div className="metric-pill" style={{ borderColor: "rgba(225,29,72,0.2)", backgroundColor: "rgba(225,29,72,0.03)", color: "hsl(var(--error))", marginBottom: "20px", display: "inline-flex", gap: "8px" }}>
                <Info size={14} />
                <span>{error}</span>
              </div>
            )}

            {/* List */}
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "300px", overflowY: "auto" }}>
              {documents.length === 0 ? (
                <div style={{ textAlign: "center", padding: "40px 0", border: "1px dashed hsl(var(--border))", borderRadius: "var(--radius-md)", color: "hsl(var(--text-muted))", fontSize: "0.85rem", backgroundColor: "hsl(var(--bg-base))" }}>
                  No PDF files found in the local RAG database. Upload your first report to start!
                </div>
              ) : (
                documents.map((doc) => (
                  <div key={doc.filename} className="document-item" style={{ padding: "14px 18px" }}>
                    <div className="document-info">
                      <FileText size={18} style={{ color: "hsl(var(--accent))" }} />
                      <div>
                        <div className="document-name" style={{ fontSize: "0.85rem" }}>{doc.filename}</div>
                        <div className="document-size" style={{ fontSize: "0.72rem" }}>Size: {doc.size_mb} MB | Format: PDF Document</div>
                      </div>
                    </div>
                    <button
                      className="document-delete-btn"
                      onClick={() => handleDelete(doc.filename)}
                      title="Delete document from Qdrant"
                      style={{ padding: "8px" }}
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Right Column: Database Telemetry Info */}
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "8px" }}>
              <Database size={16} style={{ color: "hsl(var(--accent))" }} />
              Qdrant Vector Database Telemetry
            </h3>

            {/* Status Grid Cards */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div className="fundamental-card" style={{ padding: "16px" }}>
                <span className="fundamental-label" style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <CheckCircle2 size={12} style={{ color: "hsl(var(--success))" }} />
                  Collection Status
                </span>
                <span className="fundamental-value" style={{ fontSize: "1.1rem" }}>financial_reports (ACTIVE)</span>
              </div>

              <div className="fundamental-card" style={{ padding: "16px" }}>
                <span className="fundamental-label">Local Embedding Model</span>
                <span className="fundamental-value" style={{ fontSize: "1.1rem" }}>BAAI/bge-small-en-v1.5 (ONNX optimized)</span>
              </div>

              <div className="fundamental-card" style={{ padding: "16px" }}>
                <span className="fundamental-label">Chunking & Overlap Strategy</span>
                <span className="fundamental-value" style={{ fontSize: "1.1rem" }}>1000 chars / 200 chars overlap</span>
              </div>

              <div className="fundamental-card" style={{ padding: "16px" }}>
                <span className="fundamental-label">Local persistent Storage Folder</span>
                <span className="fundamental-value" style={{ fontSize: "0.8rem", fontFamily: "var(--font-mono)", fontWeight: 500, color: "hsl(var(--text-secondary))" }}>
                  backend/app/qdrant_db/
                </span>
              </div>
            </div>

            {/* SaaS Quota Note */}
            <div style={{ padding: "16px", backgroundColor: "rgba(79, 70, 229, 0.03)", border: "1px solid rgba(79, 70, 229, 0.1)", borderRadius: "var(--radius-md)", fontSize: "0.8rem", lineHeight: 1.5, color: "hsl(var(--text-secondary))" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: 700, color: "hsl(var(--accent))", marginBottom: "6px" }}>
                <ShieldCheck size={16} />
                <span>100% Local Data Privacy</span>
              </div>
              All PDF documents uploaded here are parsed, embedded using FastEmbed, and saved to your local disk partition. The system never transmits any text contents to the internet, guaranteeing complete privacy for internal or confidential financial sheets.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
