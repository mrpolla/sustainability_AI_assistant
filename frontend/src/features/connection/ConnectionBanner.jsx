import React from "react";

/**
 * Component for displaying connection status banners
 */
const ConnectionBanner = ({ connectionStatus, handleRetryConnection }) => {
  if (connectionStatus === "checking") {
    return (
      <div
        style={{
          backgroundColor: "#263238",
          color: "#90caf9",
          padding: "0.8rem",
          borderRadius: "4px",
          marginBottom: "1.5rem",
          border: "1px solid #37474f",
          display: "flex",
          alignItems: "center",
        }}
      >
        <div>Checking connection to server...</div>
      </div>
    );
  }

  if (connectionStatus === "disconnected") {
    return (
      <div
        style={{
          backgroundColor: "#fff0f0",
          color: "#d32f2f",
          padding: "0.8rem",
          borderRadius: "4px",
          marginBottom: "1.5rem",
          border: "1px solid #ffcdd2",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <strong>Cannot connect to server.</strong> The application might not
          function correctly.
        </div>
        <button
          onClick={handleRetryConnection}
          style={{
            backgroundColor: "#d32f2f",
            color: "white",
            border: "none",
            padding: "0.4rem 0.8rem",
            borderRadius: "4px",
            cursor: "pointer",
          }}
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return null;
};

export default ConnectionBanner;
