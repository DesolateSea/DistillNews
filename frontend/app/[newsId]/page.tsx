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
import { MessageCircle, X, Send } from "lucide-react";
import { chatApi, feedsApi, type NewsItem } from "@/lib/api";

interface ChatMessage {
  text: string;
  isUser: boolean;
  timestamp: Date;
}
export default function NewsDetailPage() {
  const params = useParams();
  const router = useRouter();
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
        <div className="animate-pulse grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="md:col-span-2 space-y-4">
            <div className="h-8 bg-gray-200 rounded-md" />
            <div className="h-6 bg-gray-200 rounded-md" />
            <div className="h-4 bg-gray-200 rounded-md max-h-[400px]" />
            <div className="h-6 bg-gray-200 rounded-md" />
            <div className="h-4 bg-gray-200 rounded-md" />
          </div>
          <div className="md:col-span-1 space-y-4">
            <div className="h-6 bg-gray-200 rounded-md" />
            <div className="h-20 bg-gray-200 rounded-md" />
            <div className="h-20 bg-gray-200 rounded-md" />
            <div className="h-20 bg-gray-200 rounded-md" />
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
    <div className="container max-w-screen-lg mx-auto px-4 sm:px-6 py-8">
      <div className="mb-6">
        <Link
          href="/dashboard"
          className="inline-flex items-center text-blue-500 hover:underline"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Dashboard
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-32">
        <div className="md:col-span-2">
          <h1 className="text-3xl font-bold mb-4">{newsItem.title}</h1>
          <div className="text-sm text-muted-foreground mb-4">
            Published on{" "}
            {new Date(newsItem.publication_date).toLocaleDateString()} by{" "}
            {newsItem.author || "Unknown"} in {newsItem.category}
          </div>
          {(() => {
            const mainImageUrl =
              newsItem.source?.image_url ||
              newsItem.source?.media?.[0] ||
              (newsItem as any)?.image_url ||
              (newsItem as any)?.image;
            return mainImageUrl ? (
              <div className="bg-muted rounded-md mb-4 max-h-[400px] overflow-hidden flex items-center justify-center">
                <img
                  src={mainImageUrl}
                  alt={newsItem.title}
                  className="object-cover w-full h-full rounded-md"
                />
              </div>
            ) : null;
          })()}
          <div className="prose dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {newsItem?.markdown_content
                ? newsItem.markdown_content.replace(/\\n/g, "\n")
                : newsItem.content
                  ? newsItem.content.replace(/\\n/g, "\n")
                  : ""}
            </ReactMarkdown>
          </div>
          {newsItem.source?.url && (
            <p className="mt-4 text-sm text-muted-foreground">
              Source:{" "}
              <Link
                href={newsItem.source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 hover:underline"
              >
                {newsItem.source.title || newsItem.source.name || "Link"}
              </Link>
            </p>
          )}
          {newsItem?.location && <Location location={newsItem.location} />}
        </div>

        {/* More News Section */}
        <div className="md:col-span-1">
          <h2 className="text-xl font-bold mb-4">More News</h2>
          {moreNewsItems.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              No other news available.
            </p>
          ) : (
            <ul className="space-y-4">
              {moreNewsItems.map((item) => {
                const itemImageUrl = item.source?.image_url || item.source?.media?.[0];
                return (
                  <li key={item._id || item.id}>
                    <Link
                      href={`/${encodeURIComponent(item.id)}`}
                      className="flex items-start hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md p-2 -mx-2 transition-colors"
                    >
                      {itemImageUrl && (
                        <div className="w-16 h-16 flex-shrink-0 mr-3 overflow-hidden rounded-md bg-muted">
                          <img
                            src={itemImageUrl}
                            alt={item.title}
                            className="object-cover w-full h-full"
                          />
                        </div>
                      )}
                      <div className="flex-grow">
                        <h3 className="text-sm font-semibold leading-tight">
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
      {/* Floating Chat Button */}
      <div className="fixed bottom-6 right-6 z-50">
        {!isChatOpen ? (
          <Button
            onClick={toggleChat}
            className="h-14 w-14 rounded-full shadow-lg flex items-center justify-center"
          >
            <MessageCircle className="h-6 w-6" />
          </Button>
        ) : (
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-80 sm:w-96 flex flex-col"
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
                      className={`mb-4 flex ${msg.isUser ? "justify-end" : "justify-start"
                        }`}
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
                        <div
                          className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                          style={{ animationDelay: "0ms" }}
                        ></div>
                        <div
                          className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                          style={{ animationDelay: "200ms" }}
                        ></div>
                        <div
                          className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
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
    </div>
  );
}
