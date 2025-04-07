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
// Removed CONNECTION_CHECK_INTERVAL since we're not doing periodic checks

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

  // Check connection status - now only called manually, not in a loop
  const checkConnection = useCallback(async () => {
    try {
      const isHealthy = await checkApiHealth();
      setConnectionStatus(isHealthy ? "connected" : "disconnected");
    } catch (error) {
      console.error("Connection check failed:", error);
      setConnectionStatus("disconnected");
    }
  }, []);

  // Initial data loading function
  const loadInitialData = useCallback(async () => {
    try {
      setConnectionStatus("checking");

      // Add a maximum retry count to prevent infinite loops
      const maxAttempts = 1; // Only try once initially

      // Load products with proper loading state
      setProductLoading(true);
      setProductLoadingError("");

      try {
        const productsData = await fetchAllProductNames();

        // Validate product data structure
        if (!productsData) {
          throw new Error("No data returned from product name request");
        }

        if (typeof productsData !== "object") {
          throw new Error(
            `Expected product data to be an object, got ${typeof productsData}`
          );
        }

        if (!Array.isArray(productsData.products)) {
          console.warn("Unexpected products format:", productsData);
          // Try to recover if possible
          if (
            productsData.products === null ||
            productsData.products === undefined
          ) {
            setAllProducts([]);
          } else if (typeof productsData.products === "object") {
            // Try to convert to array if it's an object
            try {
              const productsArray = Object.values(productsData.products);
              setAllProducts(productsArray);
              console.log("Converted products object to array:", productsArray);
            } catch (conversionError) {
              setAllProducts([]);
              throw new Error(
                "Products data is not in expected format and couldn't be converted"
              );
            }
          } else {
            setAllProducts([]);
            throw new Error(
              `Products data is not an array (got ${typeof productsData.products})`
            );
          }
        } else {
          // Normal case - we have an array
          setAllProducts(productsData.products);
        }
      } catch (error) {
        console.error("Failed to load product names:", error);
        setProductLoadingError(
          `Failed to load products: ${error.message || "Unknown error"}`
        );
        setAllProducts([]); // Ensure we always have a valid array
      } finally {
        setProductLoading(false);
      }

      // Load indicators with proper loading state
      setIndicatorLoading(true);
      setIndicatorLoadingError("");

      try {
        const indicatorsData = await fetchAllIndicators();

        // Validate indicator data structure
        if (!indicatorsData) {
          throw new Error("No data returned from indicators request");
        }

        if (typeof indicatorsData !== "object") {
          throw new Error(
            `Expected indicators data to be an object, got ${typeof indicatorsData}`
          );
        }

        if (!Array.isArray(indicatorsData.indicators)) {
          console.warn("Unexpected indicators format:", indicatorsData);
          // Try to recover if possible
          if (
            indicatorsData.indicators === null ||
            indicatorsData.indicators === undefined
          ) {
            setAllIndicators([]);
          } else if (typeof indicatorsData.indicators === "object") {
            // Try to convert to array if it's an object
            try {
              const indicatorsArray = Object.values(indicatorsData.indicators);
              setAllIndicators(indicatorsArray);
              console.log(
                "Converted indicators object to array:",
                indicatorsArray
              );
            } catch (conversionError) {
              setAllIndicators([]);
              throw new Error(
                "Indicators data is not in expected format and couldn't be converted"
              );
            }
          } else {
            setAllIndicators([]);
            throw new Error(
              `Indicators data is not an array (got ${typeof indicatorsData.indicators})`
            );
          }
        } else {
          // Normal case - we have an array
          setAllIndicators(indicatorsData.indicators);
        }
      } catch (error) {
        console.error("Failed to load indicators:", error);
        setIndicatorLoadingError(
          `Failed to load indicators: ${error.message || "Unknown error"}`
        );
        setAllIndicators([]); // Ensure we always have a valid array
      } finally {
        setIndicatorLoading(false);
      }

      // If we got here, the connection worked for at least one request
      setConnectionStatus("connected");
    } catch (error) {
      console.error("Initial data loading failed:", error);
      setConnectionStatus("disconnected");

      // Always ensure we have valid arrays even if everything fails
      setAllProducts([]);
      setAllIndicators([]);
    }
  }, []);

  // Set up periodic connection checking
  useEffect(() => {
    // Initial connection check and data loading - only once
    loadInitialData();

    // We won't set up periodic checks that could cause loops
    // This prevents infinite retry loops when the server is down
  }, [loadInitialData]);

  // Handle retry connection button click
  const handleRetryConnection = useCallback(() => {
    // Don't increment retry count - we don't need it since we're not in a loop
    // Don't automatically reload on mount multiple times

    // Only try to load products - that's the main need
    const loadProducts = async () => {
      try {
        setProductLoading(true);
        setProductLoadingError("");
        setConnectionStatus("checking");

        const data = await fetchAllProductNames();
        if (data && Array.isArray(data.products)) {
          setAllProducts(data.products);
          setConnectionStatus("connected");
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
      } finally {
        setProductLoading(false);
      }
    };

    loadProducts();
  }, []);

  // Handle products loaded callback - this is called by AutoSuggestSearchBox when it loads products
  const handleProductsLoaded = useCallback((products) => {
    if (Array.isArray(products)) {
      setAllProducts(products);
      setProductLoadingError("");

      // If we successfully loaded products, we're definitely connected
      setConnectionStatus("connected");
    } else {
      console.error("Invalid products data format:", products);

      // Don't update the products list if the format is invalid
      // Just show an error but keep the existing products (if any)
      setProductLoadingError("Received invalid product data");
    }
  }, []);

  /**
   * Handle search functionality with error handling
   */
  const handleSearch = useCallback(async (searchTerm) => {
    // Validate input
    const trimmedSearchTerm = searchTerm?.trim() || "";

    // Clear previous search results if search term is empty
    if (!trimmedSearchTerm) {
      setSearchResults([]);
      setSearchError("");
      return;
    }

    setSearchLoading(true);
    setSearchError("");

    try {
      const data = await searchProducts(trimmedSearchTerm);

      // Validate the data structure
      if (!data) {
        throw new Error("No data returned from search request");
      }

      if (typeof data !== "object") {
        throw new Error(
          `Expected search data to be an object, got ${typeof data}`
        );
      }

      // Check if items exist and is an array
      if (!("items" in data)) {
        console.warn("Search response missing 'items' property:", data);

        // Try to recover by finding any array property
        const arrayProps = Object.entries(data).find(([_, value]) =>
          Array.isArray(value)
        );
        if (arrayProps) {
          console.log(`Using '${arrayProps[0]}' property as items array`);
          setSearchResults(arrayProps[1]);

          if (arrayProps[1].length === 0) {
            setSearchError(`No products found matching "${trimmedSearchTerm}"`);
          }
          return;
        }

        // If we can't find any array, create an empty array
        setSearchResults([]);
        setSearchError(`No results found (unexpected response format)`);
        return;
      }

      if (!Array.isArray(data.items)) {
        console.error("Search 'items' is not an array:", data.items);

        // Try to recover if possible
        if (data.items === null || data.items === undefined) {
          setSearchResults([]);
          setSearchError(`No products found matching "${trimmedSearchTerm}"`);
        } else if (typeof data.items === "object") {
          // Try to convert to array if it's an object
          try {
            const itemsArray = Object.values(data.items);
            setSearchResults(itemsArray);
            console.log("Converted items object to array:", itemsArray);

            if (itemsArray.length === 0) {
              setSearchError(
                `No products found matching "${trimmedSearchTerm}"`
              );
            }
          } catch (conversionError) {
            setSearchResults([]);
            setSearchError("Search results are not in expected format");
          }
        } else {
          setSearchResults([]);
          setSearchError("Received invalid data format from server");
        }
      } else {
        // Normal case - we have an array
        setSearchResults(data.items);

        // Show message if no results found
        if (data.items.length === 0) {
          setSearchError(`No products found matching "${trimmedSearchTerm}"`);
        }
      }
    } catch (error) {
      console.error("Search failed:", error);
      setSearchError(`${error.message || "Unknown error"}`);
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

  /**
   * Handle indicator selection
   */
  const handleSelectIndicator = useCallback((indicator) => {
    if (!indicator) return;

    setSelectedIndicators((prevIndicators) => {
      // Check if indicator is already selected
      const isAlreadySelected = prevIndicators.some(
        (item) => item.id === indicator.id
      );

      if (isAlreadySelected) return prevIndicators;
      return [...prevIndicators, indicator];
    });
  }, []);

  /**
   * Handle indicator removal
   */
  const handleRemoveIndicator = useCallback((indicatorToRemove) => {
    if (!indicatorToRemove) return;

    setSelectedIndicators((prevIndicators) =>
      prevIndicators.filter(
        (indicator) => indicator.id !== indicatorToRemove.id
      )
    );
  }, []);

  /**
   * Handle item selection in the checkable list
   */
  const handleItemToggle = useCallback((itemId) => {
    if (itemId === undefined || itemId === null) return;

    setSelectedItems((prev) =>
      prev.includes(itemId)
        ? prev.filter((id) => id !== itemId)
        : [...prev, itemId]
    );
  }, []);

  /**
   * Handle compare button click
   */
  const handleCompare = useCallback(async () => {
    // Validate inputs
    if (!Array.isArray(selectedItems) || selectedItems.length === 0) {
      setComparisonError("Please select at least one product to compare");
      return;
    }

    if (!Array.isArray(selectedIndicators) || selectedIndicators.length === 0) {
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

      // Validate required data structure for comparison view
      // This depends on what ComparisonView component expects
      const requiredProperties = ["products", "indicators"];
      const missingProperties = requiredProperties.filter(
        (prop) => !(prop in data)
      );

      if (missingProperties.length > 0) {
        console.warn(
          `Comparison data missing required properties: ${missingProperties.join(
            ", "
          )}`,
          data
        );

        // Try to construct a valid data structure
        const fixedData = { ...data };

        if (!("products" in data) || !Array.isArray(data.products)) {
          // Try to find product data in other properties
          if ("items" in data && Array.isArray(data.items)) {
            fixedData.products = data.items;
            console.log("Using 'items' as products array");
          } else {
            // Create empty products array as fallback
            fixedData.products = [];
            console.warn("Could not find products data, using empty array");
          }
        }

        if (!("indicators" in data) || !Array.isArray(data.indicators)) {
          // Use the selected indicators as fallback
          fixedData.indicators = selectedIndicators.map((ind) => ({
            ...ind,
            id: ind.id || ind.name,
            description: ind.description || `Values for ${ind.name}`,
          }));
          console.log(
            "Using selected indicators as fallback:",
            fixedData.indicators
          );
        }

        console.log("Fixed comparison data structure:", fixedData);
        setComparisonData(fixedData);
      } else {
        // Normal case - data has required properties
        // Validate that products and indicators are arrays
        let dataValid = true;
        let fixedData = { ...data };

        if (!Array.isArray(data.products)) {
          console.warn("Comparison 'products' is not an array:", data.products);
          dataValid = false;

          // Try to convert products to array if possible
          if (typeof data.products === "object" && data.products !== null) {
            try {
              fixedData.products = Object.values(data.products);
              console.log(
                "Converted products object to array:",
                fixedData.products
              );
            } catch (conversionError) {
              fixedData.products = [];
            }
          } else {
            fixedData.products = [];
          }
        }

        if (!Array.isArray(data.indicators)) {
          console.warn(
            "Comparison 'indicators' is not an array:",
            data.indicators
          );
          dataValid = false;

          // Try to convert indicators to array if possible
          if (typeof data.indicators === "object" && data.indicators !== null) {
            try {
              fixedData.indicators = Object.values(data.indicators);
              console.log(
                "Converted indicators object to array:",
                fixedData.indicators
              );
            } catch (conversionError) {
              fixedData.indicators = selectedIndicators;
            }
          } else {
            fixedData.indicators = selectedIndicators;
          }
        }

        if (dataValid) {
          setComparisonData(data);
        } else {
          console.log("Using fixed comparison data:", fixedData);
          setComparisonData(fixedData);
        }
      }
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

  /**
   * Handle question submission with error handling
   */
  const handleSubmit = useCallback(async () => {
    // Validate input
    if (!question?.trim()) {
      setQuestionError("Please enter a question");
      return;
    }

    // Validate LLM selection
    if (!selectedLLM) {
      setSelectedLLM(DEFAULT_LLM);
    }

    setLoading(true);
    setAnswer("");
    setQuestionError("");

    try {
      // Get the indicator keys from selected indicators
      const indicatorKeys = Array.isArray(selectedIndicators)
        ? selectedIndicators.map((indicator) => indicator?.name).filter(Boolean)
        : [];

      console.log("Submitting question with:", {
        question,
        selectedItems,
        indicatorKeys,
        selectedLLM,
      });

      const data = await askQuestion(
        question,
        selectedItems,
        indicatorKeys,
        selectedLLM
      );

      // Validate response data
      if (!data) {
        throw new Error("No data returned from question request");
      }

      if (typeof data !== "object") {
        throw new Error(
          `Expected answer data to be an object, got ${typeof data}`
        );
      }

      // Check for answer property
      if (!("answer" in data)) {
        console.warn("Response missing 'answer' property:", data);

        // Try to find any string property to use as answer
        const stringProps = Object.entries(data).find(
          ([_, value]) => typeof value === "string" && value.length > 0
        );
        if (stringProps) {
          console.log(`Using '${stringProps[0]}' property as answer`);
          setAnswer(stringProps[1]);
          return;
        }

        // If we find a nested object with an answer property, use that
        for (const [key, value] of Object.entries(data)) {
          if (
            typeof value === "object" &&
            value !== null &&
            "answer" in value &&
            typeof value.answer === "string"
          ) {
            console.log(`Found answer in nested object '${key}'`);
            setAnswer(value.answer);
            return;
          }
        }

        // If we can't find a suitable string, use a generic message
        setAnswer("Received a response without an answer. Please try again.");
        return;
      }

      // Validate answer type
      if (typeof data.answer === "string") {
        setAnswer(data.answer);
      } else if (data.answer === null || data.answer === undefined) {
        setAnswer("No answer returned from the server. Please try again.");
      } else if (typeof data.answer === "object") {
        // Try to convert object to string
        try {
          const answerString = JSON.stringify(data.answer);
          console.warn("Answer is an object, stringifying:", answerString);
          setAnswer(`Response: ${answerString}`);
        } catch (stringifyError) {
          setAnswer(
            "Received a complex answer that couldn't be displayed. Please try again."
          );
        }
      } else {
        // Convert any other type to string
        try {
          setAnswer(String(data.answer));
          console.warn(
            `Answer is type ${typeof data.answer}, converted to string:`,
            String(data.answer)
          );
        } catch (conversionError) {
          setAnswer("Received an invalid response from the server");
          console.error("Invalid answer format:", data);
        }
      }
    } catch (error) {
      console.error("Question submission failed:", error);

      // Provide more user-friendly error messages for common issues
      if (
        error.message.includes("validation error") ||
        error.message.includes("Invalid request")
      ) {
        setQuestionError(
          "There was a problem with your request format. Please try again with different parameters."
        );
      } else if (error.message.includes("Bad request")) {
        setQuestionError(
          "The server couldn't process your question. Try rephrasing or selecting different indicators."
        );
      } else if (
        error.message.includes("temporarily unavailable") ||
        error.message.includes("overloaded") ||
        error.message.includes("503")
      ) {
        // User-friendly message for 503 Service Unavailable errors
        setQuestionError(
          "The AI service is currently unavailable or overloaded. Please try again in a few minutes."
        );
        // Set a nicer message in the answer area too
        setAnswer(
          "Sorry, the AI model is temporarily unavailable. This could be due to high server load or maintenance. Your question was valid, but we couldn't get an answer right now. Please try again later."
        );
      } else if (error.message.includes("Inference error")) {
        // Handle AI model inference errors gracefully
        setQuestionError(
          "The AI model encountered a processing error. This might be due to the complexity of your question."
        );
        setAnswer(
          "Sorry, the AI model had trouble processing your question. You could try simplifying your question or selecting fewer indicators."
        );
      } else {
        setQuestionError(`${error.message || "Unknown error"}`);
      }

      if (
        !error.message.includes("temporarily unavailable") &&
        !error.message.includes("Inference error")
      ) {
        setAnswer("Failed to get an answer. Please try again later.");
      }

      if (
        error.message?.includes("connect to the server") ||
        error.message?.includes("timed out") ||
        error.message?.includes("503") ||
        error.message?.includes("temporarily unavailable")
      ) {
        setConnectionStatus("disconnected");
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
      console.warn("Invalid LLM selection:", newValue);
      setSelectedLLM(DEFAULT_LLM);
    }
  }, []);

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
            {/* Load products on demand when search is focused, not automatically */}
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
              Select Products ({searchResults?.length || 0} results found)
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
              items={searchResults || []}
              selectedItems={selectedItems || []}
              onItemToggle={handleItemToggle}
              disabled={connectionStatus === "disconnected"}
            />
            {selectedItems?.length > 0 && (
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
              indicatorList={allIndicators || []}
              selectedIndicators={selectedIndicators || []}
              onSelectIndicator={handleSelectIndicator}
              onRemoveIndicator={handleRemoveIndicator}
              disabled={connectionStatus === "disconnected"}
            />
            {selectedIndicators?.length > 0 && (
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
                (selectedItems?.length || 0) === 0 ||
                (selectedIndicators?.length || 0) === 0
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
                disabled={connectionStatus === "disconnected"}
                style={{
                  width: "100%",
                  padding: "0.5rem",
                  backgroundColor: "#333",
                  color: "#e0e0e0",
                  border: "1px solid #555",
                  borderRadius: "4px",
                  opacity: connectionStatus === "disconnected" ? 0.6 : 1,
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
              disabled={connectionStatus === "disconnected"}
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
