import React from "react";

/**
 * Component for displaying AI analysis results
 */
const AIAnalysisPanel = ({ onAnalyse, loading, result, error, disabled }) => {
  return (
    <div style={{ marginTop: "1.5rem" }}>
      <button
        onClick={onAnalyse}
        disabled={loading || disabled}
        style={{
          padding: "0.5rem 1rem",
          backgroundColor: "#4a5568",
          color: "#e0e0e0",
          border: "none",
          borderRadius: "4px",
          cursor: loading || disabled ? "not-allowed" : "pointer",
          fontSize: "0.9rem",
          opacity: loading || disabled ? 0.7 : 1,
        }}
      >
        {loading ? "Analysing..." : "Analyse results with AI"}
      </button>

      {/* Show loading indicator */}
      {loading && (
        <div style={{ marginTop: "1rem", color: "#90caf9" }}>
          Processing analysis, please wait...
        </div>
      )}

      {/* Show error message */}
      {error && (
        <div
          style={{
            marginTop: "1rem",
            padding: "1rem",
            backgroundColor: "#2d1e1e",
            borderRadius: "4px",
            border: "1px solid #f44336",
            color: "#f44336",
          }}
        >
          <strong>Analysis Error:</strong> {error}
        </div>
      )}

      {/* Show AI result */}
      {result && !loading && !error && (
        <div
          style={{
            marginTop: "1rem",
            padding: "1rem",
            backgroundColor: "#1e2a3a",
            borderRadius: "4px",
            border: "1px solid #4a5568",
            color: "#e0e0e0",
          }}
        >
          <h3 style={{ margin: "0 0 0.5rem 0", color: "#90caf9" }}>
            AI Analysis
          </h3>
          <div style={{ whiteSpace: "pre-line" }}>{result}</div>
        </div>
      )}
    </div>
  );
};

export default AIAnalysisPanel;
