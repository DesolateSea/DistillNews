"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
  LanguageCode,
  SUPPORTED_LANGUAGES,
  TRANSLATIONS,
  getStoredLanguage,
  setStoredLanguage as saveLanguageToStorage,
} from "./i18n";
import { useFeatureFlag } from "./feature-flags-context";

interface LanguageContextType {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  t: (key: string, fallback?: string) => string;
}

const LanguageContext = createContext<LanguageContextType>({
  language: "en",
  setLanguage: () => {},
  t: (key: string, fallback?: string) => fallback || key,
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<LanguageCode>("en");
  const isMultilingualEnabled = useFeatureFlag("multilingual_support");

  useEffect(() => {
    setLanguageState(getStoredLanguage());

    const handleLanguageChanged = () => {
      setLanguageState(getStoredLanguage());
    };

    window.addEventListener("language_changed", handleLanguageChanged);
    window.addEventListener("storage", handleLanguageChanged);

    return () => {
      window.removeEventListener("language_changed", handleLanguageChanged);
      window.removeEventListener("storage", handleLanguageChanged);
    };
  }, []);

  const setLanguage = useCallback((lang: LanguageCode) => {
    saveLanguageToStorage(lang);
    setLanguageState(lang);
  }, []);

  const t = useCallback(
    (key: string, fallback?: string): string => {
      // If multilingual flag is disabled, default to English
      const activeLang = isMultilingualEnabled ? language : "en";
      const dict = TRANSLATIONS[activeLang] || TRANSLATIONS.en;
      return dict[key] || TRANSLATIONS.en[key] || fallback || key;
    },
    [language, isMultilingualEnabled]
  );

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
