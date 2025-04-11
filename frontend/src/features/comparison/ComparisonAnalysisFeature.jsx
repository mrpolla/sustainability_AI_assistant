import React, { useState } from "react";
import { askQuestion } from "../../services/api";

// ComparisonAnalysisFeature component
// This component will trigger an LLM analysis when comparison data is available
const ComparisonAnalysisFeature = ({
  comparisonData,
  selectedLLM,
  onAnalysisComplete,
  onAnalysisError,
  disabled = false,
}) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);

  // Function to trigger the analysis
  const analyzeComparison = async () => {
    if (
      !comparisonData ||
      !comparisonData.products ||
      !comparisonData.indicators ||
      disabled
    ) {
      return;
    }

    setIsAnalyzing(true);
    setAnalysisError(null);

    try {
      // Build prompt for the LLM
      const prompt = buildComparisonPrompt(comparisonData);

      // Send the prompt to the LLM
      const response = await askQuestion(
        prompt,
        comparisonData.products.map((p) => p.id),
        [],
        selectedLLM
      );

      // Call onAnalysisComplete with the response
      if (onAnalysisComplete && typeof onAnalysisComplete === "function") {
        onAnalysisComplete(response.answer);
      }
    } catch (error) {
      console.error("Comparison analysis failed:", error);
      setAnalysisError(error.message || "Failed to analyze comparison data");

      if (onAnalysisError && typeof onAnalysisError === "function") {
        onAnalysisError(error);
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Function to build the prompt for the LLM
  const buildComparisonPrompt = (data) => {
    // Extract product names for easier reference
    const productNames = data.products.map((p) => p.name);

    // Begin prompt construction
    let prompt = `Please analyze and compare the following products based on the given environmental indicators and provide insights:\n\n`;

    // Add products being compared
    prompt += `Products being compared:\n`;
    productNames.forEach((name, i) => {
      prompt += `${i + 1}. ${name}\n`;
    });

    // Add detailed comparison data for each indicator
    prompt += `\nComparison data by indicator:\n`;

    data.indicators.forEach((indicator) => {
      prompt += `\nIndicator: ${indicator.key}\n`;
      prompt += `Unit: ${indicator.unit || "Not specified"}\n`;

      // For each product in this indicator
      prompt += `Values by product:\n`;

      indicator.productData.forEach((productData, i) => {
        const productId = productData.productId;
        const productName =
          data.products.find((p) => p.id === productId)?.name ||
          "Unknown Product";

        prompt += `- ${productName}:\n`;

        // Add module data for this product
        const modules = productData.modules;
        if (modules && Object.keys(modules).length > 0) {
          // Sort modules by name for consistent output
          const sortedModules = Object.entries(modules).sort(([a], [b]) =>
            a.localeCompare(b)
          );

          sortedModules.forEach(([module, value]) => {
            prompt += `  ${module}: ${value}\n`;
          });

          // Calculate and add total
          const totalValue = Object.values(modules).reduce(
            (sum, value) => sum + (parseFloat(value) || 0),
            0
          );
          prompt += `  Total: ${totalValue.toFixed(2)}\n`;
        } else {
          prompt += `  No module data available\n`;
        }
      });
    });

    // Add instructions for the analysis
    prompt += `\nPlease provide a concise analysis of these products based on the environmental indicators provided. Your analysis should include:
1. Which product performs better for each indicator and why
2. Overall environmental comparison of the products
3. Any significant insights about module contributions
4. Recommendations for potential improvements

Keep your analysis factual and based strictly on the data provided.`;

    return prompt;
  };

  return (
    <div style={{ marginTop: "1.5rem" }}>
      <button
        onClick={analyzeComparison}
        disabled={disabled || isAnalyzing || !comparisonData}
        style={{
          padding: "0.7rem 1.5rem",
          backgroundColor: "#4CAF50",
          color: "white",
          border: "none",
          borderRadius: "4px",
          cursor: disabled || isAnalyzing ? "not-allowed" : "pointer",
          fontSize: "1rem",
          fontWeight: "500",
          opacity: disabled || !comparisonData ? 0.7 : 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: "100%",
          transition: "background-color 0.2s",
        }}
      >
        {isAnalyzing ? "Analyzing Comparison Data..." : "Analyze with AI"}
      </button>

      {analysisError && (
        <div
          style={{
            marginTop: "1rem",
            color: "#f44336",
            padding: "0.5rem",
            fontSize: "0.9rem",
            backgroundColor: "rgba(244, 67, 54, 0.1)",
            borderRadius: "4px",
          }}
        >
          {analysisError}
        </div>
      )}
    </div>
  );
};

export default ComparisonAnalysisFeature;
