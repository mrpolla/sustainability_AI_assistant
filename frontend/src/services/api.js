/**
 * API service for handling backend communication
 */

// Update this URL to match your backend server address
const API_URL = "http://localhost:8001";

// Default request timeout in milliseconds
const DEFAULT_TIMEOUT = 10000;

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
 * Send a question to the backend API
 * @param {string} question - The question to send
 * @param {string[]} selectedDocuments - Array of selected document IDs
 * @returns {Promise<Object>} - The response data
 */
export const askQuestion = async (question, selectedDocuments = []) => {
  const response = await fetch(`${API_URL}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      documentIds: selectedDocuments,
    }),
  });

  if (!response.ok) {
    throw new Error("API request failed");
  }

  return await response.json();
};

/**
 * Search for products in the database
 * @param {string} searchTerm - The search term to find products
 * @returns {Promise<Object>} - The search results
 */
export const searchProducts = async (searchTerm) => {
  try {
    console.log(
      `Sending search request to ${API_URL}/search with term: ${searchTerm}`
    );

    const response = await timeoutFetch(
      fetch(`${API_URL}/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ searchTerm }),
      })
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error(
        `Search API returned status ${response.status}: ${errorText}`
      );
      throw new Error(
        `API error: ${response.status} - ${errorText || response.statusText}`
      );
    }

    const data = await response.json();
    console.log("Search API response:", data);
    return data;
  } catch (error) {
    console.error("Search request failed:", error.message);
    throw error;
  }
};
