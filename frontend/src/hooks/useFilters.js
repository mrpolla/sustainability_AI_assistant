import { useState, useEffect } from "react";
import { fetchFilters } from "../services/api";

const useFilters = () => {
  const [availableFilters, setAvailableFilters] = useState({
    category_level_1: [],
    category_level_2: [],
    category_level_3: [],
    use_cases: [],
    materials: [],
  });

  const [selectedFilters, setSelectedFilters] = useState({
    category_level_1: "",
    category_level_2: "",
    category_level_3: "",
    use_case: "",
    material: "",
  });

  const loadFilters = async () => {
    try {
      const data = await fetchFilters();
      setAvailableFilters(data);
    } catch (error) {
      console.error("Failed to fetch filters:", error);
    }
  };

  const updateFilter = (key, value) => {
    setSelectedFilters((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const resetFilters = () => {
    setSelectedFilters({
      category_level_1: "",
      category_level_2: "",
      category_level_3: "",
      use_case: "",
      material: "",
    });
  };

  return {
    availableFilters,
    selectedFilters,
    updateFilter,
    resetFilters,
    loadFilters,
  };
};

export default useFilters;
