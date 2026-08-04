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
import { ChatWindow } from "@/components/ChatWindow";
import { HeadlinesBanner } from "@/components/HeadlinesBanner";
import { useFeatureFlag } from "@/lib/feature-flags-context";
import { useLanguage } from "@/lib/i18n-context";
import { translateCategory } from "@/lib/api-translator";
import { useTranslatedArticle, useTranslatedArticles } from "@/hooks/use-translated-articles";
import { translateText } from "@/lib/client-translator";

interface ChatMessage {
  text: string;
  isUser: boolean;
  timestamp: Date;
}
export default function NewsDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { t, language } = useLanguage();
  const { newsId: encodedTitle } = params;
  const newsId = decodeURIComponent(encodedTitle as string);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [newsItem, setNewsItem] = useState<NewsItem | null>(null);
  const { translatedArticle, isTranslating } = useTranslatedArticle(newsItem);
  const [moreNewsItems, setMoreNewsItems] = useState<NewsItem[]>([]);
  const { translatedArticles: translatedMoreNews } = useTranslatedArticles(moreNewsItems);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const isSimilarNewsEnabled = useFeatureFlag("similar_news");
  const isLargeArticleChatWindowEnabled = useFeatureFlag("article_chat_large_window");

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
      const data = await chatApi.sendArticleChat(newsId, inputMessage, token);
      let replyText = data.response || "Sorry, I couldn't process your request.";
      if (language !== "en") {
        replyText = await translateText(replyText, language);
      }
      // Add bot response to chat
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
      // Add error message
      const errorMessage: ChatMessage = {
        text: errText,
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

  const [translatedSourceName, setTranslatedSourceName] = useState("");

  useEffect(() => {
    const srcName = newsItem?.source?.title || newsItem?.source?.name;
    if (!srcName) return;
    let isCancelled = false;

    if (language === "en") {
      setTranslatedSourceName(srcName);
    } else {
      translateText(srcName, language).then((res) => {
        if (!isCancelled) setTranslatedSourceName(res);
      });
    }

    return () => {
      isCancelled = true;
    };
  }, [newsItem?.source?.title, newsItem?.source?.name, language]);

  // Loading State
  if (loading || isTranslating) {
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
  const displayArticle = translatedArticle || newsItem;

  // Render News Content
  return (
    <div className="max-w-[1400px] mx-auto px-3 sm:px-6 py-6 sm:py-8">
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

      <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr_1fr] gap-5 md:gap-6 lg:gap-8">
        <div className="order-1 md:order-2">
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mb-2.5 sm:mb-4 leading-tight">{displayArticle.title}</h1>
          {(() => {
            const rawAuthor =
              displayArticle.author ||
              displayArticle.source?.name ||
              (displayArticle.source as any)?.source;
            const isValidAuthor =
              rawAuthor &&
              typeof rawAuthor === "string" &&
              rawAuthor.trim() !== "" &&
              !["unknown", "unknown author", "none", "null"].includes(rawAuthor.trim().toLowerCase()) &&
              rawAuthor.trim().toLowerCase() !== (displayArticle.title || "").trim().toLowerCase();
            return (
              <div className="text-xs sm:text-sm text-muted-foreground mb-3 sm:mb-4">
                {t("published_on")} {formatArticleDate(displayArticle.publication_date, language)}
                {isValidAuthor ? ` ${t("by_author")} ${rawAuthor.trim()}` : ""} {t("in_category")} {translateCategory(displayArticle.category || "General", language)}
              </div>
            );
          })()}
          {(() => {
            const mainImageUrl =
              displayArticle.source?.image_url ||
              displayArticle.source?.media?.[0] ||
              (displayArticle as any)?.image_url ||
              (displayArticle as any)?.image;
            return mainImageUrl ? (
              <div className="bg-muted rounded-2xl mb-4 sm:mb-6 max-h-[280px] sm:max-h-[420px] overflow-hidden flex items-center justify-center border">
                <img
                  src={mainImageUrl}
                  alt={displayArticle.title}
                  className="object-cover w-full h-full rounded-2xl"
                />
              </div>
            ) : null;
          })()}
          <div className="prose dark:prose-invert max-w-none text-sm sm:text-base leading-relaxed overflow-x-auto break-words">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {displayArticle?.markdown_content
                ? displayArticle.markdown_content.replace(/\\n/g, "\n")
                : displayArticle.content
                  ? displayArticle.content.replace(/\\n/g, "\n")
                  : ""}
            </ReactMarkdown>
          </div>
          {displayArticle.source?.url && (
            <p className="mt-6 text-xs sm:text-sm text-muted-foreground pt-4 border-t">
              {t("source_label")}:{" "}
              <Link
                href={displayArticle.source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline font-medium"
              >
                {translatedSourceName || displayArticle.source.title || displayArticle.source.name || "Link"}
              </Link>
            </p>
          )}
          {newsItem?.location && <Location location={newsItem.location} />}
        </div>

        {/* More News Section */}
        <div className="border-t md:border-t-0 pt-6 md:pt-0 order-2 md:order-1">
          <h2 className="text-lg sm:text-xl font-bold mb-4">{t("more_news")}</h2>
          {translatedMoreNews.length === 0 ? (
            <p className="text-muted-foreground text-xs sm:text-sm">
              {t("no_other_news")}
            </p>
          ) : (
            <ul className="space-y-3">
              {(isSimilarNewsEnabled ? translatedMoreNews.slice(0, 6) : translatedMoreNews).map((item) => {
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
        {/* Right spacer to keep article centered */}
        <div className="hidden md:block order-3" />
      </div>

      {/* Floating Chat Button & Mobile Drawer */}
      <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-50">
        <ChatWindow
          isOpen={isChatOpen}
          onClose={toggleChat}
          messages={messages}
          isTyping={isTyping}
          inputMessage={inputMessage}
          setInputMessage={setInputMessage}
          sendMessage={sendMessage}
          messagesEndRef={messagesEndRef}
          inputRef={inputRef}
          title="DistillNews Assistant"
          placeholder="Type your message..."
          emptyStateText="Ask me anything about the news!"
        />
      </div>
    </div>
  );
}
