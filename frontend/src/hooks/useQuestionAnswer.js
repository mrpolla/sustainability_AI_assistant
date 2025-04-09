import { useState, useCallback } from "react";
import { askQuestion } from "../services/api";

/**
 * Hook for managing question and answer functionality
 */
const useQuestionAnswer = (
  selectedItems,
  selectedIndicators,
  setConnectionStatus,
  setAiServiceStatus
) => {
  // State for questions and answers
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [questionError, setQuestionError] = useState("");

  // State for LLM selection
  const [selectedLLM, setSelectedLLM] = useState("mistral");

  // Handle question submission
  const handleSubmit = useCallback(async () => {
    if (!question?.trim()) {
      setQuestionError("Please enter a question");
      return;
    }

    setLoading(true);
    setAnswer("");
    setQuestionError("");

    try {
      const indicatorKeys = selectedIndicators
        .map((indicator) => indicator?.name)
        .filter(Boolean);

      const data = await askQuestion(
        question,
        selectedItems,
        indicatorKeys,
        selectedLLM
      );

      if (!data) {
        throw new Error("No data returned from question request");
      }

      if (data.answer) {
        setAnswer(data.answer);
      } else {
        setAnswer("No answer returned from the server.");
      }
    } catch (error) {
      console.error("Question submission failed:", error);

      if (error.isServiceUnavailable || error.status === 503) {
        setAiServiceStatus("unavailable");
        setQuestionError("The AI service is currently unavailable");
        setAnswer(
          "The AI service is temporarily unavailable. This is not related to your question or selections. " +
            "Please try again later."
        );
      } else {
        setQuestionError(error.message || "Unknown error");
        setAnswer("Failed to get an answer. Please try again later.");

        if (
          error.message?.includes("connect to the server") ||
          error.message?.includes("timed out")
        ) {
          setConnectionStatus("disconnected");
        }
      }
    } finally {
      setLoading(false);
    }
  }, [
    question,
    selectedItems,
    selectedIndicators,
    selectedLLM,
    setConnectionStatus,
    setAiServiceStatus,
  ]);

  // Handle LLM selection change
  const handleLLMChange = useCallback((e) => {
    const newValue = e.target.value;
    const LLM_OPTIONS = [
      "mistral",
      "llama3",
      "gemma:2b",
      "qwen:1.8b",
      "phi3:mini",
    ];

    if (LLM_OPTIONS.includes(newValue)) {
      setSelectedLLM(newValue);
    } else {
      setSelectedLLM("mistral");
    }
  }, []);

  return {
    question,
    setQuestion,
    answer,
    loading,
    questionError,
    selectedLLM,
    handleSubmit,
    handleLLMChange,
  };
};

export default useQuestionAnswer;
