import BookCard from "./BookCard.jsx";

function ResultsList({ candidates }) {
  if (!candidates || candidates.length === 0) return null;

  return (
    <div className="space-y-3" role="list" aria-label="Book search results">
      {candidates.map((candidate, index) => (
        <BookCard key={candidate.open_library_id || index} candidate={candidate} rank={index + 1} />
      ))}
    </div>
  );
}

export default ResultsList;
