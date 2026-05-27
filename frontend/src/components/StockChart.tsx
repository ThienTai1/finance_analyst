import React, { useState, useMemo } from "react";
import { TrendingUp, Activity, BookOpen } from "lucide-react";

interface ChartDataPoint {
  date: string;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  volume?: number;
}

interface Fundamentals {
  name: string;
  ticker: string;
  sector: string;
  industry: string;
  price: number;
  currency: string;
  market_cap: number;
  pe_ratio_formatted: string;
  dividend_yield: string;
  debt_to_equity: string;
  profit_margin: string;
  revenue_growth: string;
  summary?: string;
}

interface StockChartProps {
  ticker: string | null;
  fundamentals: Fundamentals | null;
  chartData: ChartDataPoint[];
}

export const StockChart: React.FC<StockChartProps> = ({
  ticker,
  fundamentals,
  chartData
}) => {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  // SVG parameters
  const width = 450;
  const height = 180;
  const paddingLeft = 35;
  const paddingRight = 10;
  const paddingTop = 15;
  const paddingBottom = 20;

  // Compute min/max limits for charting scaling
  const prices = useMemo(() => {
    return chartData.map(d => d.close).filter((c): c is number => c !== undefined && c !== null);
  }, [chartData]);

  const volumes = useMemo(() => {
    return chartData.map(d => d.volume).filter((v): v is number => v !== undefined && v !== null);
  }, [chartData]);

  const limits = useMemo(() => {
    if (prices.length === 0) return { minPrice: 0, maxPrice: 100, minVol: 0, maxVol: 100 };
    const minP = Math.min(...prices) * 0.98; // Add 2% padding
    const maxP = Math.max(...prices) * 1.02; // Add 2% padding
    const maxV = Math.max(...volumes);
    return { minPrice: minP, maxPrice: maxP, minVol: 0, maxVol: maxV };
  }, [prices, volumes]);

  const { minPrice, maxPrice, maxVol } = limits;

  // Helper coordinate mapper
  const getCoordinates = (index: number, val: number) => {
    if (chartData.length <= 1) return { x: paddingLeft, y: height - paddingBottom };
    const xRange = width - paddingLeft - paddingRight;
    const yRange = height - paddingTop - paddingBottom;
    
    const x = paddingLeft + (index / (chartData.length - 1)) * xRange;
    const y = height - paddingBottom - ((val - minPrice) / (maxPrice - minPrice)) * yRange;
    return { x, y };
  };

  // Build the SVG path string
  const linePath = useMemo(() => {
    if (chartData.length < 2) return "";
    let d = "";
    chartData.forEach((point, i) => {
      if (point.close !== undefined) {
        const { x, y } = getCoordinates(i, point.close);
        d += i === 0 ? `M ${x} ${y}` : ` L ${x} ${y}`;
      }
    });
    return d;
  }, [chartData, minPrice, maxPrice]);

  // Build area gradient path
  const areaPath = useMemo(() => {
    if (chartData.length < 2) return "";
    const firstPoint = getCoordinates(0, chartData[0].close || minPrice);
    const lastPoint = getCoordinates(chartData.length - 1, chartData[chartData.length - 1].close || minPrice);
    
    return `${linePath} L ${lastPoint.x} ${height - paddingBottom} L ${firstPoint.x} ${height - paddingBottom} Z`;
  }, [linePath, chartData, minPrice, maxPrice]);

  // Track hover coordinate to find nearest data point
  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement, MouseEvent>) => {
    if (chartData.length === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    
    const xRange = width - paddingLeft - paddingRight;
    const hoverPct = (x - paddingLeft) / xRange;
    let idx = Math.round(hoverPct * (chartData.length - 1));
    idx = Math.max(0, Math.min(chartData.length - 1, idx));
    setHoverIndex(idx);
  };

  const handleMouseLeave = () => {
    setHoverIndex(null);
  };

  const activePoint = hoverIndex !== null ? chartData[hoverIndex] : null;

  const formatMarketCap = (num: number) => {
    if (num >= 1e12) return `${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `${(num / 1e6).toFixed(2)}M`;
    return num.toLocaleString();
  };

  if (!ticker || !fundamentals || chartData.length === 0) {
    return (
      <div className="glass-panel chart-panel" style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "40px 24px", textAlign: "center", minHeight: "400px" }}>
        <TrendingUp size={44} style={{ color: "hsl(var(--text-muted))", marginBottom: "16px", opacity: 0.5 }} />
        <h3 style={{ marginBottom: "8px", fontWeight: 700, fontSize: "1rem" }}>Thiếu dữ liệu thị trường</h3>
        <p style={{ color: "hsl(var(--text-muted))", fontSize: "0.82rem", maxWidth: "320px", lineHeight: 1.5 }}>
          Hệ thống đang sẵn sàng. Hãy yêu cầu Agent phân tích cổ phiếu cụ thể (ví dụ: "Phân tích giá cổ phiếu AAPL" hoặc "So sánh NVDA") để vẽ biểu đồ và hiển thị các tỷ số tài chính.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-panel chart-panel" style={{ border: "1px solid hsl(var(--border))" }}>
      {/* Chart Header */}
      <div className="panel-header" style={{ borderBottom: "none", paddingBottom: 0 }}>
        <div style={{ overflow: "hidden", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span className="chart-header-ticker">{fundamentals.ticker}</span>
            <span className="logo-badge" style={{ backgroundColor: "rgba(79, 70, 229, 0.08)", color: "hsl(var(--accent))", borderColor: "rgba(79, 70, 229, 0.15)", textTransform: "none", borderRadius: "6px" }}>
              {fundamentals.sector}
            </span>
          </div>
          <span style={{ fontSize: "0.78rem", color: "hsl(var(--text-secondary))", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap", marginTop: "2px" }}>
            {fundamentals.name}
          </span>
        </div>
        <div style={{ textAlign: "right" }}>
          <div className="chart-header-price">
            {activePoint?.close ? activePoint.close.toFixed(2) : fundamentals.price.toFixed(2)}
            <span className="chart-header-currency">{fundamentals.currency}</span>
          </div>
          <span style={{ fontSize: "0.68rem", color: "hsl(var(--text-muted))" }}>
            {activePoint?.date ? `Ngày: ${activePoint.date}` : "Cập nhật gần nhất"}
          </span>
        </div>
      </div>

      {/* SVG Price Chart */}
      <div className="svg-chart-container" style={{ marginTop: "8px" }}>
        <svg
          width="100%"
          height="100%"
          viewBox={`0 0 ${width} ${height}`}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          style={{ overflow: "visible" }}
        >
          <defs>
            <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity="0.12" />
              <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity="0.00" />
            </linearGradient>
            <linearGradient id="lineGlow" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="hsl(var(--accent))" />
              <stop offset="100%" stopColor="hsl(var(--accent-light))" />
            </linearGradient>
          </defs>

          {/* Grid lines (Y-axis grid guides) */}
          {[0, 0.25, 0.5, 0.75, 1].map((p, idx) => {
            const val = minPrice + p * (maxPrice - minPrice);
            const { y } = getCoordinates(0, val);
            return (
              <g key={idx}>
                <line
                  x1={paddingLeft}
                  y1={y}
                  x2={width - paddingRight}
                  y2={y}
                  stroke="hsl(var(--border))"
                  strokeWidth="0.5"
                  strokeDasharray="2 3"
                />
                <text
                  x={paddingLeft - 6}
                  y={y + 3}
                  fill="hsl(var(--text-muted))"
                  fontSize="7.5"
                  fontWeight="600"
                  textAnchor="end"
                >
                  {val.toFixed(1)}
                </text>
              </g>
            );
          })}

          {/* Gradient Area Fill */}
          {areaPath && (
            <path d={areaPath} fill="url(#chartGradient)" />
          )}

          {/* Stroke Trendline */}
          {linePath && (
            <path
              d={linePath}
              fill="none"
              stroke="url(#lineGlow)"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Volume bars at the bottom */}
          {chartData.map((d, i) => {
            if (d.volume === undefined || d.volume === null) return null;
            const xRange = width - paddingLeft - paddingRight;
            const barWidth = Math.max(1, (xRange / chartData.length) * 0.5);
            const { x } = getCoordinates(i, minPrice);
            const barHeight = (d.volume / maxVol) * 22; // Scale volume to 22px max height
            const y = height - paddingBottom - barHeight;
            
            return (
              <rect
                key={i}
                x={x - barWidth / 2}
                y={y}
                width={barWidth}
                height={barHeight}
                fill="hsl(var(--accent))"
                opacity={hoverIndex === i ? 0.25 : 0.08}
              />
            );
          })}

          {/* Interactive cursor line and active bubble */}
          {hoverIndex !== null && activePoint && activePoint.close !== undefined && (
            <g>
              <line
                x1={getCoordinates(hoverIndex, activePoint.close).x}
                y1={paddingTop}
                x2={getCoordinates(hoverIndex, activePoint.close).x}
                y2={height - paddingBottom}
                stroke="hsl(var(--accent))"
                strokeWidth="1"
                opacity="0.3"
              />
              <circle
                cx={getCoordinates(hoverIndex, activePoint.close).x}
                cy={getCoordinates(hoverIndex, activePoint.close).y}
                r="4"
                fill="hsl(var(--accent))"
                stroke="white"
                strokeWidth="1.5"
                style={{ filter: "drop-shadow(0px 2px 4px rgba(79, 70, 229, 0.4))" }}
              />
            </g>
          )}

          {/* X Axis Line */}
          <line
            x1={paddingLeft}
            y1={height - paddingBottom}
            x2={width - paddingRight}
            y2={height - paddingBottom}
            stroke="hsl(var(--border))"
            strokeWidth="1"
          />

          {/* Start and End Dates */}
          <text
            x={paddingLeft}
            y={height - 6}
            fill="hsl(var(--text-muted))"
            fontSize="7.5"
            fontWeight="500"
            textAnchor="start"
          >
            {chartData[0]?.date}
          </text>
          <text
            x={width - paddingRight}
            y={height - 6}
            fill="hsl(var(--text-muted))"
            fontSize="7.5"
            fontWeight="500"
            textAnchor="end"
          >
            {chartData[chartData.length - 1]?.date}
          </text>
        </svg>
      </div>

      {/* Fundamentals Dashboard Grid */}
      <div style={{ padding: "0 16px 8px 16px", marginTop: "4px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "hsl(var(--text-primary))", fontSize: "0.78rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
          <Activity size={14} style={{ color: "hsl(var(--accent))" }} />
          <span>Thông số cơ bản</span>
        </div>
      </div>
      
      <div className="fundamentals-grid" style={{ margin: "0 16px 12px 16px", padding: 0, gap: "10px" }}>
        <div className="fundamental-card" style={{ padding: "10px 12px" }}>
          <span className="fundamental-label">Vốn hóa (Market Cap)</span>
          <span className="fundamental-value">{formatMarketCap(fundamentals.market_cap)}</span>
        </div>
        <div className="fundamental-card" style={{ padding: "10px 12px" }}>
          <span className="fundamental-label">Hệ số P/E (Trailing)</span>
          <span className="fundamental-value">{fundamentals.pe_ratio_formatted}</span>
        </div>
        <div className="fundamental-card" style={{ padding: "10px 12px" }}>
          <span className="fundamental-label">Tỷ suất LN (Profit Margin)</span>
          <span className="fundamental-value">{fundamentals.profit_margin}</span>
        </div>
        <div className="fundamental-card" style={{ padding: "10px 12px" }}>
          <span className="fundamental-label">Tỷ lệ Nợ/VCSH (D/E)</span>
          <span className="fundamental-value">{fundamentals.debt_to_equity}</span>
        </div>
        <div className="fundamental-card" style={{ gridColumn: "span 2", padding: "10px 12px" }}>
          <span className="fundamental-label">Tỷ suất cổ tức | Tăng trưởng DT</span>
          <span className="fundamental-value" style={{ fontSize: "0.85rem" }}>
            {fundamentals.dividend_yield} | {fundamentals.revenue_growth} (YoY)
          </span>
        </div>
      </div>

      {/* Business Brief */}
      {fundamentals.summary && (
        <div style={{ padding: "0 16px 16px 16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "hsl(var(--text-primary))", fontSize: "0.78rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>
            <BookOpen size={14} style={{ color: "hsl(var(--accent))" }} />
            <span>Tóm tắt hoạt động kinh doanh</span>
          </div>
          <p style={{ fontSize: "0.75rem", color: "hsl(var(--text-secondary))", lineHeight: 1.5, height: "70px", overflowY: "auto", padding: "8px 12px", backgroundColor: "hsl(var(--bg-base))", border: "1px solid hsl(var(--border))", borderRadius: "var(--radius-sm)" }}>
            {fundamentals.summary}
          </p>
        </div>
      )}
    </div>
  );
};
