import React from "react";

const Header = () => {
  return (
    <div
      style={{
        marginBottom: "1.5rem",
        borderBottom: "1px solid #333",
        paddingBottom: "1rem",
      }}
    >
      <h1
        style={{
          color: "#90caf9",
          margin: "0 0 0.5rem 0",
          fontSize: "1.8rem",
        }}
      >
        EPD RAG Assistant
      </h1>
      <p
        style={{
          color: "#aaa",
          margin: 0,
          fontSize: "0.9rem",
        }}
      >
        Search and ask questions about Environmental Product Declarations
      </p>
    </div>
  );
};

export default Header;
