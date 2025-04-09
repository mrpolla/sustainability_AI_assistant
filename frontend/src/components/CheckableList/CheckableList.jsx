import React from "react";

const CheckableList = ({ items, selectedItems, onItemToggle, disabled }) => {
  if (!items || items.length === 0) {
    return (
      <div
        style={{
          padding: "1rem",
          backgroundColor: "#1e1e1e",
          borderRadius: "4px",
          border: "1px solid #333",
          color: "#aaa",
          fontSize: "0.9rem",
        }}
      >
        No items found. Try a different search term.
      </div>
    );
  }

  return (
    <div
      style={{
        maxHeight: "300px",
        overflowY: "auto",
        border: "1px solid #333",
        borderRadius: "4px",
        backgroundColor: "#1e1e1e",
      }}
    >
      {items.map((item) => {
        const isSelected = selectedItems.includes(item.process_id);

        // Use name or fallback
        const displayName =
          item.name_en || item.name_en_ai || "Unnamed Product";

        // Get short description
        const shortDesc = item.short_description_ai || "";

        // Get category path (either pre-formatted or build from parts)
        const categoryPath =
          item.category_path ||
          [item.category_level_1, item.category_level_2, item.category_level_3]
            .filter(Boolean)
            .join(" > ");

        return (
          <div
            key={item.process_id}
            style={{
              padding: "0.8rem",
              borderBottom: "1px solid #333",
              display: "flex",
              backgroundColor: isSelected ? "#2c3e50" : "transparent",
              opacity: disabled ? 0.6 : 1,
              transition: "background-color 0.2s ease",
            }}
          >
            <div style={{ marginRight: "1rem" }}>
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => onItemToggle(item.process_id)}
                disabled={disabled}
                style={{
                  cursor: disabled ? "not-allowed" : "pointer",
                }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: "500", color: "#e0e0e0" }}>
                {displayName}
              </div>

              {shortDesc && (
                <div
                  style={{
                    fontSize: "0.9rem",
                    color: "#bbb",
                    marginTop: "0.3rem",
                  }}
                >
                  {shortDesc}
                </div>
              )}

              {categoryPath && (
                <div
                  style={{
                    fontSize: "0.8rem",
                    color: "#777",
                    marginTop: "0.3rem",
                    fontStyle: "italic",
                  }}
                >
                  {categoryPath}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default CheckableList;
