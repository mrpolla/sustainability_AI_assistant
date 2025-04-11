import React, { useState } from "react";
import IndicatorSelection from "../../components/IndicatorSelection";

/**
 * Component for indicator selection functionality
 */
const IndicatorPanel = ({
  indicatorList,
  selectedIndicators,
  onSelectIndicator,
  onRemoveIndicator,
  indicatorLoading,
  indicatorLoadingError,
  disabled,
}) => {
  const [showDescriptions, setShowDescriptions] = useState(false);

  return (
    <div style={{ marginTop: "2rem", marginBottom: "1.5rem" }}>
      <h3>Select Indicators</h3>
      {indicatorLoading && (
        <div style={{ marginBottom: "0.5rem", color: "#90caf9" }}>
          Loading indicators...
        </div>
      )}
      {indicatorLoadingError && (
        <div
          style={{
            color: "#d32f2f",
            fontSize: "0.85rem",
            marginBottom: "0.5rem",
            padding: "0.3rem",
            backgroundColor: "rgba(211, 47, 47, 0.1)",
            borderRadius: "4px",
          }}
        >
          {indicatorLoadingError}
        </div>
      )}
      <IndicatorSelection
        indicatorList={indicatorList}
        selectedIndicators={selectedIndicators}
        onSelectIndicator={onSelectIndicator}
        onRemoveIndicator={onRemoveIndicator}
        disabled={disabled}
      />
      {selectedIndicators.length > 0 && (
        <div>
          <div
            style={{
              fontSize: "0.9rem",
              color: "#999",
              marginTop: "0.5rem",
            }}
          >
            {selectedIndicators.length} indicator
            {selectedIndicators.length !== 1 ? "s" : ""} selected
          </div>

          <div style={{ marginTop: "0.75rem" }}>
            <button
              onClick={() => setShowDescriptions(!showDescriptions)}
              style={{
                backgroundColor: "#2c3b4c",
                border: "none",
                color: "#e0e0e0",
                padding: "0.35rem 0.75rem",
                borderRadius: "4px",
                cursor: "pointer",
                fontSize: "0.85rem",
              }}
            >
              {showDescriptions ? "Hide Descriptions" : "Show Descriptions"}
            </button>
          </div>

          {showDescriptions && (
            <div
              style={{
                marginTop: "0.5rem",
                border: "1px solid #444",
                borderRadius: "4px",
                backgroundColor: "#1a1a1a",
                padding: "0.75rem",
              }}
            >
              {selectedIndicators.map((indicator) => (
                <div key={indicator.key} style={{ marginBottom: "0.75rem" }}>
                  <div style={{ fontWeight: "bold", color: "#90caf9" }}>
                    {indicator.key} - {indicator.name}
                  </div>
                  {indicator.short_description && (
                    <div style={{ marginTop: "0.25rem", fontSize: "0.9rem" }}>
                      {indicator.short_description}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default IndicatorPanel;
