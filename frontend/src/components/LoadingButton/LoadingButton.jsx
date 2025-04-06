import React from "react";

const LoadingButton = ({ onClick, loading, text, loadingText }) => {
  return (
    <button onClick={onClick} disabled={loading}>
      {loading ? loadingText : text}
    </button>
  );
};

export default LoadingButton;
