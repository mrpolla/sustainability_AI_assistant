import React from "react";
import CheckableList from "../../components/CheckableList";

/**
 * Component for product selection functionality
 */
const ProductSelection = ({
  items,
  selectedItems,
  onItemToggle,
  searchLoading,
  disabled,
}) => {
  return (
    <div>
      <h3>
        Select Products ({items.length} results found)
        {searchLoading && (
          <span
            style={{
              marginLeft: "1rem",
              fontSize: "0.9rem",
              color: "#666",
            }}
          >
            Loading...
          </span>
        )}
      </h3>
      <CheckableList
        items={items}
        selectedItems={selectedItems}
        onItemToggle={onItemToggle}
        disabled={disabled}
      />
      {selectedItems.length > 0 && (
        <div
          style={{
            fontSize: "0.9rem",
            color: "#999",
            marginTop: "-1rem",
            marginBottom: "1rem",
          }}
        >
          {selectedItems.length} product
          {selectedItems.length !== 1 ? "s" : ""} selected
        </div>
      )}
    </div>
  );
};

export default ProductSelection;
