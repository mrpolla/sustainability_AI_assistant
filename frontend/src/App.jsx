import React, { useState, useEffect, useCallback } from "react";
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
  checkApiHealth,
} from "./services/api";

// Constants
const LLM_OPTIONS = [
  "Llama-3.2-1B-Instruct",
  "Mistral-7B-Instruct-v0.2",
  "Llama-3.2-3B",
];

const DEFAULT_LLM = "Llama-3.2-1B-Instruct";

function App() {
  // State for products
  const [allProducts, setAllProducts] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [productLoadingError, setProductLoadingError] = useState("");
  const [productLoading, setProductLoading] = useState(false);

  // State for indicators
  const [allIndicators, setAllIndicators] = useState([]);
  const [selectedIndicators, setSelectedIndicators] = useState([]);
  const [indicatorLoadingError, setIndicatorLoadingError] = useState("");
  const [indicatorLoading, setIndicatorLoading] = useState(false);

  // State for questions and answers
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [questionError, setQuestionError] = useState("");

  // State for LLM selection
  const [selectedLLM, setSelectedLLM] = useState(DEFAULT_LLM);

  // State for comparison
  const [showComparison, setShowComparison] = useState(false);
  const [comparisonData, setComparisonData] = useState(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState("");

  // State for connection
  const [connectionStatus, setConnectionStatus] = useState("unknown");
  const [aiServiceStatus, setAiServiceStatus] = useState("unknown");

  // Initial data loading function
  const loadInitialData = useCallback(async () => {
    try {
      setConnectionStatus("checking");

      // Load products
      setProductLoading(true);
      setProductLoadingError("");

      try {
        const productsData = await fetchAllProductNames();

        if (!productsData) {
          throw new Error("No data returned from product name request");
        }

        if (productsData.products && Array.isArray(productsData.products)) {
          setAllProducts(productsData.products);
        } else {
          setAllProducts([]);
        }
      } catch (error) {
        console.error("Failed to load product names:", error);
        setProductLoadingError(
          `Failed to load products: ${error.message || "Unknown error"}`
        );
        setAllProducts([]);
      } finally {
        setProductLoading(false);
      }

      // Load indicators
      setIndicatorLoading(true);
      setIndicatorLoadingError("");

      try {
        const indicatorsData = await fetchAllIndicators();

        if (!indicatorsData) {
          throw new Error("No data returned from indicators request");
        }

        if (
          indicatorsData.indicators &&
          Array.isArray(indicatorsData.indicators)
        ) {
          setAllIndicators(indicatorsData.indicators);
        } else {
          setAllIndicators([]);
        }
      } catch (error) {
        console.error("Failed to load indicators:", error);
        setIndicatorLoadingError(
          `Failed to load indicators: ${error.message || "Unknown error"}`
        );
        setAllIndicators([]);
      } finally {
        setIndicatorLoading(false);
      }

      // If we got here, connection worked
      setConnectionStatus("connected");
    } catch (error) {
      console.error("Initial data loading failed:", error);
      setConnectionStatus("disconnected");
      setAllProducts([]);
      setAllIndicators([]);
    }
  }, []);

  // Set up initial data loading
  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Handle retry connection button click
  const handleRetryConnection = useCallback(() => {
    setConnectionStatus("checking");
    setAiServiceStatus("unknown");

    // Try to load products
    const loadProducts = async () => {
      try {
        setProductLoading(true);
        setProductLoadingError("");

        const data = await fetchAllProductNames();
        if (data && Array.isArray(data.products)) {
          setAllProducts(data.products);
          setConnectionStatus("connected");

          // Check AI service
          try {
            await askQuestion("ping", [], [], DEFAULT_LLM);
            setAiServiceStatus("available");
          } catch (error) {
            if (error.isServiceUnavailable || error.status === 503) {
              setAiServiceStatus("unavailable");
            } else {
              setAiServiceStatus("unknown");
            }
          }
        } else {
          setAllProducts([]);
          throw new Error("Invalid product data format");
        }
      } catch (error) {
        console.error("Product reload failed:", error);
        setProductLoadingError(
          "Failed to load products. Please try again later."
        );
        setConnectionStatus("disconnected");
        setAiServiceStatus("unknown");
      } finally {
        setProductLoading(false);
      }
    };

    loadProducts();
  }, []);

  // Handle products loaded callback
  const handleProductsLoaded = useCallback((products) => {
    if (Array.isArray(products)) {
      setAllProducts(products);
      setProductLoadingError("");
      setConnectionStatus("connected");
    } else {
      console.error("Invalid products data format:", products);
      setProductLoadingError("Received invalid product data");
    }
  }, []);

  // Handle search functionality
  const handleSearch = useCallback(async (searchTerm) => {
    const trimmedSearchTerm = searchTerm?.trim() || "";

    if (!trimmedSearchTerm) {
      setSearchResults([]);
      setSearchError("");
      return;
    }

    setSearchLoading(true);
    setSearchError("");

    try {
      const data = await searchProducts(trimmedSearchTerm);

      if (!data) {
        throw new Error("No data returned from search request");
      }

      if (data.items && Array.isArray(data.items)) {
        setSearchResults(data.items);

        if (data.items.length === 0) {
          setSearchError(`No products found matching "${trimmedSearchTerm}"`);
        }
      } else {
        setSearchResults([]);
        setSearchError("Received invalid data format from server");
      }
    } catch (error) {
      console.error("Search failed:", error);
      setSearchError(error.message || "Unknown error");
      setSearchResults([]);

      if (
        error.message?.includes("connect to the server") ||
        error.message?.includes("timed out")
      ) {
        setConnectionStatus("disconnected");
      }
    } finally {
      setSearchLoading(false);
    }
  }, []);

  // Handle indicator selection
  const handleSelectIndicator = useCallback((indicator) => {
    if (!indicator) return;

    setSelectedIndicators((prev) => {
      const isAlreadySelected = prev.some((item) => item.id === indicator.id);
      if (isAlreadySelected) return prev;
      return [...prev, indicator];
    });
  }, []);

  // Handle indicator removal
  const handleRemoveIndicator = useCallback((indicatorToRemove) => {
    if (!indicatorToRemove) return;

    setSelectedIndicators((prev) =>
      prev.filter((indicator) => indicator.id !== indicatorToRemove.id)
    );
  }, []);

  // Handle item selection in the checkable list
  const handleItemToggle = useCallback((itemId) => {
    if (itemId === undefined || itemId === null) return;

    setSelectedItems((prev) =>
      prev.includes(itemId)
        ? prev.filter((id) => id !== itemId)
        : [...prev, itemId]
    );
  }, []);

  // Handle compare button click
  const handleCompare = useCallback(async () => {
    if (!selectedItems.length) {
      setComparisonError("Please select at least one product to compare");
      return;
    }

    if (!selectedIndicators.length) {
      setComparisonError("Please select at least one indicator to compare");
      return;
    }

    setComparisonLoading(true);
    setComparisonError("");
    setShowComparison(true);

    try {
      const data = await compareProducts(selectedItems, selectedIndicators);

      if (!data) {
        throw new Error("No data returned from comparison request");
      }

      setComparisonData(data);
    } catch (error) {
      console.error("Comparison failed:", error);
      setComparisonData(null);
      setComparisonError(
        `Comparison failed: ${error.message || "Unknown error"}`
      );

      if (
        error.message?.includes("connect to the server") ||
        error.message?.includes("timed out")
      ) {
        setConnectionStatus("disconnected");
      }
    } finally {
      setComparisonLoading(false);
    }
  }, [selectedItems, selectedIndicators]);

  // Handle question submission
  const handleSubmit = useCallback(async () => {
    if (!question?.trim()) {
      setQuestionError("Please enter a question");
      return;
    }

    setLoading(true);
    setAnswer("");
    setQuestionError("");

    try {
      const indicatorKeys = selectedIndicators
        .map((indicator) => indicator?.name)
        .filter(Boolean);

      const data = await askQuestion(
        question,
        selectedItems,
        indicatorKeys,
        selectedLLM
      );

      if (!data) {
        throw new Error("No data returned from question request");
      }

      if (data.answer) {
        setAnswer(data.answer);
      } else {
        setAnswer("No answer returned from the server.");
      }
    } catch (error) {
      console.error("Question submission failed:", error);

      if (error.isServiceUnavailable || error.status === 503) {
        setAiServiceStatus("unavailable");
        setQuestionError("The AI service is currently unavailable");
        setAnswer(
          "The AI service is temporarily unavailable. This is not related to your question or selections. " +
            "Please try again later."
        );
      } else {
        setQuestionError(error.message || "Unknown error");
        setAnswer("Failed to get an answer. Please try again later.");

        if (
          error.message?.includes("connect to the server") ||
          error.message?.includes("timed out")
        ) {
          setConnectionStatus("disconnected");
        }
      }
    } finally {
      setLoading(false);
    }
  }, [question, selectedItems, selectedIndicators, selectedLLM]);

  // Handle closing comparison view
  const handleCloseComparison = useCallback(() => {
    setShowComparison(false);
  }, []);

  // Handle LLM selection change
  const handleLLMChange = useCallback((e) => {
    const newValue = e.target.value;
    if (LLM_OPTIONS.includes(newValue)) {
      setSelectedLLM(newValue);
    } else {
      setSelectedLLM(DEFAULT_LLM);
    }
  }, []);

  // AI service unavailable banner component
  const ServiceUnavailableBanner = () => (
    <div
      style={{
        backgroundColor: "#433d5f",
        color: "#e0c3fc",
        padding: "0.8rem",
        borderRadius: "4px",
        marginBottom: "1.5rem",
        border: "1px solid #7b61c4",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <div>
        <strong>AI Service Status:</strong> The AI model service is currently
        unavailable. Your other actions will still work, but you won't be able
        to ask questions until the service is back online.
      </div>
      <button
        onClick={handleRetryConnection}
        style={{
          backgroundColor: "#7b61c4",
          color: "white",
          border: "none",
          padding: "0.4rem 0.8rem",
          borderRadius: "4px",
          cursor: "pointer",
          marginLeft: "1rem",
        }}
      >
        Check Status
      </button>
    </div>
  );

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

      {/* Connection Status Banner */}
      {connectionStatus === "checking" && (
        <div
          style={{
            backgroundColor: "#263238",
            color: "#90caf9",
            padding: "0.8rem",
            borderRadius: "4px",
            marginBottom: "1.5rem",
            border: "1px solid #37474f",
            display: "flex",
            alignItems: "center",
          }}
        >
          <div>Checking connection to server...</div>
        </div>
      )}

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
            onClick={handleRetryConnection}
            style={{
              backgroundColor: "#d32f2f",
              color: "white",
              border: "none",
              padding: "0.4rem 0.8rem",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* AI Service Status Banner */}
      {aiServiceStatus === "unavailable" &&
        connectionStatus !== "disconnected" && <ServiceUnavailableBanner />}

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
              disabled={connectionStatus === "disconnected"}
            />
            {productLoading && (
              <div style={{ marginTop: "0.5rem", color: "#90caf9" }}>
                Loading product list...
              </div>
            )}
            {productLoadingError && (
              <div
                style={{
                  color: "#d32f2f",
                  fontSize: "0.85rem",
                  marginTop: "0.3rem",
                  padding: "0.3rem",
                  backgroundColor: "rgba(211, 47, 47, 0.1)",
                  borderRadius: "4px",
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
              disabled={connectionStatus === "disconnected"}
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
            {indicatorLoading && (
              <div style={{ marginBottom: "0.5rem", color: "#90caf9" }}>
                Loading indicators...
              </div>
            )}
            {indicatorLoadingError && (
              <div
                style={{
                  color: "#d32f2f",
                  fontSize: "0.85rem",
                  marginBottom: "0.5rem",
                  padding: "0.3rem",
                  backgroundColor: "rgba(211, 47, 47, 0.1)",
                  borderRadius: "4px",
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
              disabled={connectionStatus === "disconnected"}
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
                connectionStatus === "disconnected" ||
                selectedItems.length === 0 ||
                selectedIndicators.length === 0
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
                disabled={
                  connectionStatus === "disconnected" ||
                  aiServiceStatus === "unavailable"
                }
                style={{
                  width: "100%",
                  padding: "0.5rem",
                  backgroundColor: "#333",
                  color: "#e0e0e0",
                  border: "1px solid #555",
                  borderRadius: "4px",
                  opacity:
                    connectionStatus === "disconnected" ||
                    aiServiceStatus === "unavailable"
                      ? 0.6
                      : 1,
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
              error={questionError}
              disabled={
                connectionStatus === "disconnected" ||
                aiServiceStatus === "unavailable"
              }
            />
          </div>

          <ResponseDisplay answer={answer} loading={loading} />
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
                onClick={handleCloseComparison}
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
