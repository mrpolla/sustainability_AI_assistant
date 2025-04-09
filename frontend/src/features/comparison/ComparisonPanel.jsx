import React from "react";
import CompareButton from "../../components/CompareButton/CompareButton";

/**
 * Component for product comparison functionality
 */
const ComparisonPanel = ({ onClick, disabled, loading, error }) => {
  return (
    <div
      style={{
        marginTop: "1.5rem",
        marginBottom: "1.5rem",
        display: "flex",
        justifyContent: "flex-start",
      }}
    >
      <CompareButton onClick={onClick} disabled={disabled} loading={loading} />
      {error && (
        <div
          style={{
            color: "#d32f2f",
            marginLeft: "1rem",
            fontSize: "0.9rem",
            display: "flex",
            alignItems: "center",
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
};

export default ComparisonPanel;
