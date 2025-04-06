import React from "react";

const CheckableList = ({ items, selectedItems, onItemToggle }) => {
  // Safely handle invalid inputs
  const safeItems = Array.isArray(items) ? items : [];
  const safeSelectedItems = Array.isArray(selectedItems) ? selectedItems : [];

  return (
    <div
      style={{
        border: "1px solid #444",
        borderRadius: "4px",
        height: "250px",
        overflowY: "scroll",
        marginBottom: "1.5rem",
        backgroundColor: "#1e1e1e",
      }}
    >
      {safeItems.length === 0 ? (
        <div style={{ padding: "1rem", color: "#aaa", textAlign: "center" }}>
          <p style={{ margin: 0 }}>Type in the search box to find products</p>
        </div>
      ) : (
        <ul style={{ listStyle: "none", padding: "0", margin: "0" }}>
          {safeItems.map((item) => {
            // Ensure item has valid id and name properties
            const id = item?.id || "";
            const name = item?.name || "Unnamed product";
            const description = item?.description || "";

            return (
              <li
                key={id}
                style={{
                  padding: "0.75rem 1rem",
                  borderBottom: "1px solid #333",
                  backgroundColor: safeSelectedItems.includes(id)
                    ? "#2c3b4c"
                    : "#1e1e1e",
                  transition: "background-color 0.2s",
                }}
              >
                <label
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    cursor: "pointer",
                    width: "100%",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={safeSelectedItems.includes(id)}
                    onChange={() => onItemToggle(id)}
                    style={{
                      marginRight: "0.75rem",
                      marginTop: "0.25rem",
                      flexShrink: 0,
                    }}
                  />
                  <div style={{ overflow: "hidden" }}>
                    <div
                      style={{
                        fontWeight: safeSelectedItems.includes(id)
                          ? "500"
                          : "normal",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        color: safeSelectedItems.includes(id)
                          ? "#90caf9"
                          : "#e0e0e0",
                      }}
                    >
                      {name}
                    </div>
                    {description && (
                      <div
                        style={{
                          fontSize: "0.85rem",
                          color: "#999",
                          marginTop: "0.25rem",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          display: "-webkit-box",
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: "vertical",
                        }}
                      >
                        {description}
                      </div>
                    )}
                    <div
                      style={{
                        fontSize: "0.75rem",
                        color: "#777",
                        marginTop: "0.25rem",
                      }}
                    >
                      ID: {id}
                    </div>
                  </div>
                </label>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};

export default CheckableList;
