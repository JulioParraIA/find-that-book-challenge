import { useState, useCallback } from "react";

const EXAMPLE_QUERIES = [
  "dickens tale two cities",
  "tolkien hobbit illustrated deluxe 1937",
  "mark huckleberry",
  "austen bennet pride",
  "orwell animal political allegory",
];

function SearchBar({ onSearch, isLoading }) {
  const [query, setQuery] = useState("");

  const handleSubmit = useCallback(() => {
    const trimmed = query.trim();
    if (trimmed.length === 0) return;
    onSearch(trimmed);
  }, [query, onSearch]);

  const handleKeyDown = useCallback((event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  return (
    <div>
      <div className="relative">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          placeholder="Describe the book you are looking for..."
          rows={3}
          maxLength={500}
          className="w-full px-4 py-3 rounded-lg resize-none bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 text-sm leading-relaxed transition-colors duration-150 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Book search query"
        />
        <span className="absolute bottom-2 right-3 text-xs text-slate-600">{query.length}/500</span>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <p className="text-xs text-slate-600">Press Ctrl+Enter to search</p>
        <button
          onClick={handleSubmit}
          disabled={isLoading || query.trim().length === 0}
          className="px-6 py-2 rounded-lg text-sm font-medium transition-all duration-150 bg-blue-600 text-white hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed"
        >
          {isLoading ? "Searching..." : "Search"}
        </button>
      </div>

      <div className="mt-4">
        <p className="text-xs text-slate-600 mb-2">Try an example:</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_QUERIES.map((example, i) => (
            <button key={i} onClick={() => setQuery(example)} disabled={isLoading}
              className="px-3 py-1 rounded-full text-xs bg-slate-800 border border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-300 transition-colors duration-150 disabled:opacity-50">
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default SearchBar;
