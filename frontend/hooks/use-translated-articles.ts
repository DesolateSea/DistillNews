"use client";

import { useState, useEffect } from "react";
import { useLanguage } from "@/lib/i18n-context";
import { type NewsItem } from "@/lib/api";
import { translateBatchNews, translateNewsItem } from "@/lib/client-translator";

/**
 * Custom React hook to translate a list of news articles whenever active language changes.
 */
export function useTranslatedArticles(articles: NewsItem[]) {
  const { language } = useLanguage();
  const [translatedArticles, setTranslatedArticles] = useState<NewsItem[]>([]);
  const [isTranslating, setIsTranslating] = useState(true);

  // Reset when language changes so fresh full translation runs
  useEffect(() => {
    setTranslatedArticles([]);
    setIsTranslating(true);
  }, [language]);

  useEffect(() => {
    let isCancelled = false;

    if (!articles || articles.length === 0) {
      setTranslatedArticles([]);
      setIsTranslating(false);
      return;
    }

    // Only trigger full blocking translation if we have 0 articles translated yet
    if (translatedArticles.length === 0) {
      setIsTranslating(true);
    }

    const performTranslation = async () => {
      try {
        const translated = await translateBatchNews(articles, language);
        if (!isCancelled) {
          setTranslatedArticles(translated);
        }
      } catch (err) {
        console.error("Batch translation error:", err);
        if (!isCancelled) {
          setTranslatedArticles(articles);
        }
      } finally {
        if (!isCancelled) {
          setIsTranslating(false);
        }
      }
    };

    performTranslation();

    return () => {
      isCancelled = true;
    };
  }, [articles, language]);

  return { translatedArticles, isTranslating };
}

/**
 * Custom React hook to translate a single article (including full content).
 */
export function useTranslatedArticle(article: NewsItem | null) {
  const { language } = useLanguage();
  const [translatedArticle, setTranslatedArticle] = useState<NewsItem | null>(null);
  const [isTranslating, setIsTranslating] = useState(true);

  useEffect(() => {
    let isCancelled = false;

    if (!article) {
      setTranslatedArticle(null);
      setIsTranslating(false);
      return;
    }

    setIsTranslating(true);

    const performTranslation = async () => {
      try {
        const translated = await translateNewsItem(article, language);
        if (!isCancelled) {
          setTranslatedArticle(translated);
        }
      } catch (err) {
        console.error("Single article translation error:", err);
        if (!isCancelled) {
          setTranslatedArticle(article);
        }
      } finally {
        if (!isCancelled) {
          setIsTranslating(false);
        }
      }
    };

    performTranslation();

    return () => {
      isCancelled = true;
    };
  }, [article, language]);

  return { translatedArticle, isTranslating };
}
