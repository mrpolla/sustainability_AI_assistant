import React from "react";
import LoadingButton from "../LoadingButton/LoadingButton.jsx";

const QuestionForm = ({ question, setQuestion, handleSubmit, loading }) => {
  return (
    <div>
      <textarea
        placeholder="Ask a question about EPD data..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        rows={4}
        cols={60}
      />
      <br />
      <br />
      <LoadingButton
        onClick={handleSubmit}
        loading={loading}
        text="Ask"
        loadingText="Asking..."
      />
    </div>
  );
};

export default QuestionForm;
