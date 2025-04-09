import React from "react";

/**
 * Component for displaying AI service status
 */
const AIServiceBanner = ({ aiServiceStatus, handleRetryConnection }) => {
  if (aiServiceStatus !== "unavailable") {
    return null;
  }

  return (
    <div
      style={{
        backgroundColor: "#433d5f",
        color: "#e0c3fc",
        padding: "0.8rem",
        borderRadius: "4px",
        marginBottom: "1.5rem",
        border: "1px solid #7b61c4",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <div>
        <strong>AI Service Status:</strong> The AI model service is currently
        unavailable. Your other actions will still work, but you won't be able
        to ask questions until the service is back online.
      </div>
      <button
        onClick={handleRetryConnection}
        style={{
          backgroundColor: "#7b61c4",
          color: "white",
          border: "none",
          padding: "0.4rem 0.8rem",
          borderRadius: "4px",
          cursor: "pointer",
          marginLeft: "1rem",
        }}
      >
        Check Status
      </button>
    </div>
  );
};

export default AIServiceBanner;
