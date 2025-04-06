import React, { useState, useEffect, useRef, useCallback } from "react";
import { fetchAllProductNames } from "../../services/api";

const AutoSuggestSearchBox = ({
  onSearch,
  productList = [],
  onProductsLoaded,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [isFocused, setIsFocused] = useState(false);
  const [isLoadingProducts, setIsLoadingProducts] = useState(false);
  const [localProductList, setLocalProductList] = useState(productList || []);
  const inputRef = useRef(null);
  const suggestionsRef = useRef(null);
  const initialMountRef = useRef(true);

  // Use supplied product list or local state
  const effectiveProductList =
    productList.length > 0 ? productList : localProductList;

  // Function to load product names - can be called on focus if needed
  const loadProductNames = useCallback(async () => {
    if (isLoadingProducts || effectiveProductList.length > 0) return;

    setIsLoadingProducts(true);
    try {
      const data = await fetchAllProductNames();
      if (data && Array.isArray(data.products)) {
        setLocalProductList(data.products);
        if (onProductsLoaded) {
          onProductsLoaded(data.products);
        }
      }
    } catch (error) {
      console.error("Failed to load product names on search focus:", error);
      // Silent fail, don't show error to user
    } finally {
      setIsLoadingProducts(false);
    }
  }, [isLoadingProducts, effectiveProductList.length, onProductsLoaded]);

  // Clear search results only on first mount, not on every render
  useEffect(() => {
    if (initialMountRef.current) {
      initialMountRef.current = false;
      // This will only run once after the initial render
      onSearch("");
    }
  }, []); // Empty dependency array to run only once

  // Handle outside clicks to close suggestions
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target) &&
        inputRef.current &&
        !inputRef.current.contains(event.target)
      ) {
        setIsFocused(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // Filter suggestions based on search term
  useEffect(() => {
    if (!searchTerm.trim() || !Array.isArray(effectiveProductList)) {
      setSuggestions([]);
      return;
    }

    const searchTermLower = searchTerm.toLowerCase();
    const filtered = effectiveProductList
      .filter(
        (product) =>
          product.name &&
          typeof product.name === "string" &&
          product.name.toLowerCase().includes(searchTermLower)
      )
      .slice(0, 10); // Limit to 10 suggestions

    setSuggestions(filtered);
  }, [searchTerm, effectiveProductList]);

  const handleSearch = () => {
    onSearch(searchTerm);
    setIsFocused(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setSearchTerm(suggestion.name);
    onSearch(suggestion.name);
    setIsFocused(false);
  };

  const handleFocus = () => {
    setIsFocused(true);
    // Try to load product names if we don't have any yet
    loadProductNames();
  };

  const highlightMatch = (text, query) => {
    if (!query.trim()) return text;

    try {
      const regex = new RegExp(
        `(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`,
        "gi"
      );
      return text.replace(regex, "<mark>$1</mark>");
    } catch (e) {
      return text;
    }
  };

  return (
    <div style={{ position: "relative" }}>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <input
          ref={inputRef}
          type="text"
          placeholder="Search products..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          onKeyPress={handleKeyPress}
          onFocus={handleFocus}
          style={{
            flexGrow: 1,
            padding: "0.6rem",
            borderRadius: "4px",
            border: "1px solid #444",
            backgroundColor: "#1e1e1e",
            color: "#e0e0e0",
          }}
        />
        <button
          onClick={handleSearch}
          style={{
            padding: "0.5rem 1rem",
            backgroundColor: "#2979ff",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
          }}
        >
          Search
        </button>
      </div>

      {isFocused && suggestions.length > 0 && (
        <div
          ref={suggestionsRef}
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            backgroundColor: "#1e1e1e",
            border: "1px solid #444",
            borderRadius: "0 0 4px 4px",
            zIndex: 10,
            maxHeight: "300px",
            overflowY: "auto",
            boxShadow: "0 4px 8px rgba(0,0,0,0.3)",
          }}
        >
          {suggestions.map((suggestion, index) => (
            <div
              key={suggestion.id || index}
              onClick={() => handleSuggestionClick(suggestion)}
              style={{
                padding: "0.75rem 1rem",
                borderBottom:
                  index < suggestions.length - 1 ? "1px solid #333" : "none",
                cursor: "pointer",
                backgroundColor: "#1e1e1e",
                color: "#e0e0e0",
                transition: "background-color 0.2s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "#2c2c2c";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "#1e1e1e";
              }}
              dangerouslySetInnerHTML={{
                __html: highlightMatch(suggestion.name, searchTerm),
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default AutoSuggestSearchBox;
