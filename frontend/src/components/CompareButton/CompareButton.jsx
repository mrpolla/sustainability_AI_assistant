import React from "react";

const CompareButton = ({ onClick, disabled, loading }) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      style={{
        padding: "0.6rem 1.2rem",
        backgroundColor: disabled || loading ? "#444" : "#4caf50",
        color: disabled || loading ? "#aaa" : "white",
        border: "none",
        borderRadius: "4px",
        cursor: disabled || loading ? "not-allowed" : "pointer",
        fontWeight: "medium",
        fontSize: "0.95rem",
        transition: "background-color 0.2s",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {loading && (
        <span
          style={{
            display: "inline-block",
            width: "16px",
            height: "16px",
            border: "2px solid rgba(255, 255, 255, 0.3)",
            borderTop: "2px solid #fff",
            borderRadius: "50%",
            marginRight: "8px",
            animation: "compareSpin 1s linear infinite",
          }}
        />
      )}
      <style>{`
        @keyframes compareSpin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
      {loading ? "Comparing..." : "Compare"}
    </button>
  );
};

export default CompareButton;
