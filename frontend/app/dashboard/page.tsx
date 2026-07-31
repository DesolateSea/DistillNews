"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import ReactMarkdown from "react-markdown";
import {
  Card,
  CardFooter,
  CardTitle,
} from "@/components/ui/card";
import {
  Newspaper,
  Settings,
  LogOut,
  LogIn,
  MessageCircle,
  X,
  Send,
  Search,
} from "lucide-react";
import { chatApi, feedsApi, formatArticleDate, type NewsItem } from "@/lib/api";
import { NewsFeedSkeleton } from "@/components/NewsFeedSkeleton";
import { Skeleton } from "@/components/ui/skeleton";
import { FeatureFlagGuard } from "@/lib/feature-flags-context";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ChatFab } from "@/components/ChatFab";

interface ChatMessage {
  text: string;
  isUser: boolean;
  timestamp: Date;
}

const CATEGORIES = [
  "All",
  "Technology",
  "Business",
  "Science",
  "Health",
  "Entertainment",
  "Sports",
  "World",
];

export default function DashboardPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const isFetchingRef = useRef(false);
  const ITEMS_PER_PAGE = 9;

  // Search & Category state
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>("All");

  // Chat state
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setMounted(true);
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("SNAPtoken") || localStorage.getItem("token");
      setIsLoggedIn(!!token);
    }
  }, []);

  const fetchNews = useCallback(async (pageNum: number, catOverride?: string) => {
    const token = typeof window !== "undefined" ? (localStorage.getItem("SNAPtoken") || localStorage.getItem("token")) : null;
    setIsLoggedIn(!!token);
    const catToUse = catOverride !== undefined ? catOverride : selectedCategory;
    const catParam = catToUse === "All" ? undefined : catToUse;

    try {
      isFetchingRef.current = true;
      setLoadingMore(pageNum > 1);

      if (searchQuery) {
        const { feeds, has_more } = await feedsApi.search(searchQuery, pageNum, ITEMS_PER_PAGE, catParam, token);
        const newArticles = feeds as NewsItem[];
        const hasMoreNext = newArticles.length > 0 && (has_more ?? newArticles.length === ITEMS_PER_PAGE);
        setHasMore(hasMoreNext);
        setNews((prev) => (pageNum === 1 ? newArticles : [...prev, ...newArticles]));
      } else {
        const { feeds, has_more } = await feedsApi.list(token, pageNum, ITEMS_PER_PAGE, catParam);
        const newArticles = feeds as NewsItem[];
        const hasMoreNext = newArticles.length > 0 && (has_more ?? newArticles.length === ITEMS_PER_PAGE);
        setHasMore(hasMoreNext);
        setNews((prev) => (pageNum === 1 ? newArticles : [...prev, ...newArticles]));
      }
    } catch (err) {
      console.error("Error fetching news:", err);
    } finally {
      isFetchingRef.current = false;
      setIsLoading(false);
      setLoadingMore(false);
    }
  }, [searchQuery, selectedCategory]);

  const handleSearch = async (overrideQuery?: string) => {
    const queryToUse = overrideQuery !== undefined ? overrideQuery : searchInput;
    const cleanQuery = queryToUse.trim();
    if (!cleanQuery) {
      clearSearch();
      return;
    }
    setSearchQuery(cleanQuery);
    setIsSearching(true);
    setPage(1);
    const catParam = selectedCategory === "All" ? undefined : selectedCategory;
    try {
      const token = localStorage.getItem("SNAPtoken");
      const { feeds, has_more } = await feedsApi.search(cleanQuery, 1, ITEMS_PER_PAGE, catParam, token);
      const searchArticles = feeds as NewsItem[];
      setNews(searchArticles);
      setHasMore(!!has_more);
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setIsSearching(false);
    }
  };

  const clearSearch = async () => {
    setSearchInput("");
    setSearchQuery("");
    setPage(1);
    setIsSearching(true);
    const catParam = selectedCategory === "All" ? undefined : selectedCategory;
    try {
      const token = localStorage.getItem("SNAPtoken");
      const { feeds, has_more } = await feedsApi.list(token, 1, ITEMS_PER_PAGE, catParam);
      const newArticles = feeds as NewsItem[];
      setNews(newArticles);
      setHasMore(!!has_more);
    } catch (err) {
      console.error("Error resetting feed:", err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleCategorySelect = async (category: string) => {
    if (selectedCategory === category) return;
    setSelectedCategory(category);
    setPage(1);
    setIsSearching(true);
    const catParam = category === "All" ? undefined : category;
    const token = localStorage.getItem("SNAPtoken");
    try {
      if (searchQuery) {
        const { feeds, has_more } = await feedsApi.search(searchQuery, 1, ITEMS_PER_PAGE, catParam, token);
        setNews(feeds as NewsItem[]);
        setHasMore(!!has_more);
      } else {
        const { feeds, has_more } = await feedsApi.list(token, 1, ITEMS_PER_PAGE, catParam);
        setNews(feeds as NewsItem[]);
        setHasMore(!!has_more);
      }
    } catch (err) {
      console.error("Error filtering by category:", err);
    } finally {
      setIsSearching(false);
    }
  };

  // Infinite scroll observer using IntersectionObserver on bottom sentinel
  const observerRef = useRef<IntersectionObserver | null>(null);
  const sentinelRef = useCallback(
    (node: HTMLDivElement | null) => {
      if (isLoading || loadingMore || !hasMore) return;
      if (observerRef.current) observerRef.current.disconnect();

      observerRef.current = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting && hasMore && !isFetchingRef.current) {
            setPage((p) => p + 1);
          }
        },
        { rootMargin: "300px" }
      );

      if (node) observerRef.current.observe(node);
    },
    [isLoading, loadingMore, hasMore]
  );

  // Window scroll fallback as additional backup for page scrolling
  useEffect(() => {
    const handleWindowScroll = () => {
      if (isFetchingRef.current || !hasMore || loadingMore) return;
      const scrollHeight = document.documentElement.scrollHeight;
      const scrollTop = window.scrollY || document.documentElement.scrollTop;
      const clientHeight = window.innerHeight;

      if (scrollTop + clientHeight >= scrollHeight - 300) {
        setPage((p) => p + 1);
      }
    };

    window.addEventListener("scroll", handleWindowScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleWindowScroll);
  }, [hasMore, loadingMore]);

  // On mount: load page 1
  useEffect(() => {
    fetchNews(1);
  }, [fetchNews]);

  // Auto-scroll chat to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus chat input when opened
  useEffect(() => {
    if (isChatOpen) inputRef.current?.focus();
  }, [isChatOpen]);

  const handleLogout = () => {
    localStorage.removeItem("SNAPtoken");
    setIsLoggedIn(false);
    fetchNews(1);
  };

  // Fetch subsequent pages — guard page > 1 to avoid double-fetch on mount
  useEffect(() => {
    if (hasMore && page > 1) {
      fetchNews(page);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const toggleChat = () => setIsChatOpen((prev) => !prev);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;

    const token = localStorage.getItem("SNAPtoken");

    const userMessage: ChatMessage = {
      text: inputMessage,
      isUser: true,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setIsTyping(true);

    try {
      const data = await chatApi.send(inputMessage, token);
      const botMessage: ChatMessage = {
        text: data.response || "Sorry, I couldn't process your request.",
        isUser: false,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Error sending message:", error);
      setMessages((prev) => [
        ...prev,
        {
          text: "Sorry, there was an error processing your request. Please try again.",
          isUser: false,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b sticky top-0 bg-background/95 backdrop-blur z-40">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/" className="flex items-center gap-2">
            <Newspaper className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold">DistillNews</h1>
          </Link>
          <div className="flex items-center gap-4">
            <ThemeToggle />
            <Link href="/preferences">
              <Button variant="outline" size="sm">
                <Settings className="h-4 w-4 mr-2" />
                Preferences
              </Button>
            </Link>
            {!mounted ? (
              <Skeleton className="h-8 w-20 rounded" />
            ) : isLoggedIn ? (
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                <LogOut className="h-4 w-4 mr-2" />
                Sign Out
              </Button>
            ) : (
              <Link href="/register">
                <Button size="sm">
                  <LogIn className="h-4 w-4 mr-2" />
                  Sign In
                </Button>
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1 container mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-bold">
              {!mounted ? (
                <Skeleton className="h-9 w-72 rounded inline-block" />
              ) : searchQuery ? (
                `Search Results for "${searchQuery}"`
              ) : isLoggedIn ? (
                "Your Personalized News Feed"
              ) : (
                "Latest News"
              )}
            </h1>
            {searchQuery && (
              <p className="text-sm text-muted-foreground mt-1 flex items-center gap-2">
                <span>Semantic AI vector search found {news.length} matching stories</span>
                <button
                  onClick={clearSearch}
                  className="text-xs text-primary hover:underline font-medium"
                >
                  Clear search
                </button>
              </p>
            )}
          </div>

          {/* Semantic Search Bar */}
          <FeatureFlagGuard name="semantic_search">
            <div className="relative w-full md:w-96">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSearch();
                }}
                className="w-full pl-9 pr-16 py-2 bg-background border border-input rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary shadow-sm"
              />
              <Button
                size="sm"
                onClick={() => handleSearch()}
                disabled={isSearching}
                className="absolute right-1 top-1/2 -translate-y-1/2 rounded-full h-7 px-3 text-xs flex items-center justify-center min-w-[60px]"
              >
                {isSearching ? (
                  <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-primary-foreground" />
                ) : (
                  "Search"
                )}
              </Button>
            </div>
          </FeatureFlagGuard>
        </div>

        {/* Category Filter Pills Bar */}
        <FeatureFlagGuard name="category_filters">
          <div className="flex items-center gap-2 overflow-x-auto pb-2 mb-6 scrollbar-none">
            {CATEGORIES.map((cat) => {
              const isSelected = selectedCategory === cat;
              return (
                <button
                  key={cat}
                  onClick={() => handleCategorySelect(cat)}
                  className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all whitespace-nowrap border ${
                    isSelected
                      ? "bg-primary text-primary-foreground border-primary shadow-sm"
                      : "bg-card text-muted-foreground border-border/60 hover:bg-accent hover:text-accent-foreground"
                  }`}
                >
                  {cat}
                </button>
              );
            })}
          </div>
        </FeatureFlagGuard>

        <FeatureFlagGuard name="guest_banner">
          {!isLoading && !isLoggedIn && (
            <div className="mb-6 p-4 rounded-xl bg-primary/10 border border-primary/20 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div>
                <p className="font-semibold text-sm text-foreground">Browsing as Guest</p>
                <p className="text-xs text-muted-foreground">
                  Sign in to set your favorite news topics and enjoy an AI-personalized feed.
                </p>
              </div>
              <Link href="/register">
                <Button size="sm" className="whitespace-nowrap">
                  <LogIn className="h-4 w-4 mr-2" />
                  Sign In to Personalize
                </Button>
              </Link>
            </div>
          )}
        </FeatureFlagGuard>

        {/* Empty state fallback */}
        {!isLoading && news.length === 0 && (
          <div className="text-center py-12 border rounded-xl bg-card my-6">
            <Newspaper className="h-12 w-12 mx-auto text-muted-foreground mb-4 opacity-50" />
            <h3 className="text-lg font-semibold mb-1">No news articles found</h3>
            <p className="text-sm text-muted-foreground mb-4 max-w-md mx-auto">
              No articles are currently available in the active article store. Try refreshing or check that your backend server is running.
            </p>
            <Button variant="outline" onClick={() => fetchNews(1)}>
              Retry Loading Feed
            </Button>
          </div>
        )}

        {/* Main News Feed Grid - Skeleton loading on initial load, otherwise News Cards */}
        {isLoading ? (
          <NewsFeedSkeleton count={9} />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {news.map((item, idx) => (
              <NewsCard key={`${item.id}-${idx}`} newsItem={item} />
            ))}
          </div>
        )}

        {/* Loading Spinner & Sentinel Observer for Infinite Scroll */}
        <div ref={sentinelRef} className="py-6 flex flex-col items-center justify-center">
          {loadingMore && (
            <div className="flex items-center gap-3 text-muted-foreground">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
              <span className="text-sm font-medium">Loading more news...</span>
            </div>
          )}

          {hasMore && !loadingMore && (
            <Button
              variant="outline"
              onClick={() => setPage((p) => p + 1)}
              className="px-6"
            >
              Load More News
            </Button>
          )}

          {!hasMore && news.length > 0 && (
            <p className="text-center text-muted-foreground text-sm py-4">
              You've reached the end of your feed
            </p>
          )}
        </div>
      </main>

      <footer className="border-t py-8">
        <div className="container mx-auto px-4 text-center text-muted-foreground">
          <p>© {new Date().getFullYear()} DistillNews. All rights reserved.</p>
        </div>
      </footer>

      {/* Floating Chat Button */}
      <FeatureFlagGuard name="ai_chat">
        <div className="fixed bottom-6 right-6 z-50">
          {!isChatOpen ? (
            <ChatFab onClick={toggleChat} />
          ) : (
          <div
            className="bg-card border border-border rounded-lg shadow-xl w-80 sm:w-96 flex flex-col"
            style={{ height: "500px" }}
          >
            {/* Chat Header */}
            <div className="p-4 border-b flex justify-between items-center">
              <h3 className="font-semibold">DistillNews Assistant</h3>
              <Button variant="ghost" size="icon" onClick={toggleChat}>
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 p-4 overflow-y-auto">
              {messages.length === 0 ? (
                <div className="h-full flex items-center justify-center text-center text-muted-foreground">
                  <div>
                    <MessageCircle className="h-10 w-10 mx-auto mb-2 opacity-50" />
                    <p>Ask me anything about the news!</p>
                  </div>
                </div>
              ) : (
                <>
                  {messages.map((msg, index) => (
                    <div
                      key={index}
                      className={`mb-4 flex ${msg.isUser ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-3/4 p-3 rounded-lg ${msg.isUser
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
                          }`}
                      >
                        <ReactMarkdown>
                          {msg.text.replaceAll("\n", "\n\n")}
                        </ReactMarkdown>
                        <div className="text-xs opacity-70 mt-1">
                          {msg.timestamp.toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      </div>
                    </div>
                  ))}
                  {isTyping && (
                    <div className="mb-4 flex justify-start">
                      <div className="max-w-3/4 p-3 rounded-lg bg-muted flex space-x-1">
                        <div className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                        <div className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce" style={{ animationDelay: "200ms" }} />
                        <div className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce" style={{ animationDelay: "400ms" }} />
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>

            {/* Chat Input */}
            <form onSubmit={sendMessage} className="p-4 border-t flex gap-2">
              <input
                type="text"
                ref={inputRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Type your message..."
                className="flex-1 bg-muted rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={isTyping}
              />
              <Button
                type="submit"
                size="icon"
                disabled={isTyping || !inputMessage.trim()}
              >
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </div>
        )}
      </div>
      </FeatureFlagGuard>
    </div>
  );
}

interface NewsCardProps {
  newsItem: NewsItem;
}

function NewsCard({ newsItem }: NewsCardProps) {
  const imageUrl =
    newsItem?.source?.image_url ||
    newsItem?.source?.media?.[0] ||
    (newsItem as any)?.image_url ||
    (newsItem as any)?.image;
  return (
    <Link href={`/${encodeURIComponent(newsItem.id)}`}>
      <Card className="cursor-pointer hover:shadow-md transition-shadow duration-200 px-5 min-h-[200px] pt-5">
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <div className="text-sm font-medium text-primary mb-1">
              {newsItem.category}
            </div>
            <CardTitle className="text-xl line-clamp-2">
              {newsItem.title}
            </CardTitle>
          </div>
          {imageUrl && (
            <img
              src={imageUrl}
              alt={newsItem.title}
              className="w-28 h-28 object-cover rounded-md flex-shrink-0"
              onError={(e) => {
                (e.target as HTMLElement).style.display = "none";
              }}
            />
          )}
        </div>
        <CardFooter className="flex justify-between pt-2">
          <div className="text-sm text-muted-foreground">
            {formatArticleDate(newsItem.publication_date)}
          </div>
          <Button variant="ghost" size="sm">
            Read More
          </Button>
        </CardFooter>
      </Card>
    </Link>
  );
}
