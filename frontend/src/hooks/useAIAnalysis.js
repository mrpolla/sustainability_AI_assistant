import { useState, useCallback } from "react";
import { askQuestion } from "../services/api";

/**
 * Hook for managing AI analysis of comparison results
 */
const useAIAnalysis = (
  comparisonData,
  setConnectionStatus,
  setAiServiceStatus
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
      !comparisonData.indicators
    ) {
      return;
    }

    setAiAnalysis({ loading: true, result: "", error: null });

    try {
      // Get product information
      const productNames = comparisonData.products
        .map((p) => p.name)
        .join(", ");
      const productCount = comparisonData.products.length;

      // Get indicator information
      const indicatorNames = comparisonData.indicators
        .map((ind) => ind.name)
        .join(", ");
      const indicatorCount = comparisonData.indicators.length;

      // Create a detailed summary of the comparison data
      let comparisonDetails = "";

      comparisonData.indicators.forEach((indicator) => {
        comparisonDetails += `\nIndicator: ${indicator.name} (${
          indicator.unit || "no unit"
        })\n`;

        // Process each product's data for this indicator
        indicator.productData.forEach((product) => {
          const productInfo = comparisonData.products.find(
            (p) => p.id === product.productId
          );
          if (productInfo) {
            comparisonDetails += `- ${productInfo.name}:\n`;

            // Process module data
            const modules = product.modules || {};
            Object.entries(modules).forEach(([moduleName, value]) => {
              comparisonDetails += `  - ${moduleName}: ${value}\n`;
            });
          }
        });
      });

      // Create the fully formulated prompt
      const fullyFormulatedQuestion = `
You are an expert in environmental product declarations (EPD) and life cycle assessment (LCA).
Please analyze the following comparison results between ${productCount} products across ${indicatorCount} environmental impact indicators.

Products being compared: ${productNames}
Indicators being analyzed: ${indicatorNames}

Detailed comparison data:
${comparisonDetails}

Please provide an expert analysis of these results. Include:
1. A comparison of the overall environmental performance of these products
2. Identification of which product performs best for each indicator
3. Explanation of what each indicator means in practical terms
4. Recommendations based on this comparison
5. Any notable patterns or insights from the module-level data

Keep your analysis clear and helpful for someone who may not be an expert in LCA.
`.trim();

      console.log(
        "Sending fully formulated question to LLM:",
        fullyFormulatedQuestion
      );

      // Call the API with the fully formulated question
      const response = await askQuestion(fullyFormulatedQuestion, "mistral");

      setAiAnalysis({ loading: false, result: response.answer, error: null });
    } catch (error) {
      console.error("AI analysis failed:", error);
      setAiAnalysis({
        loading: false,
        result: "",
        error: error.message || "Analysis failed",
      });

      // If it's a service unavailable error, update the AI service status
      if (error.isServiceUnavailable) {
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
  }, [comparisonData, setConnectionStatus, setAiServiceStatus]);

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
