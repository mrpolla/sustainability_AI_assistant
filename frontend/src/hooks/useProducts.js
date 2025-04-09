import { useState, useCallback } from "react";
import { fetchAllProductNames, searchProducts } from "../services/api";

/**
 * Hook for managing product data and search functionality
 */
const useProducts = (setConnectionStatus) => {
  // State for products
  const [allProducts, setAllProducts] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [productLoadingError, setProductLoadingError] = useState("");
  const [productLoading, setProductLoading] = useState(false);

  // Load product data
  const loadProducts = useCallback(async () => {
    setProductLoading(true);
    setProductLoadingError("");

    try {
      const productsData = await fetchAllProductNames();

      if (!productsData) {
        throw new Error("No data returned from product name request");
      }

      if (productsData.products && Array.isArray(productsData.products)) {
        setAllProducts(productsData.products);
      } else {
        setAllProducts([]);
      }
    } catch (error) {
      console.error("Failed to load product names:", error);
      setProductLoadingError(
        `Failed to load products: ${error.message || "Unknown error"}`
      );
      setAllProducts([]);
    } finally {
      setProductLoading(false);
    }
  }, []);

  // Handle products loaded callback
  const handleProductsLoaded = useCallback((products) => {
    if (Array.isArray(products)) {
      setAllProducts(products);
      setProductLoadingError("");
    } else {
      console.error("Invalid products data format:", products);
      setProductLoadingError("Received invalid product data");
    }
  }, []);

  // Handle search functionality
  const handleSearch = useCallback(
    async (searchTerm) => {
      const trimmedSearchTerm = searchTerm?.trim() || "";

      if (!trimmedSearchTerm) {
        setSearchResults([]);
        setSearchError("");
        return;
      }

      setSearchLoading(true);
      setSearchError("");

      try {
        const data = await searchProducts(trimmedSearchTerm);

        if (!data) {
          throw new Error("No data returned from search request");
        }

        if (data.items && Array.isArray(data.items)) {
          setSearchResults(data.items);

          if (data.items.length === 0) {
            setSearchError(`No products found matching "${trimmedSearchTerm}"`);
          }
        } else {
          setSearchResults([]);
          setSearchError("Received invalid data format from server");
        }
      } catch (error) {
        console.error("Search failed:", error);
        setSearchError(error.message || "Unknown error");
        setSearchResults([]);

        if (
          error.message?.includes("connect to the server") ||
          error.message?.includes("timed out")
        ) {
          setConnectionStatus("disconnected");
        }
      } finally {
        setSearchLoading(false);
      }
    },
    [setConnectionStatus]
  );

  // Handle item selection in the checkable list
  const handleItemToggle = useCallback((itemId) => {
    if (itemId === undefined || itemId === null) return;

    setSelectedItems((prev) =>
      prev.includes(itemId)
        ? prev.filter((id) => id !== itemId)
        : [...prev, itemId]
    );
  }, []);

  return {
    allProducts,
    searchResults,
    selectedItems,
    searchLoading,
    searchError,
    productLoadingError,
    productLoading,
    loadProducts,
    handleProductsLoaded,
    handleSearch,
    handleItemToggle,
    setSelectedItems,
  };
};

export default useProducts;
