import React, { useState, useEffect } from "react";
import Header from "./components/Header";
import AutoSuggestSearchBox from "./components/AutoSuggestSearchBox";
import CheckableList from "./components/CheckableList";
import QuestionForm from "./components/QuestionForm";
import ResponseDisplay from "./components/ResponseDisplay";
import {
  askQuestion,
  searchProducts,
  fetchAllProductNames,
} from "./services/api";

function App() {
  // State variables
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [questionError, setQuestionError] = useState("");
  const [connectionStatus, setConnectionStatus] = useState("unknown");
  const [allProducts, setAllProducts] = useState([]);
  const [productLoadingError, setProductLoadingError] = useState("");

  // Load all product names on component mount for autocomplete - with fault tolerance
  useEffect(() => {
    const loadAllProducts = async () => {
      try {
        const data = await fetchAllProductNames();
        if (data && Array.isArray(data.products)) {
          setAllProducts(data.products);
          setConnectionStatus("connected");
        }
      } catch (error) {
        console.error("Failed to load product names:", error);
        // Don't set an error message here - just silently fail
        // We'll retry when the user focuses on the search box
      }
    };

    // Try to load, but don't display errors if it fails on initial load
    loadAllProducts().catch(() => {
      // Silently fail on initial load
      console.log(
        "Initial product names loading failed, will retry on search focus"
      );
    });
  }, []);

  const handleProductsLoaded = (products) => {
    setAllProducts(products);
    setProductLoadingError("");
  };

  /**
   * Handle search functionality with error handling
   */
  const handleSearch = async (searchTerm) => {
    // Clear previous search results if search term is empty
    if (!searchTerm.trim()) {
      setSearchResults([]);
      setSearchError("");
      return;
    }

    setSearchLoading(true);
    setSearchError("");

    try {
      const data = await searchProducts(searchTerm);

      // Check if items exist and is an array
      if (Array.isArray(data.items)) {
        setSearchResults(data.items);

        // Show message if no results found
        if (data.items.length === 0) {
          setSearchError(`No products found matching "${searchTerm}"`);
        }
      } else {
        // Handle unexpected response format
        console.error("Unexpected response format:", data);
        setSearchResults([]);
        setSearchError("Received invalid data format from server");
      }
    } catch (error) {
      console.error("Search failed:", error);
      setSearchError(`${error.message || "Unknown error"}`);
      setSearchResults([]);

      // Update connection status if it appears to be a connection issue
      if (
        error.message.includes("connect to the server") ||
        error.message.includes("timed out")
      ) {
        setConnectionStatus("disconnected");
      }
    } finally {
      setSearchLoading(false);
    }
  };

  /**
   * Handle item selection in the checkable list
   */
  const handleItemToggle = (itemId) => {
    setSelectedItems((prev) =>
      prev.includes(itemId)
        ? prev.filter((id) => id !== itemId)
        : [...prev, itemId]
    );
  };

  /**
   * Handle question submission with error handling
   */
  const handleSubmit = async () => {
    // Validate input
    if (!question.trim()) {
      setQuestionError("Please enter a question");
      return;
    }

    setLoading(true);
    setAnswer("");
    setQuestionError("");

    try {
      const data = await askQuestion(question, selectedItems);

      // Handle response
      if (data && typeof data.answer === "string") {
        setAnswer(data.answer);
      } else {
        setAnswer("Received an invalid response from the server");
        console.error("Invalid answer format:", data);
      }
    } catch (error) {
      console.error("Question submission failed:", error);
      setQuestionError(`${error.message || "Unknown error"}`);
      setAnswer("Failed to get an answer. Please try again later.");

      // Update connection status if it appears to be a connection issue
      if (
        error.message.includes("connect to the server") ||
        error.message.includes("timed out")
      ) {
        setConnectionStatus("disconnected");
      }
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
        height: "100vh",
        backgroundColor: "#121212",
      }}
    >
      <Header />

      {/* Connection Status Banner - only show when disconnected */}
      {connectionStatus === "disconnected" && (
        <div
          style={{
            backgroundColor: "#fff0f0",
            color: "#d32f2f",
            padding: "0.8rem",
            borderRadius: "4px",
            marginBottom: "1.5rem",
            border: "1px solid #ffcdd2",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <strong>Cannot connect to server.</strong> The application might not
            function correctly.
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{
              backgroundColor: "#d32f2f",
              color: "white",
              border: "none",
              padding: "0.4rem 0.8rem",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Search Box */}
      <div style={{ marginTop: "1.5rem", marginBottom: "1rem" }}>
        <h3>Search Products</h3>
        <AutoSuggestSearchBox
          onSearch={handleSearch}
          productList={allProducts}
          onProductsLoaded={handleProductsLoaded}
        />
        {productLoadingError && (
          <div
            style={{
              color: "#d32f2f",
              fontSize: "0.85rem",
              marginTop: "0.3rem",
            }}
          >
            {productLoadingError}
          </div>
        )}
        {searchError && (
          <div
            style={{
              color: "#d32f2f",
              marginTop: "0.5rem",
              padding: "0.5rem",
              border: "1px solid #ffcdd2",
              borderRadius: "4px",
              backgroundColor: "#fff0f0",
            }}
          >
            {searchError}
          </div>
        )}
      </div>

      {/* Checkable List */}
      <div>
        <h3>
          Select Products ({searchResults.length} results found)
          {searchLoading && (
            <span
              style={{
                marginLeft: "1rem",
                fontSize: "0.9rem",
                color: "#666",
              }}
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
        {selectedItems.length > 0 && (
          <div
            style={{
              fontSize: "0.9rem",
              color: "#999",
              marginTop: "-1rem",
              marginBottom: "1rem",
            }}
          >
            {selectedItems.length} product
            {selectedItems.length !== 1 ? "s" : ""} selected
          </div>
        )}
      </div>

      {/* Question Form */}
      <div style={{ marginTop: "1.5rem" }}>
        <h3>Ask a Question</h3>
        <QuestionForm
          question={question}
          setQuestion={setQuestion}
          handleSubmit={handleSubmit}
          loading={loading}
          error={questionError}
        />
      </div>

      <ResponseDisplay answer={answer} />
    </div>
  );
}

export default App;
