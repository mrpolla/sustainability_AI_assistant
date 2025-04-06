import React, { useState, useEffect } from "react";
import Header from "./components/Header";
import AutoSuggestSearchBox from "./components/AutoSuggestSearchBox";
import CheckableList from "./components/CheckableList";
import QuestionForm from "./components/QuestionForm";
import ResponseDisplay from "./components/ResponseDisplay";
import IndicatorSelection from "./components/IndicatorSelection";
import CompareButton from "./components/CompareButton/CompareButton";
import ComparisonView from "./components/ComparisonView/ComparisonView";
import {
  askQuestion,
  searchProducts,
  fetchAllProductNames,
  fetchAllIndicators,
  compareProducts,
} from "./services/api";

function App() {
  // State for products
  const [allProducts, setAllProducts] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [productLoadingError, setProductLoadingError] = useState("");

  // State for indicators
  const [allIndicators, setAllIndicators] = useState([]);
  const [selectedIndicators, setSelectedIndicators] = useState([]);
  const [indicatorLoadingError, setIndicatorLoadingError] = useState("");

  // State for questions and answers
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [questionError, setQuestionError] = useState("");

  // State for comparison
  const [showComparison, setShowComparison] = useState(false);
  const [comparisonData, setComparisonData] = useState(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState("");

  // Connection status
  const [connectionStatus, setConnectionStatus] = useState("unknown");

  // Load all product names on component mount
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
        // Silently fail on initial load
      }
    };

    loadAllProducts().catch(() => {
      console.log(
        "Initial product names loading failed, will retry on search focus"
      );
    });
  }, []);

  // Load all indicators on component mount
  useEffect(() => {
    const loadAllIndicators = async () => {
      try {
        const data = await fetchAllIndicators();
        if (data && Array.isArray(data.indicators)) {
          setAllIndicators(data.indicators);
        }
      } catch (error) {
        console.error("Failed to load indicators:", error);
        setIndicatorLoadingError("Failed to load indicators");
      }
    };

    loadAllIndicators().catch(() => {
      console.log("Initial indicators loading failed");
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
        console.error("Unexpected response format:", data);
        setSearchResults([]);
        setSearchError("Received invalid data format from server");
      }
    } catch (error) {
      console.error("Search failed:", error);
      setSearchError(`${error.message || "Unknown error"}`);
      setSearchResults([]);

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
   * Handle indicator selection
   */
  const handleSelectIndicator = (indicator) => {
    setSelectedIndicators((prevIndicators) => [...prevIndicators, indicator]);
  };

  /**
   * Handle indicator removal
   */
  const handleRemoveIndicator = (indicatorToRemove) => {
    setSelectedIndicators((prevIndicators) =>
      prevIndicators.filter(
        (indicator) => indicator.id !== indicatorToRemove.id
      )
    );
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
   * Handle compare button click
   */
  const handleCompare = async () => {
    // Validate inputs
    if (selectedItems.length === 0) {
      setComparisonError("Please select at least one product to compare");
      return;
    }

    if (selectedIndicators.length === 0) {
      setComparisonError("Please select at least one indicator to compare");
      return;
    }

    setComparisonLoading(true);
    setComparisonError("");
    setShowComparison(true);

    try {
      const data = await compareProducts(selectedItems, selectedIndicators);
      setComparisonData(data);
    } catch (error) {
      console.error("Comparison failed:", error);
      setComparisonError(
        `Comparison failed: ${error.message || "Unknown error"}`
      );

      if (
        error.message.includes("connect to the server") ||
        error.message.includes("timed out")
      ) {
        setConnectionStatus("disconnected");
      }
    } finally {
      setComparisonLoading(false);
    }
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
      // Get the indicator keys from selected indicators
      const indicatorKeys = selectedIndicators.map(
        (indicator) => indicator.name
      );

      const data = await askQuestion(question, selectedItems, indicatorKeys);

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
        margin: "0 auto",
        minHeight: "100vh",
        backgroundColor: "#121212",
        maxWidth: showComparison ? "1400px" : "800px",
        transition: "max-width 0.3s ease-in-out",
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

      <div
        style={{
          display: "flex",
          flexDirection: showComparison ? "row" : "column",
          gap: showComparison ? "2rem" : "0",
        }}
      >
        {/* Left side - search, selection and question */}
        <div
          style={{
            width: showComparison ? "50%" : "100%",
            transition: "width 0.3s ease-in-out",
          }}
        >
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

          {/* Indicator Selection */}
          <div style={{ marginTop: "2rem", marginBottom: "1.5rem" }}>
            <h3>Select Indicators</h3>
            {indicatorLoadingError && (
              <div
                style={{
                  color: "#d32f2f",
                  fontSize: "0.85rem",
                  marginBottom: "0.5rem",
                }}
              >
                {indicatorLoadingError}
              </div>
            )}
            <IndicatorSelection
              indicatorList={allIndicators}
              selectedIndicators={selectedIndicators}
              onSelectIndicator={handleSelectIndicator}
              onRemoveIndicator={handleRemoveIndicator}
            />
            {selectedIndicators.length > 0 && (
              <div
                style={{
                  fontSize: "0.9rem",
                  color: "#999",
                  marginTop: "0.5rem",
                }}
              >
                {selectedIndicators.length} indicator
                {selectedIndicators.length !== 1 ? "s" : ""} selected
              </div>
            )}
          </div>

          {/* Compare Button */}
          <div
            style={{
              marginTop: "1.5rem",
              marginBottom: "1.5rem",
              display: "flex",
              justifyContent: "flex-start",
            }}
          >
            <CompareButton
              onClick={handleCompare}
              disabled={
                selectedItems.length === 0 || selectedIndicators.length === 0
              }
              loading={comparisonLoading}
            />
            {comparisonError && (
              <div
                style={{
                  color: "#d32f2f",
                  marginLeft: "1rem",
                  fontSize: "0.9rem",
                  display: "flex",
                  alignItems: "center",
                }}
              >
                {comparisonError}
              </div>
            )}
          </div>

          {/* Separator Line before Question Form */}
          <hr
            style={{
              border: "none",
              borderTop: "1px solid #333",
              margin: "2rem 0",
            }}
          />

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

        {/* Right side - comparison view */}
        {showComparison && (
          <div
            style={{
              width: "50%",
              borderLeft: "1px solid #333",
              paddingLeft: "2rem",
            }}
          >
            <ComparisonView
              comparisonData={comparisonData}
              loading={comparisonLoading}
              error={comparisonError}
            />

            {/* Button to hide comparison */}
            {!comparisonLoading && (
              <button
                onClick={() => setShowComparison(false)}
                style={{
                  marginTop: "1.5rem",
                  padding: "0.5rem 1rem",
                  backgroundColor: "#333",
                  color: "#e0e0e0",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "0.9rem",
                }}
              >
                Hide Comparison
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
