import { useState, useCallback } from "react";
import { analyzeComparison } from "../services/api";

/**
 * Hook for managing AI analysis of comparison results
 * Updated to use a dedicated comparison endpoint
 */
const useAIAnalysis = (
  comparisonData,
  setConnectionStatus,
  setAiServiceStatus,
  selectedLLM
) => {
  // State for AI analysis
  const [aiAnalysis, setAiAnalysis] = useState({
    loading: false,
    result: "",
    error: null,
  });

  // Handle analysis request
  const handleAnalyseWithAI = useCallback(async () => {
    if (
      !comparisonData ||
      !comparisonData.products ||
      !comparisonData.indicators ||
      comparisonData.products.length === 0 ||
      comparisonData.indicators.length === 0
    ) {
      setAiAnalysis({
        loading: false,
        result: "",
        error:
          "No comparison data available. Please select products and indicators first.",
      });
      return;
    }

    setAiAnalysis({ loading: true, result: "", error: null });

    try {
      // Extract product IDs
      const productIds = comparisonData.products.map((product) => product.id);

      // Extract indicator keys
      const indicatorIds = comparisonData.indicators.map(
        (indicator) => indicator.key
      );

      console.log("Analyzing comparison:", {
        products: comparisonData.products.map((p) => p.name).join(", "),
        indicators: comparisonData.indicators.map((i) => i.key).join(", "),
        model: selectedLLM,
      });

      // Call the dedicated comparison analysis endpoint
      const response = await analyzeComparison(
        productIds,
        indicatorIds,
        selectedLLM
      );

      setAiAnalysis({ loading: false, result: response.answer, error: null });
    } catch (error) {
      console.error("AI analysis failed:", error);

      let errorMessage = "Analysis failed";
      if (error.message) {
        errorMessage = error.message.includes("503")
          ? "The AI service is currently unavailable. Please try again later."
          : error.message;
      }

      setAiAnalysis({
        loading: false,
        result: "",
        error: errorMessage,
      });

      // If it's a service unavailable error, update the AI service status
      if (error.isServiceUnavailable || error.status === 503) {
        setAiServiceStatus("unavailable");
      }

      // If it's a connection error, update connection status
      if (
        error.message?.includes("connect to the server") ||
        error.message?.includes("timed out")
      ) {
        setConnectionStatus("disconnected");
      }
    }
  }, [comparisonData, selectedLLM, setConnectionStatus, setAiServiceStatus]);

  // Reset analysis
  const resetAnalysis = useCallback(() => {
    setAiAnalysis({ loading: false, result: "", error: null });
  }, []);

  return {
    aiAnalysis,
    handleAnalyseWithAI,
    resetAnalysis,
  };
};

export default useAIAnalysis;
