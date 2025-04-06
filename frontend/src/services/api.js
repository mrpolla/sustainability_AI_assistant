/**
 * API service for handling backend communication
 */

// Backend API URL
const API_URL = "http://localhost:8001";

// Default request timeout in milliseconds
const DEFAULT_TIMEOUT = 20000;

/**
 * Helper function to create a request with timeout
 * @param {Promise} fetchPromise - The fetch promise
 * @param {number} timeout - Timeout in milliseconds
 * @returns {Promise} - Promise with timeout
 */
const timeoutFetch = (fetchPromise, timeout = DEFAULT_TIMEOUT) => {
  let timeoutId;

  const timeoutPromise = new Promise((_, reject) => {
    timeoutId = setTimeout(() => {
      reject(new Error(`Request timed out after ${timeout}ms`));
    }, timeout);
  });

  return Promise.race([fetchPromise, timeoutPromise]).finally(() => {
    clearTimeout(timeoutId);
  });
};

/**
 * Generic API request function with error handling
 * @param {string} endpoint - API endpoint
 * @param {Object} data - Request data
 * @returns {Promise<Object>} - Response data
 */
const apiRequest = async (endpoint, data) => {
  try {
    console.log(`Sending request to ${API_URL}${endpoint}`);

    const response = await timeoutFetch(
      fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      })
    );

    // Try to parse the response as JSON first
    let responseData;
    let responseText = "";

    try {
      responseText = await response.text();
      responseData = JSON.parse(responseText);
    } catch (parseError) {
      console.error("Failed to parse response as JSON:", responseText);
      throw new Error(
        `Invalid response format: ${responseText.substring(0, 100)}`
      );
    }

    // Check if the response is OK
    if (!response.ok) {
      console.error(`API error ${response.status}:`, responseData);
      throw new Error(
        responseData.error ||
          responseData.detail ||
          `API error: ${response.status}`
      );
    }

    return responseData;
  } catch (error) {
    if (error.name === "AbortError" || error.message.includes("timed out")) {
      console.error("Request timed out");
      throw new Error(
        "Request timed out. The server took too long to respond."
      );
    } else if (
      error.name === "TypeError" &&
      error.message.includes("Failed to fetch")
    ) {
      console.error("Network error:", error);
      throw new Error(
        "Cannot connect to the server. Please check your internet connection."
      );
    } else {
      console.error(`Request to ${endpoint} failed:`, error);
      throw error;
    }
  }
};

/**
 * Send a question to the backend API
 * @param {string} question - The question to send
 * @param {string[]} selectedDocuments - Array of selected document IDs
 * @returns {Promise<Object>} - The response data
 */
export const askQuestion = async (question, selectedDocuments = []) => {
  try {
    const data = await apiRequest("/ask", {
      question,
      documentIds: selectedDocuments,
    });

    return {
      answer: data.answer || "No answer returned from the server.",
    };
  } catch (error) {
    console.error("Question request failed:", error);
    throw error;
  }
};

/**
 * Search for products in the database
 * @param {string} searchTerm - The search term to find products
 * @returns {Promise<Object>} - The search results
 */
export const searchProducts = async (searchTerm) => {
  try {
    const data = await apiRequest("/search", { searchTerm });

    // Ensure items is always an array even if the backend returns null or undefined
    return {
      items: Array.isArray(data.items) ? data.items : [],
    };
  } catch (error) {
    console.error("Search request failed:", error);
    throw error;
  }
};

/**
 * Fetch all product names for autocomplete
 * @returns {Promise<Array>} - Array of product names
 */
export const fetchAllProductNames = async () => {
  try {
    const data = await apiRequest("/products", {});

    // Ensure products is always an array even if the backend returns null or undefined
    return {
      products: Array.isArray(data.products) ? data.products : [],
    };
  } catch (error) {
    console.error("Failed to fetch product names:", error);
    throw error;
  }
};

/**
 * Fetch all unique indicators
 * @returns {Promise<Array>} - Array of indicators
 */
export const fetchAllIndicators = async () => {
  try {
    const data = await apiRequest("/indicators", {});

    // Ensure indicators is always an array even if the backend returns null or undefined
    return {
      indicators: Array.isArray(data.indicators) ? data.indicators : [],
    };
  } catch (error) {
    console.error("Failed to fetch indicators:", error);
    throw error;
  }
};
