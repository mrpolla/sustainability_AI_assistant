import React, { useState, useEffect } from "react";
import Header from "./components/Header";
import SearchBox from "./components/SearchBox";
import CheckableList from "./components/CheckableList";
import QuestionForm from "./components/QuestionForm";
import ResponseDisplay from "./components/ResponseDisplay";
import { askQuestion } from "./services/api";

function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);

  // Sample items - in a real app, these would come from an API
  // You'll want to replace this with actual data from your backend
  useEffect(() => {
    // Simulating initial data
    setSearchResults([
      { id: "1", name: "Document 1" },
      { id: "2", name: "Document 2" },
      { id: "3", name: "Document 3" },
    ]);
  }, []);

  const handleSearch = async (searchTerm) => {
    // In a real app, this would call your API
    console.log("Searching for:", searchTerm);

    // Simulating search results
    // Replace with actual API call
    setSearchResults([
      { id: "1", name: `Result for "${searchTerm}" 1` },
      { id: "2", name: `Result for "${searchTerm}" 2` },
      { id: "3", name: `Result for "${searchTerm}" 3` },
      { id: "4", name: `Result for "${searchTerm}" 4` },
    ]);
  };

  const handleItemToggle = (itemId) => {
    setSelectedItems((prev) =>
      prev.includes(itemId)
        ? prev.filter((id) => id !== itemId)
        : [...prev, itemId]
    );
  };

  const handleSubmit = async () => {
    if (!question) return;
    setLoading(true);

    try {
      // You can now include selected items in your question API call
      const data = await askQuestion(question, selectedItems);
      setAnswer(data.answer);
    } catch (err) {
      setAnswer("Error communicating with backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        padding: "2rem",
        fontFamily: "sans-serif",
        maxWidth: "800px",
        margin: "0 auto",
      }}
    >
      <Header />

      {/* Search Box */}
      <div style={{ marginTop: "1.5rem", marginBottom: "1rem" }}>
        <h3>Search Documents</h3>
        <SearchBox onSearch={handleSearch} />
      </div>

      {/* Checkable List */}
      <div>
        <h3>Select Documents ({selectedItems.length} selected)</h3>
        <CheckableList
          items={searchResults}
          selectedItems={selectedItems}
          onItemToggle={handleItemToggle}
        />
      </div>

      {/* Question Form */}
      <div style={{ marginTop: "1.5rem" }}>
        <h3>Ask a Question</h3>
        <QuestionForm
          question={question}
          setQuestion={setQuestion}
          handleSubmit={handleSubmit}
          loading={loading}
        />
      </div>

      <ResponseDisplay answer={answer} />
    </div>
  );
}

export default App;
