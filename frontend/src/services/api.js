/**
 * API service for handling backend communication
 */

// Backend API URL
const API_URL = "http://localhost:8001";

// Default request timeout in milliseconds
const DEFAULT_TIMEOUT = 20000;

// Maximum number of retry attempts for failed requests
const MAX_RETRIES = 2;

// Exponential backoff starting delay in milliseconds
const INITIAL_BACKOFF = 1000;

/**
 * Validate that required parameters are present
 * @param {Object} params - Parameters to validate
 * @param {string[]} required - List of required parameter names
 * @throws {Error} - If a required parameter is missing or invalid
 */
const validateParams = (params, required = []) => {
  if (!params || typeof params !== "object") {
    throw new Error("Invalid request parameters: must be an object");
  }

  for (const param of required) {
    if (params[param] === undefined || params[param] === null) {
      throw new Error(`Missing required parameter: ${param}`);
    }
  }
};

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
 * Implements exponential backoff retry logic
 * @param {Function} operation - Function to retry
 * @param {number} maxRetries - Maximum number of retries
 * @param {number} initialBackoff - Initial backoff delay in ms
 * @returns {Promise<any>} - Result of the operation
 */
const withRetry = async (
  operation,
  maxRetries = MAX_RETRIES,
  initialBackoff = INITIAL_BACKOFF
) => {
  let lastError;
  let retryCount = 0;

  while (retryCount <= maxRetries) {
    try {
      if (retryCount > 0) {
        console.warn(`Retry attempt ${retryCount}/${maxRetries}`);
      }
      return await operation();
    } catch (error) {
      lastError = error;

      // Don't retry if it's a client error (4xx) except 503
      if (error.status >= 400 && error.status < 500 && error.status !== 503) {
        break;
      }

      if (retryCount >= maxRetries) {
        break;
      }

      // Calculate backoff time with exponential increase
      const backoffTime = initialBackoff * Math.pow(2, retryCount);
      console.warn(`Request failed. Retrying in ${backoffTime}ms...`);

      await new Promise((resolve) => setTimeout(resolve, backoffTime));
      retryCount++;
    }
  }

  throw lastError;
};

/**
 * Extract and format error details from response
 * @param {Response} response - Fetch Response object
 * @param {any} responseData - Parsed response data
 * @returns {Error} - Formatted error with details
 */
const createDetailedError = (response, responseData, responseText) => {
  // Basic error message
  let errorMessage = `API error ${response.status}`;
  if (response.statusText) {
    errorMessage += ` (${response.statusText})`;
  }

  // Add details from response if available
  if (responseData) {
    if (responseData.error) {
      errorMessage += `: ${responseData.error}`;
    } else if (responseData.detail) {
      errorMessage += `: ${responseData.detail}`;
    } else if (responseData.message) {
      errorMessage += `: ${responseData.message}`;
    }
  }

  const error = new Error(errorMessage);

  error.status = response.status;
  error.statusText = response.statusText;
  error.endpoint = response.url;
  error.responseData = responseData;

  return error;
};

/**
 * Generic API request function with error handling
 * @param {string} endpoint - API endpoint
 * @param {Object} data - Request data
 * @param {Object} options - Additional request options
 * @returns {Promise<Object>} - Response data
 */
