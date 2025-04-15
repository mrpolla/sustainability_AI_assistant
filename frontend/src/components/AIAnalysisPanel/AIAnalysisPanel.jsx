import React from "react";

/**
 * Component for displaying AI analysis results with colored bullet points
 */
const AIAnalysisPanel = ({ onAnalyse, loading, result, error, disabled }) => {
  // Format the text with colored bullet points in boxes
  const formatResult = (text) => {
    if (!text) return null;

    // Split by lines to process each bullet point
    const lines = text.split("\n");

    // Colors for bullet points and boxes (cycling through these)
    const colors = [
      { border: "#4caf50", bg: "#1e3026" }, // Green
      { border: "#ff9800", bg: "#332618" }, // Orange
      { border: "#03a9f4", bg: "#162630" }, // Blue
      { border: "#9c27b0", bg: "#261a2d" }, // Purple
      { border: "#2196f3", bg: "#182a3d" }, // Light Blue
      { border: "#ffc107", bg: "#332d15" }, // Yellow/Gold
    ];

    // Group content by bullet points
    const sections = [];
    let currentSection = null;
    let title = "";

    // First line might be a title
    if (
      lines.length > 0 &&
      !lines[0].trim().startsWith("-") &&
      lines[0].trim().length > 0
    ) {
      title = lines[0].trim();
    }

    // Process each line
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      // Skip empty lines
      if (!line) continue;

      // Skip the title line
      if (i === 0 && line === title) continue;

      // If it's a bullet point, start a new section
      if (line.startsWith("-")) {
        // If we already have a section in progress, save it
        if (currentSection) {
          sections.push(currentSection);
        }

        // Start a new section
        currentSection = {
          bullet: line.substring(0, 1),
          content: [line.substring(1).trim()],
        };
      }
      // If it's a regular line and we have a current section, add to it
      else if (currentSection) {
        currentSection.content.push(line);
      }
      // Otherwise, it's a standalone line not part of a bullet point
      else {
        sections.push({
          bullet: "",
          content: [line],
        });
      }
    }

    // Don't forget the last section
    if (currentSection) {
      sections.push(currentSection);
    }

    return (
      <div>
        {/* Title section if exists */}
        {title && (
          <div
            style={{
              marginBottom: "1rem",
              fontSize: "1.1rem",
              color: "#a9d5ff",
            }}
          >
            {title}
          </div>
        )}

        {/* Display each section in a box */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {sections.map((section, index) => {
            const color = colors[index % colors.length];

            return (
              <div
                key={index}
                style={{
                  padding: "0.8rem",
                  backgroundColor: color.bg,
                  borderRadius: "4px",
                  borderLeft: `3px solid ${color.border}`,
                  lineHeight: "1.5",
                }}
              >
                {section.content.map((line, lineIndex) => (
                  <div
                    key={lineIndex}
                    style={{
                      marginBottom:
                        lineIndex < section.content.length - 1 ? "0.5rem" : 0,
                    }}
                  >
                    {lineIndex === 0 && section.bullet && (
                      <span
                        style={{
                          color: color.border,
                          fontWeight: "bold",
                          marginRight: "0.5rem",
                        }}
                      >
                        {section.bullet}
                      </span>
                    )}
                    <span>
                      {/* Parse and render markdown-style bold text */}
                      {line.split(/(\*\*[^*]+\*\*)/).map((part, partIndex) => {
                        if (part.startsWith("**") && part.endsWith("**")) {
                          // This is bold text
                          return (
                            <span
                              key={partIndex}
                              style={{ fontWeight: "bold" }}
                            >
                              {part.substring(2, part.length - 2)}
                            </span>
                          );
                        } else {
                          // Regular text
                          return <span key={partIndex}>{part}</span>;
                        }
                      })}
                    </span>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div style={{ marginTop: "1.5rem" }}>
      <button
        onClick={onAnalyse}
        disabled={loading || disabled}
        style={{
          padding: "0.5rem 1rem",
          backgroundColor: "#4a5568",
          color: "#e0e0e0",
          border: "none",
          borderRadius: "4px",
          cursor: loading || disabled ? "not-allowed" : "pointer",
          fontSize: "0.9rem",
          opacity: loading || disabled ? 0.7 : 1,
        }}
      >
        {loading ? "Analysing..." : "Analyse results with AI"}
      </button>

      {/* Show loading indicator */}
      {loading && (
        <div style={{ marginTop: "1rem", color: "#90caf9" }}>
          Processing analysis, please wait...
        </div>
      )}

      {/* Show error message */}
      {error && (
        <div
          style={{
            marginTop: "1rem",
            padding: "1rem",
            backgroundColor: "#2d1e1e",
            borderRadius: "4px",
            border: "1px solid #f44336",
            color: "#f44336",
          }}
        >
          <strong>Analysis Error:</strong> {error}
        </div>
      )}

      {/* Show AI result */}
      {result && !loading && !error && (
        <div
          style={{
            marginTop: "1rem",
            padding: "1rem",
            backgroundColor: "#1e2a3a",
            borderRadius: "4px",
            border: "1px solid #4a5568",
            color: "#e0e0e0",
          }}
        >
          <h3 style={{ margin: "0 0 0.5rem 0", color: "#90caf9" }}>
            AI Analysis
          </h3>
          {formatResult(result)}
        </div>
      )}
    </div>
  );
};

export default AIAnalysisPanel;
