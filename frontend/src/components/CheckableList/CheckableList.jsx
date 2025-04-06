import React from "react";

const CheckableList = ({ items, selectedItems, onItemToggle }) => {
  return (
    <div
      style={{
        border: "1px solid #ccc",
        borderRadius: "4px",
        maxHeight: "200px",
        overflowY: "auto",
        marginBottom: "1.5rem",
      }}
    >
      {items.length === 0 ? (
        <p style={{ padding: "0.5rem", color: "#666", textAlign: "center" }}>
          No items to display
        </p>
      ) : (
        <ul style={{ listStyle: "none", padding: "0", margin: "0" }}>
          {items.map((item) => (
            <li
              key={item.id}
              style={{
                padding: "0.5rem",
                borderBottom: "1px solid #eee",
                backgroundColor: selectedItems.includes(item.id)
                  ? "#f0f7ff"
                  : "transparent",
              }}
            >
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedItems.includes(item.id)}
                  onChange={() => onItemToggle(item.id)}
                  style={{ marginRight: "0.5rem" }}
                />
                {item.name}
              </label>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default CheckableList;
