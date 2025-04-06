import React from "react";

const ComparisonTable = ({
  indicator = {
    name: "Unnamed Indicator",
    unit: "",
    productData: [],
  },
  products = [],
}) => {
  // Safely extract modules from product data
  const getModules = () => {
    const allModules = indicator.productData.flatMap((productData) =>
      Object.keys(productData?.modules || {})
    );
    return [...new Set(allModules)].sort();
  };

  // Get product data for a specific product
  const getProductData = (productId) => {
    return (
      indicator.productData.find((data) => data.productId === productId) || {
        modules: {},
      }
    );
  };

  // Format numeric values
  const formatValue = (value) => {
    if (value == null) return "N/A";
    return typeof value === "number" ? value.toFixed(2) : value;
  };

  // Determine modules
  const modules = getModules();

  // Render nothing if no products
  if (products.length === 0) {
    return (
      <div className="text-gray-600 p-4 text-center">
        No products available for comparison
      </div>
    );
  }

  return (
    <div className="mb-8">
      <h3 className="text-xl font-semibold text-blue-600 mb-4">
        {indicator.name}
      </h3>

      <div className="overflow-x-auto rounded-lg shadow-lg">
        <table className="w-full border-separate border-spacing-0 text-sm bg-white text-gray-800">
          <thead>
            <tr>
              <th className="p-3 text-left border border-gray-200 bg-blue-50 font-semibold">
                Product
              </th>
              <th className="p-3 text-left border border-gray-200 bg-blue-50 font-semibold">
                Unit
              </th>
              {modules.map((module) => (
                <th
                  key={module}
                  className="p-3 text-right border border-gray-200 bg-blue-50 font-semibold"
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
                  className={`${
                    index % 2 ? "bg-gray-50" : "bg-white"
                  } hover:bg-blue-100 transition-colors`}
                >
                  <td className="p-3 border border-gray-200 max-w-[200px] truncate">
                    {product.name}
                  </td>
                  <td className="p-3 border border-gray-200">
                    {indicator.unit || "N/A"}
                  </td>
                  {modules.map((module) => (
                    <td
                      key={module}
                      className={`p-3 text-right border border-gray-200 
                        ${
                          productData.modules[module]
                            ? ""
                            : "bg-gray-100 text-gray-500"
                        }`}
                    >
                      {formatValue(productData.modules[module])}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ComparisonTable;
