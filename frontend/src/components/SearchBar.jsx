import React, { useRef, useEffect } from 'react';

export default function SearchBar({ value, onChange, placeholder = 'Search videos...' }) {
  const timerRef = useRef(null);

  function handleChange(e) {
    const val = e.target.value;
    // Debounce 300ms
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      onChange(val);
    }, 300);
  }

  useEffect(() => {
    return () => clearTimeout(timerRef.current);
  }, []);

  return (
    <div className="search-bar">
      <span className="search-bar-icon">&#128269;</span>
      <input
        type="text"
        defaultValue={value}
        onChange={handleChange}
        placeholder={placeholder}
      />
    </div>
  );
}
