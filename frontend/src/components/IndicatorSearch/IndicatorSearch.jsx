import React, { useState, useEffect, useRef, useCallback } from "react";

const IndicatorSearch = ({ indicatorList = [], onIndicatorSelect }) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef(null);
  const suggestionsRef = useRef(null);

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
    if (!searchTerm.trim() || !Array.isArray(indicatorList)) {
      setSuggestions([]);
      return;
    }

    const searchTermLower = searchTerm.toLowerCase();
    const filtered = indicatorList
      .filter(
        (indicator) =>
          (indicator.name &&
            typeof indicator.name === "string" &&
            indicator.name.toLowerCase().includes(searchTermLower)) ||
          (indicator.key &&
            typeof indicator.key === "string" &&
            indicator.key.toLowerCase().includes(searchTermLower))
      )
      .slice(0, 10); // Limit to 10 suggestions

    setSuggestions(filtered);
  }, [searchTerm, indicatorList]);

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && suggestions.length > 0) {
      handleSuggestionClick(suggestions[0]);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    if (onIndicatorSelect) {
      onIndicatorSelect(suggestion);
    }
    setSearchTerm("");
    setIsFocused(false);
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
      <input
        ref={inputRef}
        type="text"
        placeholder="Search indicators..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        onKeyPress={handleKeyPress}
        onFocus={() => setIsFocused(true)}
        style={{
          width: "100%",
          padding: "0.6rem",
          borderRadius: "4px",
          border: "1px solid #444",
          backgroundColor: "#1e1e1e",
          color: "#e0e0e0",
        }}
      />

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
              title={suggestion.short_description || ""}
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
                __html: highlightMatch(
                  `${suggestion.key} - ${suggestion.name}`,
                  searchTerm
                ),
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default IndicatorSearch;
