import { useState, useCallback } from "react";

function CoverPlaceholder() {
  return (
    <div className="w-full h-full bg-slate-700 flex items-center justify-center rounded">
      <svg className="w-10 h-10 text-slate-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
      </svg>
    </div>
  );
}

function BookCard({ candidate, rank }) {
  const [imageError, setImageError] = useState(false);
  const handleImageError = useCallback(() => setImageError(true), []);
  const hasCover = candidate.cover_url && !imageError;

  return (
    <article className="flex gap-4 p-4 rounded-lg bg-slate-800/60 border border-slate-700/50 hover:border-slate-600 transition-colors duration-150" role="listitem">
      <div className="flex-shrink-0 w-6 pt-1">
        <span className="text-xs font-mono text-slate-600 select-none">{String(rank).padStart(2, "0")}</span>
      </div>
      <div className="flex-shrink-0 w-20 h-28 overflow-hidden rounded">
        {hasCover
          ? <img src={candidate.cover_url} alt={`Cover of ${candidate.title}`} onError={handleImageError} className="w-full h-full object-cover" loading="lazy" />
          : <CoverPlaceholder />}
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-base font-semibold text-slate-100 leading-tight truncate">{candidate.title}</h3>
        <p className="mt-1 text-sm text-slate-400">
          {candidate.author}
          {candidate.first_publish_year && <span className="text-slate-600"> &middot; {candidate.first_publish_year}</span>}
        </p>
        <p className="mt-2 text-xs text-slate-500 leading-relaxed">{candidate.explanation}</p>
        {candidate.open_library_url && (
          <a href={candidate.open_library_url} target="_blank" rel="noopener noreferrer"
            className="inline-block mt-2 text-xs text-blue-400 hover:text-blue-300 transition-colors duration-150">
            View on Open Library &rarr;
          </a>
        )}
      </div>
    </article>
  );
}

export default BookCard;
