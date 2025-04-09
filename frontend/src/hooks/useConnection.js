import { useState, useCallback } from "react";
import { fetchAllProductNames, askQuestion } from "../services/api";

/**
 * Hook for managing connection status and related functionality
 */
const useConnection = (DEFAULT_LLM) => {
  const [connectionStatus, setConnectionStatus] = useState("unknown");
  const [aiServiceStatus, setAiServiceStatus] = useState("unknown");

  // Handle retry connection button click
  const handleRetryConnection = useCallback(() => {
    setConnectionStatus("checking");
    setAiServiceStatus("unknown");

    // Try to load products
    const loadProducts = async () => {
      try {
        const data = await fetchAllProductNames();
        if (data && Array.isArray(data.products)) {
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
          throw new Error("Invalid product data format");
        }
      } catch (error) {
        console.error("Product reload failed:", error);
        setConnectionStatus("disconnected");
        setAiServiceStatus("unknown");
      }
    };

    loadProducts();
  }, [DEFAULT_LLM]);

  return {
    connectionStatus,
    setConnectionStatus,
    aiServiceStatus,
    setAiServiceStatus,
    handleRetryConnection,
  };
};

export default useConnection;
