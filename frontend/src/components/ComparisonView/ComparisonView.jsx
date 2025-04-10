import React from "react";
import ComparisonTable from "../ComparisonTable";

const ComparisonView = ({ comparisonData, loading, error, onClose }) => {
  if (loading) {
    return (
      <div
        style={{
          padding: "1rem",
          backgroundColor: "#1e1e1e",
          borderRadius: "4px",
          textAlign: "center",
          color: "#e0e0e0",
        }}
      >
        <div
          style={{
            marginBottom: "1rem",
            fontSize: "1.1rem",
          }}
        >
          Loading comparison data...
        </div>
        <div
          style={{
            display: "inline-block",
            width: "40px",
            height: "40px",
            border: "3px solid rgba(255, 255, 255, 0.3)",
            borderTop: "3px solid #90caf9",
            borderRadius: "50%",
            animation: "spin 1s linear infinite",
          }}
        />
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          padding: "1rem",
          backgroundColor: "#1e1e1e",
          borderRadius: "4px",
          color: "#f44336",
          border: "1px solid #f44336",
        }}
      >
        <h3 style={{ margin: "0 0 0.5rem 0" }}>Error Loading Comparison</h3>
        <p style={{ margin: 0 }}>{error}</p>
      </div>
    );
  }

  if (
    !comparisonData ||
    !comparisonData.indicators ||
    comparisonData.indicators.length === 0
  ) {
    return (
      <div
        style={{
          padding: "1rem",
          backgroundColor: "#1e1e1e",
          borderRadius: "4px",
          color: "#e0e0e0",
        }}
      >
        <h3 style={{ margin: "0 0 0.5rem 0" }}>No Comparison Data</h3>
        <p style={{ margin: 0 }}>
          Select products and indicators, then click Compare to view comparison
          data.
        </p>
      </div>
    );
  }

  const { indicators, products, modules = [] } = comparisonData;

  return (
    <div>
      {/* Header with title and hide button */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid #444",
          paddingBottom: "0.5rem",
          marginBottom: "1.5rem",
        }}
      >
        <h2 style={{ color: "#90caf9", margin: 0 }}>Comparison Results</h2>
        <button
          onClick={onClose}
          style={{
            padding: "0.5rem 1rem",
            backgroundColor: "#333",
            color: "#e0e0e0",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "0.9rem",
          }}
        >
          Hide Comparison
        </button>
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <p
          style={{ color: "#aaa", fontSize: "0.9rem", margin: "0 0 0.25rem 0" }}
        >
          Comparing {products.length} product{products.length !== 1 ? "s" : ""}{" "}
          across {indicators.length} indicator
          {indicators.length !== 1 ? "s" : ""}
        </p>
      </div>

      {indicators.map((indicator, index) => (
        <ComparisonTable
          key={`${indicator.name}-${index}`}
          indicator={indicator}
          products={products}
          modules={modules}
        />
      ))}
    </div>
  );
};

export default ComparisonView;
