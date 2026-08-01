"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LanguageToggle } from "@/components/LanguageToggle";
import { useLanguage } from "@/lib/i18n-context";
import { useFeatureFlag } from "@/lib/feature-flags-context";
import { HeadlinesBanner } from "@/components/HeadlinesBanner";
import {
  ArrowRight,
  Newspaper,
  Zap,
  Filter,
  RefreshCw,
  Shield,
  Lightbulb,
  Sparkles,
} from "lucide-react";

export default function HomePage() {
  const [mounted, setMounted] = useState(false);
  const { t } = useLanguage();

  useEffect(() => { setMounted(true); }, []);

  // Always call hooks unconditionally
  const heroBadgeFlag   = useFeatureFlag("landing_hero_badge");
  const bottomCtaFlag   = useFeatureFlag("landing_sample_articles");

  // Before hydration completes, show everything (matches SSR defaults which are all true)
  const showHeroBadge   = !mounted || heroBadgeFlag;
  const showBottomCta   = !mounted || bottomCtaFlag;

  return (
    <div className="flex flex-col min-h-screen">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="border-b bg-background/95 backdrop-blur sticky top-0 z-40">
        <div className="container mx-auto px-3 sm:px-4 py-3 sm:py-4 flex justify-between items-center gap-2">
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <Newspaper className="h-5 w-5 sm:h-6 sm:w-6 text-primary" />
            <span className="text-lg sm:text-2xl font-bold tracking-tight">DistillNews</span>
          </Link>
          <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
            <LanguageToggle />
            <ThemeToggle />
            <Link href="/dashboard" className="hidden sm:inline-flex">
              <Button variant="outline" size="sm" className="h-9 px-2.5 sm:px-4 text-xs sm:text-sm">
                <span>{t("explore_news")}</span>
              </Button>
            </Link>
            <Link href="/register">
              <Button size="sm" className="h-9 px-2.5 sm:px-4 text-xs sm:text-sm">
                <span className="hidden xs:inline">{t("sign_in")}</span>
                <ArrowRight className="h-3.5 w-3.5 sm:ml-1.5 sm:h-4 sm:w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">

        {/* ── Hero ───────────────────────────────────────────────────────── */}
        <section className="pt-1 sm:pt-4 pb-4 sm:pb-8">
          <div className="container mx-auto px-3 sm:px-4">
            <div className="text-left mb-3 sm:mb-5">
              <HeadlinesBanner variant="full" />
            </div>
            <div className="max-w-4xl mx-auto text-center">
              {showHeroBadge && (
                <div className="inline-flex items-center gap-1.5 sm:gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs sm:text-sm font-medium mb-2 sm:mb-3">
                  <Sparkles className="h-3.5 w-3.5" />
                  {t("hero_badge")}
                </div>
              )}
              <h1 className="text-3xl xs:text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight mb-2 sm:mb-4 leading-tight">
                {t("hero_title_1")}{" "}
                <span className="text-primary">{t("hero_title_2")}</span>
              </h1>
              <p className="text-base sm:text-xl text-muted-foreground mb-4 sm:mb-6 max-w-3xl mx-auto px-2">
                {t("hero_subtitle")}
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-2.5 sm:gap-4 max-w-md sm:max-w-none mx-auto">
                <Link href="/dashboard" className="w-full sm:w-auto">
                  <Button size="lg" variant="outline" className="w-full sm:w-auto px-5 sm:px-8 h-10 sm:h-12 text-sm sm:text-base">
                    {t("read_todays_news")}
                  </Button>
                </Link>
                <Link href="/register" className="w-full sm:w-auto">
                  <Button size="lg" className="w-full sm:w-auto px-5 sm:px-8 h-10 sm:h-12 text-sm sm:text-base">
                    {t("create_account")}
                    <ArrowRight className="ml-2 h-4 w-4 sm:h-5 sm:w-5" />
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* ── Feature grid ───────────────────────────────────────────────── */}
        <section className="bg-muted/50 py-8 sm:py-16 px-4 hidden sm:block">
          <div className="container mx-auto max-w-6xl">
            <h2 className="text-2xl sm:text-3xl font-bold text-center mb-6 sm:mb-10">
              {t("what_makes_different")}
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-8">
              <FeatureCard
                icon={<RefreshCw className="h-8 w-8 sm:h-10 sm:w-10 text-primary" />}
                title={t("fresh_every_day")}
                description={t("fresh_every_day_desc")}
              />
              <FeatureCard
                icon={<Filter className="h-8 w-8 sm:h-10 sm:w-10 text-primary" />}
                title={t("your_topics_your_feed")}
                description={t("your_topics_desc")}
              />
              <FeatureCard
                icon={<Shield className="h-8 w-8 sm:h-10 sm:w-10 text-primary" />}
                title={t("no_bias_no_spin")}
                description={t("no_bias_desc")}
              />
              <FeatureCard
                icon={<Zap className="h-8 w-8 sm:h-10 sm:w-10 text-primary" />}
                title={t("short_clear_summaries")}
                description={t("short_summaries_desc")}
              />
              <FeatureCard
                icon={<Newspaper className="h-8 w-8 sm:h-10 sm:w-10 text-primary" />}
                title={t("thousands_of_sources")}
                description={t("sources_desc")}
              />
              <FeatureCard
                icon={<Lightbulb className="h-8 w-8 sm:h-10 sm:w-10 text-primary" />}
                title={t("context_included")}
                description={t("context_desc")}
              />
            </div>
          </div>
        </section>

        {/* ── Bottom CTA ─────────────────────────────────────────────────── */}
        {showBottomCta && (
          <section className="py-6 sm:py-12 px-4">
            <div className="container mx-auto max-w-4xl text-center">
              <h2 className="text-2xl sm:text-3xl font-bold mb-2 sm:mb-4">Give it a try</h2>
              <p className="text-base sm:text-xl text-muted-foreground mb-4 sm:mb-6">
                Free to read. No sign-up required to start.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 max-w-md sm:max-w-none mx-auto">
                <Link href="/dashboard" className="w-full sm:w-auto">
                  <Button size="lg" variant="outline" className="w-full sm:w-auto px-6 sm:px-8 h-11 sm:h-12 text-sm sm:text-base">
                    Open the news feed
                  </Button>
                </Link>
                <Link href="/register" className="w-full sm:w-auto">
                  <Button size="lg" className="w-full sm:w-auto px-6 sm:px-8 h-11 sm:h-12 text-sm sm:text-base">
                    Sign in
                    <ArrowRight className="ml-2 h-4 w-4 sm:h-5 sm:w-5" />
                  </Button>
                </Link>
              </div>
            </div>
          </section>
        )}
      </main>

      {/* ── Footer ─────────────────────────────────────────────────────── */}
      <footer className="border-t py-4 sm:py-6">
        <div className="container mx-auto px-4 text-center text-xs sm:text-sm text-muted-foreground">
          <p>© {new Date().getFullYear()} DistillNews. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="bg-background p-6 rounded-lg shadow-sm border">
      <div className="mb-4">{icon}</div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-muted-foreground">{description}</p>
    </div>
  );
}
