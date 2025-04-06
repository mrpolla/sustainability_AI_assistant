import React from "react";
import IndicatorTag from "../IndicatorTag";

const IndicatorTagList = ({ selectedIndicators, onRemoveIndicator }) => {
  if (!selectedIndicators || selectedIndicators.length === 0) {
    return (
      <div
        style={{
          padding: "0.75rem",
          color: "#777",
          fontStyle: "italic",
          borderRadius: "4px",
          border: "1px dashed #444",
          backgroundColor: "#1a1a1a",
        }}
      >
        No indicators selected. Search and select indicators above.
      </div>
    );
  }

  return (
    <div
      style={{
        padding: "0.75rem",
        borderRadius: "4px",
        border: "1px solid #444",
        backgroundColor: "#1a1a1a",
        minHeight: "2.5rem",
      }}
    >
      {selectedIndicators.map((indicator) => (
        <IndicatorTag
          key={indicator.id}
          indicator={indicator}
          onRemove={onRemoveIndicator}
        />
      ))}
    </div>
  );
};

export default IndicatorTagList;
