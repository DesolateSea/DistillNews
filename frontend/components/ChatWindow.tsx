"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { MessageCircle, X, Send } from "lucide-react";
import { ChatFab } from "@/components/ChatFab";

interface ChatMessage {
  text: string;
  isUser: boolean;
  timestamp: Date;
}

interface ChatWindowProps {
  isOpen: boolean;
  onClose: () => void;
  messages: ChatMessage[];
  isTyping: boolean;
  inputMessage: string;
  setInputMessage: (val: string) => void;
  sendMessage: (e: React.FormEvent) => void;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  inputRef: React.RefObject<HTMLInputElement | null>;
  title?: string;
  placeholder?: string;
  emptyStateText?: string;
}

export function ChatWindow({
  isOpen,
  onClose,
  messages,
  isTyping,
  inputMessage,
  setInputMessage,
  sendMessage,
  messagesEndRef,
  inputRef,
  title = "Chat Assistant",
  placeholder = "Type your message...",
  emptyStateText = "Ask me anything!",
}: ChatWindowProps) {
  // Size state (width & height in px)
  const [size, setSize] = useState({ width: 520, height: 680 });

  const isResizingRef = useRef(false);
  const dragStartRef = useRef<{
    mouseX: number;
    mouseY: number;
    initialWidth: number;
    initialHeight: number;
  }>({
    mouseX: 0,
    mouseY: 0,
    initialWidth: 520,
    initialHeight: 680,
  });

  const handleMouseDownTopLeft = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isResizingRef.current = true;
    dragStartRef.current = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      initialWidth: size.width,
      initialHeight: size.height,
    };
    document.body.style.userSelect = "none";
  }, [size]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizingRef.current) return;

      const deltaX = e.clientX - dragStartRef.current.mouseX;
      const deltaY = e.clientY - dragStartRef.current.mouseY;

      // Resizing from Top-Left while bottom-right corner stays anchored fixed:
      // Moving mouse left (deltaX < 0) expands width
      // Moving mouse up (deltaY < 0) expands height
      const minWidth = 320;
      const maxWidth = window.innerWidth - 32;
      const minHeight = 400;
      const maxHeight = window.innerHeight - 32;

      let newWidth = dragStartRef.current.initialWidth - deltaX;
      let newHeight = dragStartRef.current.initialHeight - deltaY;

      newWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));
      newHeight = Math.max(minHeight, Math.min(maxHeight, newHeight));

      setSize({ width: newWidth, height: newHeight });
    };

    const handleMouseUp = () => {
      if (isResizingRef.current) {
        isResizingRef.current = false;
        document.body.style.userSelect = "";
      }
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  if (!isOpen) {
    return <ChatFab onClick={onClose} />;
  }

  return (
    <>
      {/* Mobile overlay backdrop */}
      <div
        className="fixed inset-0 bg-background/80 backdrop-blur-xs sm:hidden z-40"
        onClick={onClose}
      />

      <div
        style={{
          width: `${size.width}px`,
          height: `${size.height}px`,
        }}
        className="fixed inset-x-3 bottom-3 top-14 sm:top-auto sm:left-auto sm:right-0 sm:bottom-0 max-w-[95vw] max-h-[90vh] sm:max-w-none sm:max-h-none bg-card border border-border rounded-2xl shadow-2xl z-50 flex flex-col overflow-hidden transition-none"
      >
        {/* Top-Left Resize Handle */}
        <div
          onMouseDown={handleMouseDownTopLeft}
          className="hidden sm:flex absolute top-0 left-0 w-7 h-7 z-50 cursor-nwse-resize items-center justify-center group"
          title="Resize from Top-Left"
        >
          <div className="w-3 h-3 border-t-2 border-l-2 border-primary/50 group-hover:border-primary group-hover:scale-110 transition-all rounded-tl-sm mt-1 ml-1" />
        </div>

        {/* Chat Header */}
        <div className="p-3.5 sm:p-4 border-b flex justify-between items-center bg-muted/30 select-none">
          <h3 className="font-semibold text-sm sm:text-base pl-2">{title}</h3>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 rounded-full"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 p-3.5 sm:p-4 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center text-center text-muted-foreground">
              <div>
                <MessageCircle className="h-10 w-10 mx-auto mb-2 opacity-50" />
                <p className="text-xs sm:text-sm">{emptyStateText}</p>
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`mb-4 flex ${
                    msg.isUser ? "justify-end" : "justify-start"
                  }`}
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
                    <div
                      className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce"
                      style={{ animationDelay: "0ms" }}
                    />
                    <div
                      className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce"
                      style={{ animationDelay: "200ms" }}
                    />
                    <div
                      className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce"
                      style={{ animationDelay: "400ms" }}
                    />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Chat Input */}
        <form
          onSubmit={sendMessage}
          className="p-3 sm:p-4 border-t flex gap-2 bg-background"
        >
          <input
            type="text"
            ref={inputRef}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder={placeholder}
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
  );
}