const apiRequest = async (endpoint, data, options = {}) => {
  const { timeout = DEFAULT_TIMEOUT, retries = MAX_RETRIES } = options;
  const requestId = Math.random().toString(36).substring(2, 12);
  const url = `${API_URL}${endpoint}`;

  console.log(`Request to ${endpoint} [${requestId}]`);

  const startTime = Date.now();

  try {
    return await withRetry(
      async () => {
        const response = await timeoutFetch(
          fetch(url, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Request-ID": requestId,
            },
            body: JSON.stringify(data),
          }),
          timeout
        );

        // Parse the response
        let responseData;
        let responseText = "";

        try {
          responseText = await response.text();
          responseData = responseText ? JSON.parse(responseText) : {};
        } catch (parseError) {
          console.error(
            `Failed to parse response as JSON: ${responseText.substring(
              0,
              100
            )}`
          );
          throw new Error(
            `Invalid response format: ${responseText.substring(0, 100)}`
          );
        }

        // Check if the response is OK
        if (!response.ok) {
          const error = createDetailedError(
            response,
            responseData,
            responseText
          );
          console.error(`API error ${response.status}: ${error.message}`);
          throw error;
        }

        return responseData;
      },
      retries,
      INITIAL_BACKOFF
    );
  } catch (error) {
    const duration = Date.now() - startTime;

    if (error.name === "AbortError" || error.message.includes("timed out")) {
      console.error(`Request timed out after ${duration}ms [${requestId}]`);
      throw new Error(
        `Request timed out after ${timeout}ms. The server took too long to respond.`
      );
    } else if (
      error.name === "TypeError" &&
      error.message.includes("Failed to fetch")
    ) {
      console.error(`Network error after ${duration}ms [${requestId}]`);
      throw new Error(
        "Cannot connect to the server. Please check your internet connection."
      );
    } else if (error.status === 503) {
      // Special handling for 503 Service Unavailable
      console.error(
        `Service unavailable error after ${duration}ms [${requestId}]`
      );

      let errorMsg =
        "The AI service is currently unavailable. Please try again later.";

      // Try to extract message from response if available
      if (error.responseData && error.responseData.answer) {
        errorMsg = error.responseData.answer;
      }

      const serviceError = new Error(errorMsg);
      serviceError.isServiceUnavailable = true;
      serviceError.status = 503;
      throw serviceError;
    } else {
      console.error(`Request to ${endpoint} failed: ${error.message}`);
      throw error;
    }
  }
};

/**
 * Send a simple question to the backend API (without RAG)
 * @param {string} question - The fully formulated question to send
 * @param {string} llmModel - Selected LLM model
 * @returns {Promise<Object>} - The response data
 */
export const askQuestion = async (question, llmModel = "mistral") => {
  try {
    validateParams({ question }, ["question"]);

    console.log(`Asking simple question with model ${llmModel}`);

    const data = await apiRequest(
      "/ask",
      {
        question,
        documentIds: [], // Keep this empty array to satisfy the backend schema
        llmModel: llmModel,
      },
      {
        timeout: DEFAULT_TIMEOUT * 1.5, // 30 seconds
        retries: 3, // More retries for AI requests
      }
    );

    return {
      answer: data.answer || "No answer returned from the server.",
      metadata: data.metadata || {},
    };
  } catch (error) {
    console.error(`Question request failed: ${error.message}`);

    // If it's a 503 error, make sure it has the service unavailable flag
    if (error.status === 503 && !error.isServiceUnavailable) {
      const serviceError = new Error(
        error.message || "The AI service is currently unavailable"
      );
      serviceError.isServiceUnavailable = true;
      serviceError.status = 503;
      throw serviceError;
    }

    throw error;
  }
};

/**
 * Send a question to the backend API using RAG
 * @param {string} question - The question to send
 * @param {string[]} selectedDocuments - Array of selected document IDs
 * @param {string[]} selectedIndicators - Array of selected indicator keys
 * @param {string} llmModel - Selected LLM model
 * @returns {Promise<Object>} - The response data
 */
