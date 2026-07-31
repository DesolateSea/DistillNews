"use client";

import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Globe, Check } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useLanguage } from "@/lib/i18n-context";
import { SUPPORTED_LANGUAGES, LanguageCode } from "@/lib/i18n";
import { useFeatureFlag } from "@/lib/feature-flags-context";

export function LanguageToggle() {
  const { language, setLanguage } = useLanguage();
  const [mounted, setMounted] = useState(false);
  const isEnabled = useFeatureFlag("multilingual_support");

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || !isEnabled) {
    return null;
  }

  const currentLangObj = SUPPORTED_LANGUAGES.find((l) => l.code === language) || SUPPORTED_LANGUAGES[0];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-9 px-2.5 rounded-full gap-1.5 text-xs font-semibold hover:bg-accent"
          title="Change UI language"
        >
          <span className="text-base leading-none">{currentLangObj.flag}</span>
          <span className="hidden sm:inline-block uppercase">{currentLangObj.code}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-40">
        {SUPPORTED_LANGUAGES.map((lang) => (
          <DropdownMenuItem
            key={lang.code}
            onClick={() => setLanguage(lang.code)}
            className="flex items-center justify-between cursor-pointer text-xs font-medium"
          >
            <div className="flex items-center gap-2">
              <span className="text-sm">{lang.flag}</span>
              <span>{lang.label}</span>
            </div>
            {language === lang.code && <Check className="h-3.5 w-3.5 text-primary" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
