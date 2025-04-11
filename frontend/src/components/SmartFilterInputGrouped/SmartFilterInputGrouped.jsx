import React, { useState, useRef, useEffect } from "react";

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

const SmartFilterInputGrouped = ({
  label,
  value,
  onChange,
  groupedSuggestions,
}) => {
  const [inputValue, setInputValue] = useState(value || "");
  const [isFocused, setIsFocused] = useState(false);
  const containerRef = useRef(null);

  // Flatten and label suggestions
  const flatSuggestions = Object.entries(groupedSuggestions).flatMap(
    ([group, values]) => values.map((v) => ({ group, value: v }))
  );

  const filtered = flatSuggestions.filter((s) =>
    s.value.toLowerCase().includes(inputValue.toLowerCase())
  );

  const handleSelect = (val, group) => {
    setInputValue(val);
    onChange(val, group);
    setIsFocused(false);
  };

  // Close on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsFocused(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={containerRef} style={{ position: "relative", minWidth: "200px" }}>
      <label
        style={{
          display: "block",
          marginBottom: "0.2rem",
          color: "#ccc",
          fontSize: "0.85rem",
        }}
      >
        {label}
      </label>
      <input
        type="text"
        value={inputValue}
        onFocus={() => setIsFocused(true)}
        onChange={(e) => {
          setInputValue(e.target.value);
          onChange(e.target.value); // immediate filter feedback
        }}
        style={{
          width: "100%",
          padding: "0.5rem",
          borderRadius: "4px",
          border: "1px solid #444",
          backgroundColor: "#1e1e1e",
          color: "#eee",
        }}
      />
      {isFocused && filtered.length > 0 && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            zIndex: 100,
            backgroundColor: "#1e1e1e",
            border: "1px solid #444",
            maxHeight: "250px",
            overflowY: "auto",
            borderRadius: "0 0 4px 4px",
            boxShadow: "0 6px 10px rgba(0,0,0,0.5)",
          }}
        >
          {Object.entries(groupedSuggestions).map(([group, values]) => {
            const groupFiltered = values.filter((v) =>
              v.toLowerCase().includes(inputValue.toLowerCase())
            );
            if (groupFiltered.length === 0) return null;

            return (
              <div key={group}>
                <div
                  style={{
                    padding: "0.3rem 0.8rem",
                    fontSize: "0.75rem",
                    color: "#999",
                    fontStyle: "italic",
                    backgroundColor: "#111",
                    borderBottom: "1px solid #333",
                  }}
                >
                  ({group})
                </div>
                {groupFiltered.map((val) => (
                  <div
                    key={val}
                    onClick={() => handleSelect(val, group)}
                    style={{
                      padding: "0.6rem 0.8rem",
                      cursor: "pointer",
                      borderBottom: "1px solid #2a2a2a",
                      color: "#eee",
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.backgroundColor = "#2c2c2c")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.backgroundColor = "#1e1e1e")
                    }
                    dangerouslySetInnerHTML={{
                      __html: highlightMatch(val, inputValue),
                    }}
                  />
                ))}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default SmartFilterInputGrouped;
