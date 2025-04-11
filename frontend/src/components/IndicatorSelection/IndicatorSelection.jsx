import React from "react";
import IndicatorSearch from "../IndicatorSearch";
import IndicatorTagList from "../IndicatorTagList";

const IndicatorSelection = ({
  indicatorList,
  selectedIndicators,
  onSelectIndicator,
  onRemoveIndicator,
}) => {
  // Function to handle when an indicator is selected from the search
  const handleIndicatorSelect = (indicator) => {
    // Check if the indicator is already selected
    const isAlreadySelected = selectedIndicators.some(
      (selected) => selected.id === indicator.key
    );

    // Only add if not already selected
    if (!isAlreadySelected && onSelectIndicator) {
      onSelectIndicator(indicator);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: "0.75rem" }}>
        <IndicatorSearch
          indicatorList={indicatorList}
          onIndicatorSelect={handleIndicatorSelect}
        />
      </div>
      <IndicatorTagList
        selectedIndicators={selectedIndicators}
        onRemoveIndicator={onRemoveIndicator}
      />
    </div>
  );
};

export default IndicatorSelection;
