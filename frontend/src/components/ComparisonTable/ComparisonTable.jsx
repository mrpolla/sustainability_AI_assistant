import React from "react";

/**
 * Normalizes unit names to a consistent format
 * @param {string} unit - The unit to normalize
 * @returns {string} - The normalized unit
 */
const normalizeUnit = (unit) => {
  if (unit == null) {
    return "-";
  }

  if (typeof unit !== "string") {
    return String(unit);
  }

  // Handle NULL values
  if (unit.toUpperCase() === "NULL" || unit.trim() === "") {
    return "-";
  }

  unit = unit.trim().toLowerCase();

  // Define regex patterns and their standardized forms
  const mappings = {
    // Volume units
    "^m[\\^³]?[3]?$": "m³",
    "^m\\s*[3³]$": "m³",
    "^m\\^3$": "m³",
    "^m³.*$": "m³",

    // Carbon dioxide equivalents
    "^kg.*co.*?2.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "kg CO₂ eq",
    "^kg.*co.*?\\(?2\\)?.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "kg CO₂ eq",
    "^kg.*co_?\\(?2\\)?[- ]?äq\\.?$": "kg CO₂ eq",
    "^kg\\s*co_?\\(?2\\)?(?:\\s|-|_).*$": "kg CO₂ eq",

    // CFC equivalents
    "^kg.*(?:cfc|r)\\s*11.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "kg CFC-11 eq",
    "^kg.*(?:cfc|r)11.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "kg CFC-11 eq",
    "^kg\\s*cfc-11\\s*eq\\.?$": "kg CFC-11 eq",

    // Phosphorus equivalents
    "^kg.*p(?:[ -]?eq|\\s?äq|\\s?aeq|\\s?äqv|\\s?eqv|[- ]?äquiv|\\s?equivalent).*$":
      "kg P eq",
    "^kg.*p[- ]?äq.*$": "kg P eq",
    "^kg.*phosphat.*$": "kg PO₄ eq",

    // NMVOC equivalents
    "^kg.*n.*mvoc.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "kg NMVOC eq",
    "^kg.*nmvoc.*$": "kg NMVOC eq",

    // Ethene/Ethylene equivalents
    "^kg.*(?:ethen|ethene|ethylen).*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "kg C₂H₂ eq",
    "^kg.*(?:ethen|ethene|ethylen)[- ]?äq.*$": "kg C₂H₂ eq",
    "^kg.*c2h[24].*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "kg C₂H₂ eq",

    // Antimony equivalents
    "^kg.*sb.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$": "kg Sb eq",

    // Sulfur dioxide equivalents
    "^kg.*so.*?2.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "kg SO₂ eq",
    "^kg.*so_?\\(?2\\)?.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "kg SO₂ eq",

    // Phosphate equivalents
    "^kg.*po.*?4.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "kg PO₄ eq",
    "^kg.*po_?\\(?4\\)?.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "kg PO₄ eq",
    "^kg.*po.*\\(?3-?\\)?.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "kg PO₄ eq",
    "^kg.*\\(po4\\)3-.*$": "kg PO₄ eq",
    "^kg.*phosphate.*$": "kg PO₄ eq",

    // Nitrogen equivalents
    "^kg.*n.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$": "kg N eq",
    "^mol.*n.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$": "mol N eq",
    "^mole.*n.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$": "mol N eq",

    // Hydrogen ion equivalents
    "^mol.*h.*[\\+\\^].*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "mol H⁺ eq",
    "^mole.*h.*[\\+\\^].*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "mol H⁺ eq",
    "^mol.*h.*[-\\+](?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "mol H⁺ eq",

    // Uranium equivalents
    "^k?bq.*u235.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*$":
      "kBq U235 eq",

    // World water equivalents
    "^m.*?3.*world.*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*(?:deprived|entzogen)?$":
      "m³ world eq deprived",
    "^m\\^?\\(?3\\)?.*w(?:orld|elt).*(?:eq|äq|aeq|äqv|eqv|[- ]?äquiv|\\s?equivalent).*(?:deprived|entzogen)$":
      "m³ world eq deprived",

    // Disease incidence
    "^disease\\s*incidence$": "disease incidence",
    "^krankheitsfälle$": "disease incidence",

    // Other specific units
    "^ctuh$": "CTUh",
    "^ctue$": "CTUe",
    "^sqp$": "SQP",
    "^dimensionless$": "dimensionless",

    // Simple units
    "^-?$": "-",
    "^mj$": "MJ",
    "^kg$": "kg",

    // Per unit conversions
    "^kg\\/pce$": "kg/pce",
    "^kg\\s*\\/\\s*pce$": "kg/pce",

    // Compound units with divisions or per - volume-based
    "^kg\\s*\\/\\s*m[\\^]?3$": "kg/m³",
    "^kg\\s*\\/\\s*m3$": "kg/m³",
    "^kg\\s*per\\s*m3$": "kg/m³",
    "^kg\\s*per\\s*m[\\^]?3$": "kg/m³",

    // Compound units with divisions or per - area-based
    "^kg\\s*\\/\\s*m[\\^]?2$": "kg/m²",
    "^kg\\s*\\/\\s*m2$": "kg/m²",
    "^kg\\s*per\\s*m2$": "kg/m²",
    "^kg\\s*per\\s*m[\\^]?2$": "kg/m²",
  };

  // Check unit against each pattern
  for (const [pattern, standard] of Object.entries(mappings)) {
    if (new RegExp(pattern).test(unit)) {
      return standard;
    }
  }

  // If no match found, return the original unit
  return unit;
};

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

  // Normalize the indicator unit
  const normalizedUnit = normalizeUnit(indicator.unit);

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
                    {normalizedUnit || "N/A"}
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
            {/* New spanning footer row */}
            <tr
              style={{
                ...footerRowStyle,
                height: "20px", // Half the height of normal rows
                backgroundColor: "#0d47a1",
              }}
            >
              <td
                colSpan={modules.length + 2}
                style={{
                  padding: "0.375rem",
                  border: "2px solid #90caf9",
                  fontSize: "0.8rem",
                  fontStyle: "italic",
                }}
              >
                Statistics across category: {indicator.category}
              </td>
            </tr>
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
          Indicator: <strong>{indicator.key}</strong> &middot; Unit:{" "}
          <strong>{normalizedUnit}</strong>
        </p>
      </div>
    </div>
  );
};

export default ComparisonTable;
