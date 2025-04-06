import React, { useState } from "react";

const SearchBox = ({ onSearch }) => {
  const [searchTerm, setSearchTerm] = useState("");

  const handleSearch = () => {
    if (searchTerm.trim()) {
      onSearch(searchTerm);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  return (
    <div style={{ marginBottom: "1rem" }}>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <input
          type="text"
          placeholder="Search..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          onKeyPress={handleKeyPress}
          style={{ flexGrow: 1, padding: "0.5rem" }}
        />
        <button onClick={handleSearch} style={{ padding: "0.5rem 1rem" }}>
          Search
        </button>
      </div>
    </div>
  );
};

export default SearchBox;
