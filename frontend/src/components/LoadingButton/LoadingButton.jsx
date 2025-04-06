import React from "react";

const LoadingButton = ({ onClick, loading, text, loadingText, disabled }) => {
  return (
    <button
      onClick={onClick}
      disabled={loading || disabled}
      style={{
        padding: "0.5rem 1rem",
        backgroundColor: loading || disabled ? "#444" : "#2979ff",
        color: loading || disabled ? "#aaa" : "white",
        border: "none",
        borderRadius: "4px",
        cursor: loading || disabled ? "not-allowed" : "pointer",
        fontWeight: "medium",
        transition: "background-color 0.2s",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minWidth: "120px",
      }}
    >
      {loading && (
        <span
          style={{
            display: "inline-block",
            width: "16px",
            height: "16px",
            border: "2px solid rgba(255, 255, 255, 0.3)",
            borderTop: "2px solid #666",
            borderRadius: "50%",
            marginRight: "8px",
            animation: "spin 1s linear infinite",
          }}
        />
      )}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
      {loading ? loadingText : text}
    </button>
  );
};

export default LoadingButton;
