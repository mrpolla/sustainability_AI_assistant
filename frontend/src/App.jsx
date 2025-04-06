import React, { useState } from "react";
import Header from "./components/Header";
import SearchBox from "./components/SearchBox";
import CheckableList from "./components/CheckableList";
import QuestionForm from "./components/QuestionForm";
import ResponseDisplay from "./components/ResponseDisplay";
import { askQuestion, searchProducts } from "./services/api";

function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);

  const [searchError, setSearchError] = useState("");

  const handleSearch = async (searchTerm) => {
    if (!searchTerm.trim()) {
      setSearchResults([]);
      setSearchError("");
      return;
    }

    setSearchLoading(true);
    setSearchError("");

    try {
      const data = await searchProducts(searchTerm);
      setSearchResults(data.items || []);
    } catch (error) {
      console.error("Search failed:", error);
      setSearchError(`Search failed: ${error.message || "Unknown error"}`);
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
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
    setAnswer("");

    try {
      // You can now include selected items in your question API call
      const data = await askQuestion(question, selectedItems);
      setAnswer(data.answer);
    } catch (err) {
      setAnswer(
        `Error communicating with backend: ${err.message || "Unknown error"}`
      );
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
        <h3>Search Products</h3>
        <SearchBox onSearch={handleSearch} />
        {searchError && (
          <div
            style={{
              color: "red",
              marginTop: "0.5rem",
              padding: "0.5rem",
              border: "1px solid #ffcccc",
              borderRadius: "4px",
              backgroundColor: "#fff8f8",
            }}
          >
            {searchError}
          </div>
        )}
      </div>

      {/* Checkable List */}
      <div>
        <h3>
          Select Products ({selectedItems.length} selected)
          {searchLoading && (
            <span
              style={{ marginLeft: "1rem", fontSize: "0.9rem", color: "#666" }}
            >
              Loading...
            </span>
          )}
        </h3>
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
