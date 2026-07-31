"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Flame, ChevronRight } from "lucide-react";
import { feedsApi, formatArticleDate, type NewsItem } from "@/lib/api";
import { useFeatureFlag } from "@/lib/feature-flags-context";

interface HeadlinesBannerProps {
  variant?: "ticker" | "hero" | "full";
}

export function HeadlinesBanner({ variant = "full" }: HeadlinesBannerProps) {
  const isEnabled = useFeatureFlag("top_headlines");
  const [headlines, setHeadlines] = useState<NewsItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!isEnabled) return;
    let isMounted = true;
    const fetchTopHeadlines = async () => {
      try {
        const data = await feedsApi.list(null, 1, 30);
        if (isMounted && data?.feeds && data.feeds.length > 0) {
          // Filter to only include articles that have a valid image URL
          const withImages = data.feeds.filter((item) => {
            const img =
              item.source?.image_url ||
              item.source?.media?.[0] ||
              (item as any).image_url ||
              (item as any).image;
            return typeof img === "string" && img.trim().length > 0;
          });
          setHeadlines(withImages.length > 0 ? withImages : data.feeds);
        }
      } catch (err) {
        console.error("Error loading top headlines:", err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };
    fetchTopHeadlines();
    return () => {
      isMounted = false;
    };
  }, [isEnabled]);

  // Auto-cycle headlines every 5 seconds
  useEffect(() => {
    if (headlines.length <= 1) return;
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % headlines.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [headlines.length]);

  if (!isEnabled || isLoading || headlines.length === 0) return null;

  const currentStory = headlines[currentIndex];
  const heroStory = headlines[currentIndex];

  const heroImage =
    heroStory?.source?.image_url ||
    heroStory?.source?.media?.[0] ||
    (heroStory as any)?.image_url ||
    (heroStory as any)?.image;

  return (
    <div className="w-full space-y-4 mb-6">
      {/* Headlines Ticker Bar */}
      <div className="bg-card border border-border/80 rounded-xl p-2.5 sm:px-4 shadow-xs flex items-center gap-3 overflow-hidden backdrop-blur">
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-red-500/10 text-red-600 dark:text-red-400 text-xs font-bold rounded-lg uppercase tracking-wider shrink-0 animate-pulse">
          <Flame className="h-3.5 w-3.5 fill-current" />
          <span>Top Headlines</span>
        </div>

        <div className="flex-1 min-w-0">
          <Link
            href={`/${encodeURIComponent(currentStory.id)}`}
            className="group flex items-center justify-between gap-2 text-sm text-foreground hover:text-primary transition-colors"
          >
            <span className="font-medium truncate group-hover:underline">
              {currentStory.title}
            </span>
            <span className="text-xs text-muted-foreground shrink-0 hidden sm:inline-flex items-center gap-1">
              <span>{currentStory.category}</span>
              <span>•</span>
              <span>{formatArticleDate(currentStory.publication_date)}</span>
            </span>
          </Link>
        </div>

        {headlines.length > 1 && (
          <div className="flex items-center gap-1 shrink-0">
            {headlines.slice(0, 5).map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentIndex(idx)}
                className={`h-1.5 rounded-full transition-all ${
                  idx === currentIndex ? "w-5 bg-primary" : "w-1.5 bg-muted-foreground/30 hover:bg-muted-foreground/60"
                }`}
                aria-label={`Go to headline ${idx + 1}`}
              />
            ))}
          </div>
        )}
      </div>

      {/* Featured Hero Story Card (For 'hero' or 'full' variant) */}
      {(variant === "hero" || variant === "full") && heroStory && (
        <div className="relative rounded-2xl overflow-hidden border border-border/80 bg-gradient-to-r from-primary/10 via-card to-card shadow-sm hover:shadow-md transition-all">
          <div className="p-6 md:p-8 flex flex-col md:flex-row gap-6 items-center">
            <div className="flex-1 space-y-3">
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-primary text-primary-foreground text-xs font-semibold rounded-full uppercase tracking-wider">
                  Featured Headline
                </span>
                <span className="text-xs text-muted-foreground font-medium">
                  {heroStory.category}
                </span>
              </div>
              <Link href={`/${encodeURIComponent(heroStory.id)}`}>
                <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight hover:text-primary transition-colors line-clamp-2">
                  {heroStory.title}
                </h2>
              </Link>
              <p className="text-muted-foreground text-sm line-clamp-2 md:line-clamp-3">
                {heroStory.summary}
              </p>
              <div className="pt-2 flex items-center gap-4">
                <Link href={`/${encodeURIComponent(heroStory.id)}`}>
                  <button className="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline">
                    Read Full Story <ChevronRight className="h-4 w-4" />
                  </button>
                </Link>
                <span className="text-xs text-muted-foreground">
                  {formatArticleDate(heroStory.publication_date)}
                </span>
              </div>
            </div>

            {heroImage && (
              <div className="w-full md:w-72 h-48 md:h-44 rounded-xl overflow-hidden shrink-0 shadow-xs relative bg-muted">
                <img
                  key={heroImage}
                  src={heroImage}
                  alt={heroStory.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  onLoad={(e) => {
                    (e.target as HTMLElement).style.display = "block";
                  }}
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = "none";
                  }}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
