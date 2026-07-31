import { Skeleton } from "@/components/ui/skeleton";

export function ArticleSkeletonCard() {
  return (
    <div className="flex flex-col h-full rounded-xl border border-border/60 bg-card text-card-foreground shadow-sm overflow-hidden animate-pulse transition-all">
      {/* Image Skeleton Header */}
      <div className="w-full h-48 bg-muted relative flex items-center justify-center">
        <Skeleton className="w-full h-full rounded-none" />
        <Skeleton className="absolute top-3 left-3 h-5 w-20 rounded-full bg-primary/20" />
      </div>

      {/* Card Body Skeleton */}
      <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
        <div className="space-y-2.5">
          {/* Title Placeholder (2 lines) */}
          <Skeleton className="h-5 w-11/12 rounded" />
          <Skeleton className="h-5 w-3/4 rounded" />

          {/* Date & Source line */}
          <Skeleton className="h-3 w-1/2 rounded mt-2" />
        </div>

        {/* Summary Placeholder (3 lines) */}
        <div className="space-y-2 pt-2">
          <Skeleton className="h-3.5 w-full rounded" />
          <Skeleton className="h-3.5 w-11/12 rounded" />
          <Skeleton className="h-3.5 w-4/5 rounded" />
        </div>

        {/* Footer info line */}
        <div className="pt-4 border-t border-border/40 flex items-center justify-between">
          <Skeleton className="h-3 w-24 rounded" />
          <Skeleton className="h-3 w-16 rounded" />
        </div>
      </div>
    </div>
  );
}

export function NewsFeedSkeleton({ count = 9 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
      {Array.from({ length: count }).map((_, idx) => (
        <ArticleSkeletonCard key={idx} />
      ))}
    </div>
  );
}
