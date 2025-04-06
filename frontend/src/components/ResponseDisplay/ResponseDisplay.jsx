import React from "react";

const ResponseDisplay = ({ answer }) => {
  return (
    <div style={{ marginTop: "2rem" }}>
      <strong style={{ color: "#90caf9" }}>Answer:</strong>
      <pre
        style={{
          backgroundColor: "#1e1e1e",
          padding: "1rem",
          borderRadius: "4px",
          border: "1px solid #444",
          color: "#e0e0e0",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {answer}
      </pre>
    </div>
  );
};

export default ResponseDisplay;
