import React from "react";

const ResponseDisplay = ({ answer }) => {
  return (
    <div style={{ marginTop: "2rem" }}>
      <strong>Answer:</strong>
      <pre>{answer}</pre>
    </div>
  );
};

export default ResponseDisplay;
