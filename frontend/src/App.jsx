import React, { useEffect, useState } from "react";
import Header from "./components/Header";
import ComparisonView from "./components/ComparisonView/ComparisonView";

// Feature Components
import ConnectionBanner from "./features/connection/ConnectionBanner";
import AIServiceBanner from "./features/connection/AIServiceBanner";
import ProductSearch from "./features/product/ProductSearch";
import ProductSelection from "./features/product/ProductSelection";
import IndicatorPanel from "./features/indicator/IndicatorPanel";
import ComparisonPanel from "./features/comparison/ComparisonPanel";
import QuestionPanel from "./features/question/QuestionPanel";
import AnalysisPanel from "./features/analysis/AnalysisPanel";

// Custom Hooks
import {
  useConnection,
  useProducts,
  useIndicators,
  useComparison,
  useQuestionAnswer,
  useAIAnalysis,
} from "./hooks";

// Constants
const DEFAULT_LLM = "mistral";

function App() {
  // Initialize all hooks
  const [selectedLLM, setSelectedLLM] = useState(DEFAULT_LLM);
  const {
    connectionStatus,
    setConnectionStatus,
    aiServiceStatus,
    setAiServiceStatus,
    handleRetryConnection,
  } = useConnection(DEFAULT_LLM);

  const {
    allProducts,
    searchResults,
    selectedItems,
    searchLoading,
    searchError,
    productLoadingError,
    productLoading,
    loadProducts,
    handleProductsLoaded,
    handleSearch,
    handleItemToggle,
  } = useProducts(setConnectionStatus);

  const {
    allIndicators,
    selectedIndicators,
    indicatorLoadingError,
    indicatorLoading,
    loadIndicators,
    handleSelectIndicator,
    handleRemoveIndicator,
  } = useIndicators();

  const {
    showComparison,
    comparisonData,
    comparisonLoading,
    comparisonError,
    handleCompare,
    handleCloseComparison,
  } = useComparison(selectedItems, selectedIndicators, setConnectionStatus);

  const {
    question,
    setQuestion,
    answer,
    loading,
    questionError,
    handleSubmit,
    handleLLMChange,
  } = useQuestionAnswer(
    selectedItems,
    selectedIndicators,
    setConnectionStatus,
    setAiServiceStatus,
    selectedLLM
  );

  const { aiAnalysis, handleAnalyseWithAI, resetAnalysis } = useAIAnalysis(
    comparisonData,
    setConnectionStatus,
    setAiServiceStatus,
    selectedLLM
  );

  // Set up initial data loading
  useEffect(() => {
    const loadInitialData = async () => {
      setConnectionStatus("checking");
      await loadProducts();
      await loadIndicators();
      setConnectionStatus("connected");
    };

    loadInitialData();
  }, [loadProducts, loadIndicators, setConnectionStatus]);

  return (
    <div
      style={{
        padding: "2rem",
        fontFamily: "sans-serif",
        margin: "0 auto",
        minHeight: "100vh",
        backgroundColor: "#121212",
        width: showComparison ? "90%" : "50%",
        maxWidth: "90%",
        transition: "all 0.3s ease-in-out",
      }}
    >
      <Header />

      {/* Connection Status Banner */}
      <ConnectionBanner
        connectionStatus={connectionStatus}
        handleRetryConnection={handleRetryConnection}
      />

      {/* AI Service Status Banner */}
      {aiServiceStatus === "unavailable" &&
        connectionStatus !== "disconnected" && (
          <AIServiceBanner
            aiServiceStatus={aiServiceStatus}
            handleRetryConnection={handleRetryConnection}
          />
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
          {/* Product Search */}
          <ProductSearch
            onSearch={handleSearch}
            productList={allProducts}
            onProductsLoaded={handleProductsLoaded}
            searchError={searchError}
            productLoading={productLoading}
            productLoadingError={productLoadingError}
            disabled={connectionStatus === "disconnected"}
          />

          {/* Product Selection */}
          <ProductSelection
            items={searchResults}
            selectedItems={selectedItems}
            onItemToggle={handleItemToggle}
            searchLoading={searchLoading}
            disabled={connectionStatus === "disconnected"}
          />

          {/* Indicator Selection */}
          <IndicatorPanel
            indicatorList={allIndicators}
            selectedIndicators={selectedIndicators}
            onSelectIndicator={handleSelectIndicator}
            onRemoveIndicator={handleRemoveIndicator}
            indicatorLoading={indicatorLoading}
            indicatorLoadingError={indicatorLoadingError}
            disabled={connectionStatus === "disconnected"}
          />

          {/* Compare Button */}
          <ComparisonPanel
            onClick={handleCompare}
            disabled={
              connectionStatus === "disconnected" ||
              selectedItems.length === 0 ||
              selectedIndicators.length === 0
            }
            loading={comparisonLoading}
            error={comparisonError}
          />

          {/* Separator Line before Question Form */}
          <hr
            style={{
              border: "none",
              borderTop: "1px solid #333",
              margin: "2rem 0",
            }}
          />

          {/* Question Form */}
          <QuestionPanel
            question={question}
            setQuestion={setQuestion}
            handleSubmit={handleSubmit}
            loading={loading}
            error={questionError}
            answer={answer}
            selectedLLM={selectedLLM}
            handleLLMChange={handleLLMChange}
            disabled={
              connectionStatus === "disconnected" ||
              aiServiceStatus === "unavailable"
            }
          />
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
              onClose={handleCloseComparison}
            />

            {/* Analysis Panel */}
            {!comparisonLoading && !comparisonError && (
              <AnalysisPanel
                onAnalyse={handleAnalyseWithAI}
                aiAnalysis={aiAnalysis}
                disabled={
                  connectionStatus === "disconnected" ||
                  aiServiceStatus === "unavailable"
                }
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
