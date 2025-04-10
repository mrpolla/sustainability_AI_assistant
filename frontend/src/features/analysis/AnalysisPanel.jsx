import React from "react";
import AIAnalysisPanel from "../../components/AIAnalysisPanel";

/**
 * Feature component for AI analysis of comparison results
 */
const AnalysisPanel = ({ onAnalyse, aiAnalysis, disabled }) => {
  return (
    <AIAnalysisPanel
      onAnalyse={onAnalyse}
      loading={aiAnalysis.loading}
      result={aiAnalysis.result}
      error={aiAnalysis.error}
      disabled={disabled}
    />
  );
};

export default AnalysisPanel;
