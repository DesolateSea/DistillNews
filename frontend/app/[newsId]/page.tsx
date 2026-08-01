"use client";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useEffect, useState, useRef } from "react";
import dynamic from "next/dynamic";

const Location = dynamic(() => import("./location"), { ssr: false });
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageCircle, X, Send } from "lucide-react";
import { chatApi, feedsApi, formatArticleDate, type NewsItem } from "@/lib/api";
import { ChatFab } from "@/components/ChatFab";
import { HeadlinesBanner } from "@/components/HeadlinesBanner";
import { useLanguage } from "@/lib/i18n-context";

interface ChatMessage {
  text: string;
  isUser: boolean;
  timestamp: Date;
}
export default function NewsDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { t } = useLanguage();
  const { newsId: encodedTitle } = params;
  const newsId = decodeURIComponent(encodedTitle as string);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [newsItem, setNewsItem] = useState<NewsItem | null>(null);
  const [moreNewsItems, setMoreNewsItems] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const startTimeRef = useRef<number | null>(null);

  const sendDuration = async () => {
    if (!startTimeRef.current) return;
    const token = localStorage.getItem("SNAPtoken");
    const durationMs = Date.now() - startTimeRef.current;

    try {
      if (token) await feedsApi.trackTime(newsId, durationMs, token);
    } catch (err) {
      console.error("Failed to track article duration:", err);
    }
  };
  const toggleChat = () => {
    setIsChatOpen(!isChatOpen);
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputMessage.trim()) return;

    const token = localStorage.getItem("SNAPtoken");

    // Add user message to chat
    const userMessage: ChatMessage = {
      text: inputMessage,
      isUser: true,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setIsTyping(true);

    try {
      const data = await chatApi.sendArticleChat(newsId, inputMessage, token);
      // Add bot response to chat
      const botMessage: ChatMessage = {
        text: data.response || "Sorry, I couldn't process your request.",
        isUser: false,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Error sending message:", error);

      // Add error message
      const errorMessage: ChatMessage = {
        text: "Sorry, there was an error processing your request. Please try again.",
        isUser: false,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    const token = localStorage.getItem("SNAPtoken");

    const fetchNews = async () => {
      setLoading(true);
      setError(null);
      try {
        const newsData = await feedsApi.get(newsId, token);
        setNewsItem(newsData);
        startTimeRef.current = Date.now();

        const feeds = await feedsApi.list(token);
        setMoreNewsItems(feeds.feeds.filter((item) => item.id !== newsId));
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;
        console.error("Error fetching news:", err);
        setError((err as Error).message || "An unknown error occurred");
        setNewsItem(null);
        setMoreNewsItems([]);
      } finally {
        setLoading(false);
      }
    };

    fetchNews();

    const handleBeforeUnload = () => sendDuration();
    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      sendDuration();
      controller.abort();
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [router, newsId]);

  // Loading State
  if (loading) {
    return (
      <div className="container max-w-screen-lg mx-auto px-4 sm:px-6 py-8">
        <div className="mb-6">
          <Skeleton className="h-6 w-36 rounded" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
          <div className="md:col-span-2 space-y-6">
            <Skeleton className="h-10 w-11/12 rounded-lg" />
            <Skeleton className="h-4 w-1/2 rounded" />
            <Skeleton className="h-72 w-full rounded-xl" />
            <div className="space-y-3 pt-2">
              <Skeleton className="h-4 w-full rounded" />
              <Skeleton className="h-4 w-full rounded" />
              <Skeleton className="h-4 w-11/12 rounded" />
              <Skeleton className="h-4 w-4/5 rounded" />
            </div>
          </div>
          <div className="md:col-span-1 space-y-4">
            <Skeleton className="h-7 w-32 rounded" />
            <div className="space-y-3">
              <Skeleton className="h-20 w-full rounded-lg" />
              <Skeleton className="h-20 w-full rounded-lg" />
              <Skeleton className="h-20 w-full rounded-lg" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error State
  if (error && !newsItem) {
    return (
      <div className="container max-w-screen-lg mx-auto px-4 sm:px-6 py-8 text-red-600">
        <h1 className="text-2xl font-bold mb-4">Error Loading News</h1>
        <p>{error}</p>
        <Link
          href="/dashboard"
          className="text-blue-500 hover:underline mt-4 inline-block"
        >
          Go back to Dashboard
        </Link>
      </div>
    );
  }

  // Not Found State
  if (!newsItem && !loading && !error) {
    return (
      <div className="container max-w-screen-lg mx-auto px-4 sm:px-6 py-8">
        <h1 className="text-2xl font-bold mb-4">News Not Found</h1>
        <p>The requested news article could not be found.</p>
        <Link
          href="/dashboard"
          className="text-blue-500 hover:underline mt-4 inline-block"
        >
          Go back to Dashboard
        </Link>
      </div>
    );
  }

  // Final Fallback
  if (!newsItem) return null;

  // Render News Content
  return (
    <div className="container max-w-screen-lg mx-auto px-3 sm:px-6 py-2.5 sm:py-8">
      <HeadlinesBanner variant="ticker" />

      <div className="mb-3 sm:mb-6">
        <Link
          href="/dashboard"
          className="inline-flex items-center text-xs sm:text-sm text-primary hover:underline font-medium"
        >
          <ArrowLeft className="mr-1.5 h-3.5 w-3.5 sm:h-4 sm:w-4" />
          {t("back_to_dashboard")}
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 md:gap-8 lg:gap-12">
        <div className="md:col-span-2">
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mb-2.5 sm:mb-4 leading-tight">{newsItem.title}</h1>
          {(() => {
            const rawAuthor =
              newsItem.author ||
              newsItem.source?.name ||
              (newsItem.source as any)?.source;
            const isValidAuthor =
              rawAuthor &&
              typeof rawAuthor === "string" &&
              rawAuthor.trim() !== "" &&
              !["unknown", "unknown author", "none", "null"].includes(rawAuthor.trim().toLowerCase()) &&
              rawAuthor.trim().toLowerCase() !== (newsItem.title || "").trim().toLowerCase();
            return (
              <div className="text-xs sm:text-sm text-muted-foreground mb-3 sm:mb-4">
                {t("published_on")} {formatArticleDate(newsItem.publication_date)}
                {isValidAuthor ? ` ${t("by_author")} ${rawAuthor.trim()}` : ""} {t("in_category")} {newsItem.category || "General"}
              </div>
            );
          })()}
          {(() => {
            const mainImageUrl =
              newsItem.source?.image_url ||
              newsItem.source?.media?.[0] ||
              (newsItem as any)?.image_url ||
              (newsItem as any)?.image;
            return mainImageUrl ? (
              <div className="bg-muted rounded-2xl mb-4 sm:mb-6 max-h-[280px] sm:max-h-[420px] overflow-hidden flex items-center justify-center border">
                <img
                  src={mainImageUrl}
                  alt={newsItem.title}
                  className="object-cover w-full h-full rounded-2xl"
                />
              </div>
            ) : null;
          })()}
          <div className="prose dark:prose-invert max-w-none text-sm sm:text-base leading-relaxed overflow-x-auto break-words">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {newsItem?.markdown_content
                ? newsItem.markdown_content.replace(/\\n/g, "\n")
                : newsItem.content
                  ? newsItem.content.replace(/\\n/g, "\n")
                  : ""}
            </ReactMarkdown>
          </div>
          {newsItem.source?.url && (
            <p className="mt-6 text-xs sm:text-sm text-muted-foreground pt-4 border-t">
              Source:{" "}
              <Link
                href={newsItem.source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline font-medium"
              >
                {newsItem.source.title || newsItem.source.name || "Link"}
              </Link>
            </p>
          )}
          {newsItem?.location && <Location location={newsItem.location} />}
        </div>

        {/* More News Section */}
        <div className="md:col-span-1 border-t md:border-t-0 pt-6 md:pt-0">
          <h2 className="text-lg sm:text-xl font-bold mb-4">More News</h2>
          {moreNewsItems.length === 0 ? (
            <p className="text-muted-foreground text-xs sm:text-sm">
              No other news available.
            </p>
          ) : (
            <ul className="space-y-3">
              {moreNewsItems.map((item) => {
                const itemImageUrl = item.source?.image_url || item.source?.media?.[0];
                return (
                  <li key={item._id || item.id}>
                    <Link
                      href={`/${encodeURIComponent(item.id)}`}
                      className="flex items-center hover:bg-accent rounded-xl p-2.5 transition-colors border border-border/50 bg-card/60 gap-3"
                    >
                      {itemImageUrl && (
                        <div className="w-14 h-14 sm:w-16 sm:h-16 flex-shrink-0 overflow-hidden rounded-lg bg-muted">
                          <img
                            src={itemImageUrl}
                            alt={item.title}
                            className="object-cover w-full h-full"
                          />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <h3 className="text-xs sm:text-sm font-semibold leading-snug line-clamp-2">
                          {item.title}
                        </h3>
                      </div>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      {/* Floating Chat Button & Mobile Drawer */}
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
                <h3 className="font-semibold text-sm sm:text-base">DistillNews Assistant</h3>
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
                      <p className="text-xs sm:text-sm">Ask me anything about the news!</p>
                    </div>
                  </div>
                ) : (
                  <>
                    {messages.map((msg, index) => (
                      <div
                        key={index}
                        className={`mb-4 flex ${msg.isUser ? "justify-end" : "justify-start"
                          }`}
                      >
                        <div
                          className={`max-w-[85%] sm:max-w-3/4 p-3 rounded-2xl text-xs sm:text-sm ${msg.isUser
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
                          <div
                            className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce"
                            style={{ animationDelay: "0ms" }}
                          ></div>
                          <div
                            className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce"
                            style={{ animationDelay: "200ms" }}
                          ></div>
                          <div
                            className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce"
                            style={{ animationDelay: "400ms" }}
                          ></div>
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
                  placeholder="Type your message..."
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
    </div>
  );
}
