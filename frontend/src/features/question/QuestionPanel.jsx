import React from "react";
import QuestionForm from "../../components/QuestionForm";
import ResponseDisplay from "../../components/ResponseDisplay";

// Constants
const LLM_OPTIONS = ["mistral", "llama3", "gemma:2b", "qwen:1.8b", "phi3:mini"];

/**
 * Component for question and answer functionality
 */
const QuestionPanel = ({
  question,
  setQuestion,
  handleSubmit,
  loading,
  error,
  answer,
  selectedLLM,
  handleLLMChange,
  disabled,
}) => {
  return (
    <div>
      <div style={{ marginTop: "1.5rem" }}>
        <h3>Ask a Question</h3>

        {/* LLM Selection Dropdown */}
        <div style={{ marginBottom: "1rem" }}>
          <label
            htmlFor="llm-select"
            style={{
              display: "block",
              marginBottom: "0.5rem",
              color: "#e0e0e0",
            }}
          >
            Select LLM Model
          </label>
          <select
            id="llm-select"
            value={selectedLLM}
            onChange={handleLLMChange}
            disabled={disabled}
            style={{
              width: "100%",
              padding: "0.5rem",
              backgroundColor: "#333",
              color: "#e0e0e0",
              border: "1px solid #555",
              borderRadius: "4px",
              opacity: disabled ? 0.6 : 1,
            }}
          >
            {LLM_OPTIONS.map((llm) => (
              <option key={llm} value={llm}>
                {llm}
              </option>
            ))}
          </select>
        </div>

        <QuestionForm
          question={question}
          setQuestion={setQuestion}
          handleSubmit={handleSubmit}
          loading={loading}
          error={error}
          disabled={disabled}
        />
      </div>

      <ResponseDisplay answer={answer} loading={loading} />
    </div>
  );
};

export default QuestionPanel;
