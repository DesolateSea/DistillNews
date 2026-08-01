"use client";

import React, { useEffect, useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";
import { useLanguage } from "@/lib/i18n-context";
import { SUPPORTED_LANGUAGES } from "@/lib/i18n";
import { useFeatureFlag } from "@/lib/feature-flags-context";

export function LanguageToggle() {
  const { language, setLanguage } = useLanguage();
  const [mounted, setMounted] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const isEnabled = useFeatureFlag("multilingual_support");
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  if (!mounted || !isEnabled) {
    return null;
  }

  const currentLangObj = SUPPORTED_LANGUAGES.find((l) => l.code === language) || SUPPORTED_LANGUAGES[0];

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="h-9 px-2 sm:px-2.5 rounded-full gap-1 text-xs font-semibold hover:bg-accent"
        title="Change UI language"
        aria-expanded={isOpen}
      >
        <span className="text-sm leading-none">{currentLangObj.flag}</span>
        <span className="hidden sm:inline-block uppercase">{currentLangObj.code}</span>
      </Button>

      {isOpen && (
        <div className="absolute right-0 mt-1 w-40 rounded-xl bg-popover text-popover-foreground shadow-lg border border-border p-1 z-50 animate-in fade-in-80 zoom-in-95">
          {SUPPORTED_LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => {
                setLanguage(lang.code);
                setIsOpen(false);
              }}
              className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium hover:bg-accent hover:text-accent-foreground transition-colors text-left"
            >
              <div className="flex items-center gap-2">
                <span className="text-sm">{lang.flag}</span>
                <span>{lang.label}</span>
              </div>
              {language === lang.code && <Check className="h-3.5 w-3.5 text-primary" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
