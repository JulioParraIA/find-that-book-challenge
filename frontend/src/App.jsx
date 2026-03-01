import { useState, useCallback } from "react";
import { searchBooks, ApiError } from "./services/api.js";
import SearchBar from "./components/SearchBar.jsx";
import ResultsList from "./components/ResultsList.jsx";
import LoadingState from "./components/LoadingState.jsx";

function App() {
  const [candidates, setCandidates] = useState([]);
  const [extractedFields, setExtractedFields] = useState(null);
  const [totalResults, setTotalResults] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = useCallback(async (query) => {
    setError(null);
    setCandidates([]);
    setExtractedFields(null);
    setTotalResults(0);
    setIsLoading(true);
    setHasSearched(true);

    try {
      const response = await searchBooks(query);
      setCandidates(response.candidates || []);
      setExtractedFields(response.extracted_fields || null);
      setTotalResults(response.total_results || 0);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "An unexpected error occurred.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <div className="min-h-screen bg-slate-900">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Find That Book</h1>
          <p className="mt-1 text-sm text-slate-400">Enter a messy description, title, author, or keywords.</p>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <SearchBar onSearch={handleSearch} isLoading={isLoading} />

        {extractedFields && !isLoading && (
          <div className="mt-6 p-4 bg-slate-800/50 border border-slate-700 rounded-lg">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Interpreted Query</p>
            <div className="flex flex-wrap gap-3 text-sm">
              {extractedFields.title && <span className="px-3 py-1 bg-blue-900/40 text-blue-300 border border-blue-800 rounded-full">Title: {extractedFields.title}</span>}
              {extractedFields.author && <span className="px-3 py-1 bg-green-900/40 text-green-300 border border-green-800 rounded-full">Author: {extractedFields.author}</span>}
              {extractedFields.keywords?.map((kw, i) => <span key={i} className="px-3 py-1 bg-slate-700/50 text-slate-300 border border-slate-600 rounded-full">{kw}</span>)}
            </div>
          </div>
        )}

        {error && (
          <div className="mt-6 p-4 bg-red-900/20 border border-red-800 rounded-lg text-red-300 text-sm" role="alert">
            <p className="font-medium">Search failed</p>
            <p className="mt-1 text-red-400">{error}</p>
          </div>
        )}

        {isLoading && <div className="mt-8"><LoadingState /></div>}

        {!isLoading && candidates.length > 0 && (
          <div className="mt-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-200">Results</h2>
              <span className="text-xs text-slate-500">Showing {candidates.length} of {totalResults} matches</span>
            </div>
            <ResultsList candidates={candidates} />
          </div>
        )}

        {!isLoading && hasSearched && candidates.length === 0 && !error && (
          <div className="mt-12 text-center">
            <p className="text-slate-500 text-sm">No books found. Try rephrasing your query.</p>
          </div>
        )}
      </main>

      <footer className="border-t border-slate-800 mt-16">
        <div className="max-w-4xl mx-auto px-4 py-6 text-center">
          <p className="text-xs text-slate-600">Powered by Claude AI and Open Library. Built for the CBTW Technical Challenge.</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
