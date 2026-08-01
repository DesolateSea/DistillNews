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
import { chatApi, feedsApi, formatArticleDate, clearApiCache, type NewsItem } from "@/lib/api";
import { NewsFeedSkeleton } from "@/components/NewsFeedSkeleton";
import { Skeleton } from "@/components/ui/skeleton";
import { FeatureFlagGuard } from "@/lib/feature-flags-context";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LanguageToggle } from "@/components/LanguageToggle";
import { useLanguage } from "@/lib/i18n-context";
import { translateCategory } from "@/lib/api-translator";
import { ChatFab } from "@/components/ChatFab";
import { HeadlinesBanner } from "@/components/HeadlinesBanner";
import { useTranslatedArticles } from "@/hooks/use-translated-articles";
import { translateText } from "@/lib/client-translator";

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
  const { t, language } = useLanguage();
  const [mounted, setMounted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [news, setNews] = useState<NewsItem[]>([]);
  const { translatedArticles, isTranslating } = useTranslatedArticles(news);
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
      const token = localStorage.getItem("SNAPtoken") || localStorage.getItem("token");
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
      const token = localStorage.getItem("SNAPtoken") || localStorage.getItem("token");
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
    const token = localStorage.getItem("SNAPtoken") || localStorage.getItem("token");
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
    if (typeof window !== "undefined") {
      localStorage.removeItem("SNAPtoken");
      localStorage.removeItem("token");
    }
    clearApiCache();
    setIsLoggedIn(false);
    setNews([]);
    setPage(1);
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

    const token = localStorage.getItem("SNAPtoken") || localStorage.getItem("token");

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
      let replyText = data.response || "Sorry, I couldn't process your request.";
      if (language !== "en") {
        replyText = await translateText(replyText, language);
      }
      const botMessage: ChatMessage = {
        text: replyText,
        isUser: false,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Error sending message:", error);
      let errText = "Sorry, there was an error processing your request. Please try again.";
      if (language !== "en") {
        errText = await translateText(errText, language);
      }
      setMessages((prev) => [
        ...prev,
        {
          text: errText,
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
        <div className="container mx-auto px-3 sm:px-4 py-3 sm:py-4 flex justify-between items-center gap-2">
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <Newspaper className="h-5 w-5 sm:h-6 sm:w-6 text-primary" />
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight">DistillNews</h1>
          </Link>
          <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
            <LanguageToggle />
            <ThemeToggle />
            <Link href="/preferences">
              <Button variant="outline" size="sm" className="h-9 px-2.5 sm:px-3 text-xs sm:text-sm">
                <Settings className="h-4 w-4 sm:mr-1.5" />
                <span className="hidden sm:inline">{t("preferences")}</span>
              </Button>
            </Link>
            {!mounted ? (
              <Skeleton className="h-8 w-16 sm:w-20 rounded" />
            ) : isLoggedIn ? (
              <Button variant="ghost" size="sm" onClick={handleLogout} className="h-9 px-2.5 sm:px-3 text-xs sm:text-sm">
                <LogOut className="h-4 w-4 sm:mr-1.5" />
                <span className="hidden sm:inline">{t("sign_out")}</span>
              </Button>
            ) : (
              <Link href="/register">
                <Button size="sm" className="h-9 px-2.5 sm:px-3 text-xs sm:text-sm">
                  <LogIn className="h-4 w-4 sm:mr-1.5" />
                  <span className="hidden sm:inline">{t("sign_in")}</span>
                </Button>
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1 container mx-auto px-3 sm:px-4 py-2.5 sm:py-8">
        <HeadlinesBanner variant="full" />

        <div className="flex flex-col md:flex-row md:items-center justify-between mb-3.5 sm:mb-6 gap-2.5 sm:gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
              {!mounted ? (
                <Skeleton className="h-8 sm:h-9 w-60 sm:w-72 rounded inline-block" />
              ) : searchQuery ? (
                `Search Results for "${searchQuery}"`
              ) : isLoggedIn ? (
                t("personalized_feed")
              ) : (
                t("latest_news")
              )}
            </h1>
            {searchQuery && (
              <p className="text-xs sm:text-sm text-muted-foreground mt-1 flex items-center gap-2">
                <span>Semantic AI vector search found {news.length} matching stories</span>
                <button
                  onClick={clearSearch}
                  className="text-xs text-primary hover:underline font-medium"
                >
                  {t("clear_search")}
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
                placeholder={t("search_placeholder")}
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSearch();
                }}
                className="w-full pl-9 pr-24 py-2 bg-background border border-input rounded-full text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary shadow-xs"
              />
              <Button
                size="sm"
                onClick={() => handleSearch()}
                disabled={isSearching}
                className="absolute right-1 top-1/2 -translate-y-1/2 rounded-full h-7 px-3 text-xs flex items-center justify-center min-w-[64px]"
              >
                {isSearching ? (
                  <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-primary-foreground" />
                ) : (
                  t("search_button")
                )}
              </Button>
            </div>
          </FeatureFlagGuard>
        </div>

        {/* Category Filter Pills Bar */}
        <FeatureFlagGuard name="category_filters">
          <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto pb-1.5 mb-3.5 sm:mb-6 no-scrollbar -mx-3 px-3 sm:mx-0 sm:px-0">
            {CATEGORIES.map((cat) => {
              const isSelected = selectedCategory === cat;
              return (
                <button
                  key={cat}
                  onClick={() => handleCategorySelect(cat)}
                  className={`px-3.5 py-1.5 sm:px-4 rounded-full text-xs font-medium transition-all whitespace-nowrap shrink-0 border ${
                    isSelected
                      ? "bg-primary text-primary-foreground border-primary shadow-xs"
                      : "bg-card text-muted-foreground border-border/60 hover:bg-accent hover:text-accent-foreground"
                  }`}
                >
                  {translateCategory(cat, language)}
                </button>
              );
            })}
          </div>
        </FeatureFlagGuard>

        <FeatureFlagGuard name="guest_banner">
          {!isLoading && !isLoggedIn && (
            <div className="mb-3.5 sm:mb-6 p-3.5 sm:p-4 rounded-xl bg-primary/10 border border-primary/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
              <div>
                <p className="font-semibold text-sm text-foreground">{t("browsing_as_guest")}</p>
                <p className="text-xs text-muted-foreground">
                  {t("guest_banner_subtitle")}
                </p>
              </div>
              <Link href="/register" className="w-full sm:w-auto">
                <Button size="sm" className="w-full sm:w-auto whitespace-nowrap">
                  <LogIn className="h-4 w-4 mr-2" />
                  {t("sign_in_to_personalize")}
                </Button>
              </Link>
            </div>
          )}
        </FeatureFlagGuard>

        {/* Empty state fallback */}
        {!isLoading && news.length === 0 && (
          <div className="text-center py-8 sm:py-12 border rounded-xl bg-card my-4 sm:my-6 px-4">
            <Newspaper className="h-10 w-10 sm:h-12 sm:w-12 mx-auto text-muted-foreground mb-3 sm:mb-4 opacity-50" />
            <h3 className="text-base sm:text-lg font-semibold mb-1">{t("no_articles_found")}</h3>
            <p className="text-xs sm:text-sm text-muted-foreground mb-4 max-w-md mx-auto">
              {t("no_articles_desc")}
            </p>
            <Button variant="outline" onClick={() => fetchNews(1)}>
              {t("retry_feed")}
            </Button>
          </div>
        )}

        {/* Main News Feed Grid */}
        {isLoading || (isTranslating && translatedArticles.length === 0) ? (
          <NewsFeedSkeleton count={9} />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 sm:gap-6 mb-4 sm:mb-8">
            {translatedArticles.map((item, idx) => (
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
              {t("load_more_news")}
            </Button>
          )}

          {!hasMore && news.length > 0 && (
            <p className="text-center text-muted-foreground text-sm py-4">
              {t("end_of_feed")}
            </p>
          )}
        </div>
      </main>

      <footer className="border-t py-6 sm:py-8">
        <div className="container mx-auto px-4 text-center text-xs sm:text-sm text-muted-foreground">
          <p>© {new Date().getFullYear()} DistillNews. {t("rights_reserved")}</p>
        </div>
      </footer>

      {/* Floating Chat Button & Modal/Drawer */}
      <FeatureFlagGuard name="ai_chat">
        <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-50">
          {!isChatOpen ? (
            <ChatFab onClick={toggleChat} />
          ) : (
            <>
              {/* Mobile overlay backdrop */}
              <div
                className="fixed inset-0 bg-background/80 backdrop-blur-xs sm:hidden z-40"
                onClick={toggleChat}
              />
              <div
                className="fixed inset-x-3 bottom-3 top-14 sm:top-auto sm:left-auto sm:right-6 sm:bottom-6 sm:w-[400px] sm:h-[550px] bg-card border border-border rounded-2xl shadow-2xl z-50 flex flex-col overflow-hidden"
              >
                {/* Chat Header */}
                <div className="p-3.5 sm:p-4 border-b flex justify-between items-center bg-muted/30">
                  <h3 className="font-semibold text-sm sm:text-base">{t("chat_assistant_title")}</h3>
                  <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full" onClick={toggleChat}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                {/* Chat Messages */}
                <div className="flex-1 p-3.5 sm:p-4 overflow-y-auto">
                  {messages.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-center text-muted-foreground">
                      <div>
                        <MessageCircle className="h-10 w-10 mx-auto mb-2 opacity-50" />
                        <p className="text-xs sm:text-sm">{t("chat_ask_anything")}</p>
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
                            className={`max-w-[85%] sm:max-w-3/4 p-3 rounded-2xl text-xs sm:text-sm ${
                              msg.isUser
                                ? "bg-primary text-primary-foreground rounded-br-none"
                                : "bg-muted rounded-bl-none"
                            }`}
                          >
                            <ReactMarkdown>
                              {msg.text.replaceAll("\n", "\n\n")}
                            </ReactMarkdown>
                            <div className="text-[10px] opacity-70 mt-1 text-right">
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
                          <div className="max-w-3/4 p-3 rounded-2xl rounded-bl-none bg-muted flex space-x-1">
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
                <form onSubmit={sendMessage} className="p-3 sm:p-4 border-t flex gap-2 bg-background">
                  <input
                    type="text"
                    ref={inputRef}
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder={t("chat_type_message")}
                    className="flex-1 bg-muted rounded-xl px-3 py-2 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    disabled={isTyping}
                  />
                  <Button
                    type="submit"
                    size="icon"
                    className="rounded-xl h-9 w-9 shrink-0"
                    disabled={isTyping || !inputMessage.trim()}
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </form>
              </div>
            </>
          )}
        </div>
      </FeatureFlagGuard>
    </div>
  );
}

function NewsCard({ newsItem }: { newsItem: NewsItem }) {
  const { t, language } = useLanguage();
  const imageUrl =
    newsItem.source?.image_url ||
    newsItem.source?.media?.[0] ||
    (newsItem as any).image_url ||
    (newsItem as any).image;

  return (
    <Card className="flex flex-col justify-between hover:shadow-md transition-shadow overflow-hidden rounded-2xl border border-border/70">
      <div>
        <div className="p-5 sm:p-6 pb-2.5 sm:pb-3 flex justify-between gap-3.5 sm:gap-4">
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-primary mb-1">
              {translateCategory(newsItem.category, language)}
            </div>
            <CardTitle className="text-lg sm:text-xl font-bold line-clamp-3 sm:line-clamp-2 leading-snug">
              {newsItem.title}
            </CardTitle>
          </div>
          {imageUrl && (
            <img
              key={imageUrl}
              src={imageUrl}
              alt={newsItem.title}
              className="w-20 h-20 sm:w-28 sm:h-28 object-cover rounded-xl flex-shrink-0 bg-muted"
              onLoad={(e) => {
                (e.target as HTMLElement).style.display = "block";
              }}
              onError={(e) => {
                (e.target as HTMLElement).style.display = "none";
              }}
            />
          )}
        </div>
        <div className="px-5 sm:px-6 py-2 text-xs sm:text-sm text-muted-foreground line-clamp-3 leading-relaxed">
          {newsItem.summary}
        </div>
      </div>
      <CardFooter className="flex justify-between items-center pt-2 p-5 sm:p-6">
        <div className="text-xs text-muted-foreground font-medium">
          {formatArticleDate(newsItem.publication_date, language)}
        </div>
        <Link href={`/${encodeURIComponent(newsItem.id)}`}>
          <Button variant="ghost" size="sm" className="h-8 px-3 text-xs rounded-lg font-medium">
            {t("read_more")}
          </Button>
        </Link>
      </CardFooter>
    </Card>
  );
}
