import React from "react";

const IndicatorTag = ({ indicator, onRemove }) => {
  const handleDoubleClick = () => {
    if (onRemove) {
      onRemove(indicator);
    }
  };

  const handleRemoveClick = (e) => {
    e.stopPropagation();
    if (onRemove) {
      onRemove(indicator);
    }
  };

  return (
    <div
      onDoubleClick={handleDoubleClick}
      style={{
        display: "inline-flex",
        alignItems: "center",
        backgroundColor: "#2c3b4c",
        borderRadius: "4px",
        padding: "0.35rem 0.5rem",
        margin: "0 0.5rem 0.5rem 0",
        fontSize: "0.9rem",
        color: "#e0e0e0",
        cursor: "default",
        userSelect: "none",
        transition: "background-color 0.2s",
        maxWidth: "100%",
      }}
    >
      <span
        style={{
          marginRight: "0.4rem",
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
      >
        {indicator.name}
      </span>
      <button
        onClick={handleRemoveClick}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: "16px",
          height: "16px",
          borderRadius: "50%",
          border: "none",
          backgroundColor: "#455a74",
          color: "#e0e0e0",
          fontSize: "0.8rem",
          fontWeight: "bold",
          cursor: "pointer",
          padding: 0,
          lineHeight: 1,
        }}
      >
        ×
      </button>
    </div>
  );
};

export default IndicatorTag;
