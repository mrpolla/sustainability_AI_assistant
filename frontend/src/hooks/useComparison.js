import { useState, useCallback } from "react";
import { compareProducts } from "../services/api";

/**
 * Hook for managing product comparison functionality
 */
const useComparison = (
  selectedItems,
  selectedIndicators,
  setConnectionStatus
) => {
  // State for comparison
  const [showComparison, setShowComparison] = useState(false);
  const [comparisonData, setComparisonData] = useState(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState("");

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
  }, [selectedItems, selectedIndicators, setConnectionStatus]);

  // Handle closing comparison view
  const handleCloseComparison = useCallback(() => {
    setShowComparison(false);
  }, []);

  return {
    showComparison,
    comparisonData,
    comparisonLoading,
    comparisonError,
    handleCompare,
    handleCloseComparison,
  };
};

export default useComparison;
