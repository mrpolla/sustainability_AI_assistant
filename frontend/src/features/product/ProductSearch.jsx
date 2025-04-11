import React, { useState, useEffect } from "react";
import useFilters from "../../hooks/useFilters";
import SmartFilterInputGrouped from "../../components/SmartFilterInputGrouped";
import SmartFilterInput from "../../components/SmartFilterInput";

/**
 * Component for product search functionality
 */
const ProductSearch = ({
  onSearch,
  searchError,
  productLoading,
  productLoadingError,
  disabled,
}) => {
  const { availableFilters, selectedFilters, updateFilter, loadFilters } =
    useFilters();

  // Load filter options once on mount
  useEffect(() => {
    loadFilters();
  }, []);

  const handleSearchClick = () => {
    onSearch(selectedFilters);
  };

  return (
    <div style={{ marginBottom: "1rem" }}>
      <h3 style={{ marginBottom: "1rem" }}>Search Products</h3>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          columnGap: "2rem",
          rowGap: "1rem",
          marginBottom: "1.25rem",
          alignItems: "flex-start",
        }}
      >
        <SmartFilterInputGrouped
          label="Category"
          value={
            selectedFilters.category_level_1 ||
            selectedFilters.category_level_2 ||
            selectedFilters.category_level_3 ||
            ""
          }
          onChange={(val, group) => {
            if (group === "Category Level 1")
              updateFilter("category_level_1", val);
            else if (group === "Category Level 2")
              updateFilter("category_level_2", val);
            else if (group === "Category Level 3")
              updateFilter("category_level_3", val);
          }}
          groupedSuggestions={{
            "Category Level 1": availableFilters.category_level_1,
            "Category Level 2": availableFilters.category_level_2,
            "Category Level 3": availableFilters.category_level_3,
          }}
        />

        <SmartFilterInput
          label="Use Case"
          value={selectedFilters.use_case}
          onChange={(val) => updateFilter("use_case", val)}
          suggestions={availableFilters.use_cases}
        />

        <SmartFilterInput
          label="Material"
          value={selectedFilters.material}
          onChange={(val) => updateFilter("material", val)}
          suggestions={availableFilters.materials}
        />

        <SmartFilterInput
          label="Product Name"
          value={selectedFilters.product_name}
          onChange={(val) => updateFilter("product_name", val)}
          suggestions={[]}
        />
      </div>

      <button
        onClick={handleSearchClick}
        disabled={disabled}
        style={{
          padding: "0.6rem 1.2rem",
          fontSize: "1rem",
          borderRadius: "4px",
          border: "none",
          backgroundColor: "#1976d2",
          color: "#fff",
          cursor: "pointer",
          marginBottom: "1.25rem",
        }}
      >
        Search
      </button>

      {productLoading && (
        <div style={{ marginTop: "0.5rem", color: "#90caf9" }}>
          Loading product list...
        </div>
      )}

      {productLoadingError && (
        <div
          style={{
            color: "#d32f2f",
            fontSize: "0.85rem",
            marginTop: "0.3rem",
            padding: "0.3rem",
            backgroundColor: "rgba(211, 47, 47, 0.1)",
            borderRadius: "4px",
          }}
        >
          {productLoadingError}
        </div>
      )}

      {searchError && (
        <div
          style={{
            color: "#d32f2f",
            marginTop: "0.5rem",
            padding: "0.5rem",
            border: "1px solid #ffcdd2",
            borderRadius: "4px",
            backgroundColor: "#fff0f0",
          }}
        >
          {searchError}
        </div>
      )}
    </div>
  );
};

export default ProductSearch;
