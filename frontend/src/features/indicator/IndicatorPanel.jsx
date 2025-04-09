import React from "react";
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
      )}
    </div>
  );
};

export default IndicatorPanel;
