/**
 * Multilingual i18n Localization System for DistillNews.
 *
 * Imports translation dictionaries from frontend/i18n/strings.js
 */

import { strings } from "../i18n/strings.js";

export type LanguageCode = "en" | "es" | "hi" | "fr" | "de";

export interface LanguageOption {
  code: LanguageCode;
  label: string;
  flag: string;
}

export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: "en", label: "English", flag: "🇺🇸" },
  { code: "es", label: "Español", flag: "🇪🇸" },
  { code: "hi", label: "हिन्दी", flag: "🇮🇳" },
  { code: "fr", label: "Français", flag: "🇫🇷" },
  { code: "de", label: "Deutsch", flag: "🇩🇪" },
];

export const TRANSLATIONS: Record<LanguageCode, Record<string, string>> = strings as Record<
  LanguageCode,
  Record<string, string>
>;

const STORAGE_KEY = "distill_news_app_language";

export function getStoredLanguage(): LanguageCode {
  if (typeof window === "undefined") return "en";
  const stored = localStorage.getItem(STORAGE_KEY) as LanguageCode | null;
  if (stored && TRANSLATIONS[stored]) {
    return stored;
  }
  return "en";
}

export function setStoredLanguage(lang: LanguageCode): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, lang);
  window.dispatchEvent(new CustomEvent("language_changed", { detail: { lang } }));
}
