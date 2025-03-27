import React, { useState } from "react";

function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!question) return;
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question }),
      });
      const data = await response.json();
      setAnswer(data.answer);
    } catch (err) {
      setAnswer("Error communicating with backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h2>EPD RAG Assistant</h2>
      <textarea
        placeholder="Ask a question about EPD data..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        rows={4}
        cols={60}
      />
      <br />
      <br />
      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Asking..." : "Ask"}
      </button>
      <div style={{ marginTop: "2rem" }}>
        <strong>Answer:</strong>
        <p>{answer}</p>
      </div>
    </div>
  );
}

export default App;
