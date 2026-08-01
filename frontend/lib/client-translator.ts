/**
 * Client-side Translation Engine for DistillNews using Google Free Translate API.
 * 
 * Includes 2-level caching (In-Memory L1 + LocalStorage L2) to eliminate duplicate requests,
 * ensuring zero cost, high speed, and instant fallback to English.
 */

import { LanguageCode } from "./i18n";
import { type NewsItem } from "./api";

const memoryTranslationCache = new Map<string, string>();

function getStorageKey(lang: string, text: string): string {
  // Simple hash for long strings to keep key concise
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    hash = (hash << 5) - hash + text.charCodeAt(i);
    hash |= 0;
  }
  return `distill_tr_${lang}_${hash}`;
}

function isLikelyNonEnglish(text: string): boolean {
  return /[^\x00-\x7F]/.test(text);
}

/**
 * Translate a single text string using Google's free translation service.
 */
export async function translateText(text: string, targetLang: LanguageCode): Promise<string> {
  if (!text || !text.trim()) {
    return text;
  }

  // If target is English and text is already pure ASCII English, skip fetch
  if (targetLang === "en" && !isLikelyNonEnglish(text)) {
    return text;
  }

  const cacheKey = getStorageKey(targetLang, text);

  // 1. Check L1 Memory Cache
  if (memoryTranslationCache.has(cacheKey)) {
    return memoryTranslationCache.get(cacheKey)!;
  }

  // 2. Check L2 LocalStorage Cache
  if (typeof window !== "undefined" && window.localStorage) {
    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        memoryTranslationCache.set(cacheKey, cached);
        return cached;
      }
    } catch {
      // ignore storage errors
    }
  }

  // 3. Fetch from Google Free Translate API (CORS friendly)
  try {
    const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=${targetLang}&dt=t&q=${encodeURIComponent(
      text
    )}`;

    const response = await fetch(url);
    if (!response.ok) return text;

    const data = await response.json();
    if (data && Array.isArray(data[0])) {
      const translated = data[0]
        .map((part: [string, ...unknown[]]) => part[0])
        .filter(Boolean)
        .join("");

      if (translated) {
        // Store in L1 and L2 caches
        memoryTranslationCache.set(cacheKey, translated);
        if (typeof window !== "undefined" && window.localStorage) {
          try {
            localStorage.setItem(cacheKey, translated);
          } catch {
            // ignore storage full errors
          }
        }
        return translated;
      }
    }
  } catch (error) {
    console.warn("Client translation failed for text, falling back to original:", error);
  }

  return text;
}

/**
 * Translate a NewsItem's title and summary on the client side.
 */
export async function translateNewsItem(item: NewsItem, targetLang: LanguageCode): Promise<NewsItem> {
  if (!item) return item;
  if (targetLang === "en" && !isLikelyNonEnglish(item.title) && !isLikelyNonEnglish(item.summary)) {
    return item;
  }

  const [translatedTitle, translatedSummary] = await Promise.all([
    translateText(item.title, targetLang),
    translateText(item.summary, targetLang),
  ]);

  let translatedContent = item.content;
  let translatedMarkdown = item.markdown_content;

  if (item.content) {
    translatedContent = await translateText(item.content, targetLang);
  }
  if (item.markdown_content) {
    translatedMarkdown = await translateText(item.markdown_content, targetLang);
  }

  return {
    ...item,
    title: translatedTitle,
    summary: translatedSummary,
    content: translatedContent,
    markdown_content: translatedMarkdown,
  };
}

/**
 * Batch translate a list of NewsItems (titles and summaries only for fast card rendering).
 */
export async function translateBatchNews(items: NewsItem[], targetLang: LanguageCode): Promise<NewsItem[]> {
  if (!items || items.length === 0) return items;

  return Promise.all(
    items.map(async (item) => {
      if (targetLang === "en" && !isLikelyNonEnglish(item.title) && !isLikelyNonEnglish(item.summary)) {
        return item;
      }

      const [translatedTitle, translatedSummary] = await Promise.all([
        translateText(item.title, targetLang),
        translateText(item.summary, targetLang),
      ]);

      return {
        ...item,
        title: translatedTitle,
        summary: translatedSummary,
      };
    })
  );
}