export const askRagQuestion = async (
  question,
  selectedDocuments = [],
  selectedIndicators = [],
  llmModel = "mistral"
) => {
  try {
    validateParams({ question }, ["question"]);
    console.log(`Documents ${selectedDocuments}`);

    // Ensure arrays are properly formatted
    const documentIds = Array.isArray(selectedDocuments)
      ? selectedDocuments.filter(
          (id) => id !== null && id !== undefined && id !== ""
        )
      : [];
    const indicatorIds = Array.isArray(selectedIndicators)
      ? selectedIndicators
      : [];

    console.log(`Asking RAG question with model ${llmModel}`);
    console.log(
      `Selected documents: ${
        documentIds.length > 0 ? documentIds.join(", ") : "none"
      }`
    );
    console.log(
      `Selected indicators: ${
        indicatorIds.length > 0 ? indicatorIds.join(", ") : "none"
      }`
    );

    const payload = {
      question,
      documentIds: documentIds,
      indicatorIds: indicatorIds,
      llmModel: llmModel || "mistral",
    };

    console.log(
      "Sending payload to /askrag:",
      JSON.stringify(payload, null, 2)
    );

    const data = await apiRequest("/askrag", payload, {
      timeout: DEFAULT_TIMEOUT * 1.5, // 30 seconds
      retries: 3, // More retries for AI requests
    });

    return {
      answer: data.answer || "No answer returned from the server.",
      metadata: data.metadata || {},
    };
  } catch (error) {
    console.error(`RAG question request failed: ${error.message}`);

    // If it's a 503 error, make sure it has the service unavailable flag
    if (error.status === 503 && !error.isServiceUnavailable) {
      const serviceError = new Error(
        error.message || "The AI service is currently unavailable"
      );
      serviceError.isServiceUnavailable = true;
      serviceError.status = 503;
      throw serviceError;
    }

    throw error;
  }
};

export const fetchFilters = async () => {
  const response = await fetch("http://localhost:8001/filters");
  if (!response.ok) {
    throw new Error(`Failed to fetch filters: ${response.statusText}`);
  }
  return await response.json();
};

/**
 * Search for products in the database
 * @param {string} searchTerm - The search term to find products
 * @returns {Promise<Object>} - The search results
 */
export const searchProducts = async (filters = {}) => {
  return await apiRequest("/search", filters);
};

/**
 * Fetch all product names for autocomplete
 * @returns {Promise<Array>} - Array of product names
 */
export const fetchAllProductNames = async () => {
  try {
    const data = await apiRequest("/products", {});

    return {
      products: Array.isArray(data.products) ? data.products : [],
      timestamp: new Date().toISOString(),
    };
  } catch (error) {
    console.error(`Failed to fetch product names: ${error.message}`);
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

    return {
      indicators: Array.isArray(data.indicators) ? data.indicators : [],
      timestamp: new Date().toISOString(),
    };
  } catch (error) {
    console.error(`Failed to fetch indicators: ${error.message}`);
    throw error;
  }
};

/**
 * Compare selected products with selected indicators
 * @param {string[]} productIds - Array of selected product IDs
 * @param {Object[]} indicators - Array of selected indicator objects
 * @returns {Promise<Object>} - Comparison data
 */
export const compareProducts = async (productIds, indicators) => {
  try {
    validateParams({ productIds, indicators }, ["productIds", "indicators"]);

    if (!Array.isArray(productIds) || productIds.length === 0) {
      throw new Error("productIds must be a non-empty array");
    }

    if (!Array.isArray(indicators)) {
      throw new Error("indicators must be an array");
    }

    // Extract indicator keys from indicator objects
    const indicatorKeys = indicators.map((indicator) => {
      if (!indicator || typeof indicator !== "object" || !indicator.key) {
        throw new Error(
          "Each indicator must be an object with a name property"
        );
      }
      return indicator.key;
    });

    const data = await apiRequest(
      "/compare",
      {
        productIds,
        indicatorKeys,
      },
      {
        timeout: DEFAULT_TIMEOUT * 1.5,
      }
    );

    return {
      ...data,
      timestamp: new Date().toISOString(),
    };
  } catch (error) {
    console.error(`Comparison request failed: ${error.message}`);
    throw error;
  }
};

/**
 * Health check function to verify API connectivity
 * @returns {Promise<boolean>} - True if API is reachable
 */
export const checkApiHealth = async () => {
  try {
    await apiRequest(
      "/health",
      {},
      {
        timeout: 5000, // Short timeout for health checks
        retries: 0, // No retries for health checks
      }
    );
    return true;
  } catch (error) {
    console.error(`API health check failed: ${error.message}`);
    return false;
  }
};
