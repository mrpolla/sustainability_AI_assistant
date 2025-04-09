import { useState, useCallback } from "react";
import { fetchAllIndicators } from "../services/api";

/**
 * Hook for managing indicator data and selection
 */
const useIndicators = () => {
  // State for indicators
  const [allIndicators, setAllIndicators] = useState([]);
  const [selectedIndicators, setSelectedIndicators] = useState([]);
  const [indicatorLoadingError, setIndicatorLoadingError] = useState("");
  const [indicatorLoading, setIndicatorLoading] = useState(false);

  // Load indicator data
  const loadIndicators = useCallback(async () => {
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

  return {
    allIndicators,
    selectedIndicators,
    indicatorLoadingError,
    indicatorLoading,
    loadIndicators,
    handleSelectIndicator,
    handleRemoveIndicator,
    setSelectedIndicators,
  };
};

export default useIndicators;
