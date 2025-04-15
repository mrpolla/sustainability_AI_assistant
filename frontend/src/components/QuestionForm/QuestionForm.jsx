import React from "react";
import LoadingButton from "../LoadingButton";

const QuestionForm = ({
  question,
  setQuestion,
  handleSubmit,
  loading,
  error,
}) => {
  const handleKeyPress = (e) => {
    if (e.key === "Enter" && e.ctrlKey) {
      handleSubmit();
    }
  };

  return (
    <div>
      <textarea
        placeholder="Ask a question about EPD data..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={handleKeyPress}
        rows={4}
        style={{
          width: "100%",
          padding: "0.5rem",
          border: error ? "1px solid #d32f2f" : "1px solid #444",
          borderRadius: "4px",
          resize: "vertical",
          backgroundColor: "#1e1e1e",
          color: "#e0e0e0",
          fontFamily:
            "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif",
          fontSize: "1rem",
          lineHeight: "1.5",
          letterSpacing: "0.015em",
        }}
      />
      {error && (
        <div
          style={{
            color: "#d32f2f",
            fontSize: "0.85rem",
            marginTop: "0.3rem",
            fontFamily:
              "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif",
          }}
        >
          {error}
        </div>
      )}
      <div
        style={{
          marginTop: "0.5rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <small
          style={{
            color: "#666",
            fontFamily:
              "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif",
            fontSize: "0.8rem",
          }}
        >
          Press Ctrl+Enter to submit
        </small>
        <LoadingButton
          onClick={handleSubmit}
          loading={loading}
          text="Ask Question"
          loadingText="Asking..."
        />
      </div>
    </div>
  );
};

export default QuestionForm;
