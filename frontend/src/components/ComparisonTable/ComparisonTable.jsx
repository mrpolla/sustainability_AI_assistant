import React from "react";

const ComparisonTable = ({
  indicator = {
    name: "Unnamed Indicator",
    unit: "",
    productData: [],
  },
  products = [],
  allIndicators = [],
}) => {
  console.log("🔍 indicator.key:", indicator.key);
  console.log(
    "📦 allIndicators keys:",
    allIndicators.map((i) => i.key)
  );
  const enriched = allIndicators.find((i) => i.key === indicator.key) || {};
  const displayName = `${indicator.key} – ${enriched.name || "Unknown"}`;
  const tooltip = enriched.short_description || "";
  const longDescription = enriched.long_description || "";

  const getModules = () => {
    const allModules = indicator.productData.flatMap((productData) =>
      Object.keys(productData?.modules || {})
    );
    return [...new Set(allModules)].sort();
  };

  const getProductData = (productId) => {
    return (
      indicator.productData.find((data) => data.productId === productId) || {
        modules: {},
      }
    );
  };

  const formatValue = (value) => {
    if (value == null) return "N/A";
    return typeof value === "number" ? value.toFixed(2) : value;
  };

  const footerRowStyle = {
    backgroundColor: "#1e1e1e",
    color: "#90caf9",
    fontWeight: 600,
  };

  const footerCellStyle = {
    padding: "0.75rem",
    textAlign: "right",
    border: "2px solid #90caf9",
  };

  const footerLabelStyle = {
    padding: "0.75rem",
    textAlign: "left",
    border: "2px solid #90caf9",
    backgroundColor: "#1e1e1e",
    color: "#90caf9",
    fontWeight: 600,
  };

  const modules = getModules();

  if (products.length === 0) {
    return (
      <div style={{ color: "#aaa", padding: "1rem", textAlign: "center" }}>
        No products available for comparison
      </div>
    );
  }
  console.log("🧩 Indicator Data:", indicator);
  return (
    <div style={{ marginBottom: "2rem" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          marginBottom: "1rem",
        }}
      >
        <h3
          style={{
            fontSize: "1.25rem",
            fontWeight: 600,
            color: "#90caf9",
            margin: 0,
          }}
        >
          {displayName}
        </h3>
        <div
          style={{
            position: "relative",
            display: "inline-block",
          }}
          onMouseEnter={(e) => {
            const tooltip = e.currentTarget.querySelector(".tooltip-content");
            if (tooltip) {
              tooltip.style.opacity = "1";
              tooltip.style.visibility = "visible";
            }
          }}
          onMouseLeave={(e) => {
            const tooltip = e.currentTarget.querySelector(".tooltip-content");
            if (tooltip) {
              tooltip.style.opacity = "0";
              tooltip.style.visibility = "hidden";
            }
          }}
        >
          <div
            style={{
              cursor: "help",
              backgroundColor: "#1976d2",
              color: "white",
              fontSize: "0.75rem",
              fontWeight: "bold",
              borderRadius: "50%",
              width: "18px",
              height: "18px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
              position: "relative",
            }}
          >
            i
            <div
              className="tooltip-content"
              style={{
                position: "absolute",
                top: "140%",
                left: "50%",
                transform: "translateX(-50%)",
                backgroundColor: "#1e1e1e",
                color: "#e0e0e0",
                padding: "1rem",
                border: "1px solid #90caf9",
                borderRadius: "6px",
                maxWidth: "500px",
                width: "max-content",
                zIndex: 10,
                transition: "opacity 0.2s ease-in-out",
                whiteSpace: "normal",
                fontSize: "0.85rem",
                opacity: 0,
                visibility: "hidden",
                textAlign: "left",
              }}
            >
              <strong style={{ color: "#90caf9" }}>{tooltip}</strong>
              <div style={{ marginTop: "0.5rem" }}>{longDescription}</div>
            </div>
          </div>
        </div>
      </div>

      <div
        style={{
          overflowX: "auto",
          borderRadius: "8px",
          boxShadow: "0 4px 6px rgba(0, 0, 0, 0.3)",
        }}
      >
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "0.875rem",
          }}
        >
          <thead>
            <tr>
              <th
                style={{
                  padding: "0.75rem",
                  textAlign: "left",
                  backgroundColor: "#1976d2",
                  color: "white",
                  fontWeight: 600,
                  border: "2px solid #90caf9",
                }}
              >
                Product
              </th>
              <th
                style={{
                  padding: "0.75rem",
                  textAlign: "left",
                  backgroundColor: "#1976d2",
                  color: "white",
                  fontWeight: 600,
                  border: "2px solid #90caf9",
                }}
              >
                Unit
              </th>
              {modules.map((module) => (
                <th
                  key={module}
                  style={{
                    padding: "0.75rem",
                    textAlign: "right",
                    backgroundColor: "#1976d2",
                    color: "white",
                    fontWeight: 600,
                    border: "2px solid #90caf9",
                  }}
                >
                  {module}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {products.map((product, index) => {
              const productData = getProductData(product.id);

              return (
                <tr
                  key={product.id}
                  style={{
                    backgroundColor: index % 2 ? "#424242" : "#303030",
                    color: "white",
                    transition: "background-color 0.2s",
                  }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.backgroundColor = "#1e4976")
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.backgroundColor =
                      index % 2 ? "#424242" : "#303030")
                  }
                >
                  <td
                    style={{
                      padding: "0.75rem",
                      border: "2px solid #90caf9",
                      maxWidth: "200px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {product.name}
                  </td>
                  <td
                    style={{
                      padding: "0.75rem",
                      border: "2px solid #90caf9",
                    }}
                  >
                    {indicator.unit || "N/A"}
                  </td>
                  {modules.map((module) => (
                    <td
                      key={module}
                      style={{
                        padding: "0.75rem",
                        textAlign: "right",
                        border: "2px solid #90caf9",
                        backgroundColor: productData.modules[module]
                          ? ""
                          : "#1e1e1e",
                        color: productData.modules[module] ? "white" : "#777",
                      }}
                    >
                      {formatValue(productData.modules[module])}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr style={footerRowStyle}>
              <td style={footerLabelStyle}>Mean</td>
              <td style={footerCellStyle}></td>
              {modules.map((module) => (
                <td key={`mean-${module}`} style={footerCellStyle}>
                  {formatValue(indicator?.stats?.[module]?.mean)}
                </td>
              ))}
            </tr>
            <tr style={footerRowStyle}>
              <td style={footerLabelStyle}>Min</td>
              <td style={footerCellStyle}></td>
              {modules.map((module) => (
                <td key={`min-${module}`} style={footerCellStyle}>
                  {formatValue(indicator?.stats?.[module]?.min)}
                </td>
              ))}
            </tr>
            <tr style={footerRowStyle}>
              <td style={footerLabelStyle}>Max</td>
              <td style={footerCellStyle}></td>
              {modules.map((module) => (
                <td key={`max-${module}`} style={footerCellStyle}>
                  {formatValue(indicator?.stats?.[module]?.max)}
                </td>
              ))}
            </tr>
          </tfoot>
        </table>
        <p style={{ color: "#90caf9", fontSize: "0.9rem", marginTop: "1rem" }}>
          Category statistics for <strong>{indicator.category}</strong> &middot;
          Indicator: <strong>{indicator.key}</strong>
        </p>
      </div>
    </div>
  );
};

export default ComparisonTable;
