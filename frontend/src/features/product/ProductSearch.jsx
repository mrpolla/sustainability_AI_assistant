import React from "react";
import AutoSuggestSearchBox from "../../components/AutoSuggestSearchBox";

/**
 * Component for product search functionality
 */
const ProductSearch = ({
  onSearch,
  productList,
  onProductsLoaded,
  searchError,
  productLoading,
  productLoadingError,
  disabled,
}) => {
  return (
    <div style={{ marginTop: "1.5rem", marginBottom: "1rem" }}>
      <h3>Search Products</h3>
      <AutoSuggestSearchBox
        onSearch={onSearch}
        productList={productList}
        onProductsLoaded={onProductsLoaded}
        disabled={disabled}
      />
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
