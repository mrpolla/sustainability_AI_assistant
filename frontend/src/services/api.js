/**
 * API service for handling backend communication
 */

const API_URL = "http://localhost:8001";

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
