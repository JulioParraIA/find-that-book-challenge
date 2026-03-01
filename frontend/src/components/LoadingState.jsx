const SKELETON_COUNT = 5;

function SkeletonCard() {
  return (
    <div className="flex gap-4 p-4 rounded-lg bg-slate-800/60 border border-slate-700/50 animate-pulse" aria-hidden="true">
      <div className="flex-shrink-0 w-6 pt-1"><div className="h-3 w-5 bg-slate-700 rounded" /></div>
      <div className="flex-shrink-0 w-20 h-28 bg-slate-700 rounded" />
      <div className="flex-1 space-y-3">
        <div className="h-4 w-3/4 bg-slate-700 rounded" />
        <div className="h-3 w-1/2 bg-slate-700/60 rounded" />
        <div className="space-y-1.5 pt-1">
          <div className="h-2.5 w-full bg-slate-700/40 rounded" />
          <div className="h-2.5 w-2/3 bg-slate-700/40 rounded" />
        </div>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-3" role="status" aria-label="Loading search results">
      <span className="sr-only">Searching for books...</span>
      {Array.from({ length: SKELETON_COUNT }, (_, i) => <SkeletonCard key={i} />)}
    </div>
  );
}

export default LoadingState;
