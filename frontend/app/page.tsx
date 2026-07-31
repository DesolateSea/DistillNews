"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useFeatureFlag } from "@/lib/feature-flags-context";
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
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Newspaper className="h-6 w-6 text-primary" />
            <span className="text-2xl font-bold">DistillNews</span>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link href="/dashboard">
              <Button variant="outline">Explore News</Button>
            </Link>
            <Link href="/register">
              <Button>
                Sign In
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">

        {/* ── Hero ───────────────────────────────────────────────────────── */}
        <section className="py-20 px-4">
          <div className="container mx-auto max-w-5xl text-center">
            {showHeroBadge && (
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
                <Sparkles className="h-3.5 w-3.5" />
                AI-summarised · Updated daily
              </div>
            )}
            <h1 className="text-4xl md:text-6xl font-bold mb-6">
              Stay informed.{" "}
              <span className="text-primary">Without the noise.</span>
            </h1>
            <p className="text-xl text-muted-foreground mb-10 max-w-3xl mx-auto">
              DistillNews reads thousands of articles so you don't have to.
              Get clear, balanced summaries of what's happening — in seconds.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/dashboard">
                <Button size="lg" variant="outline" className="px-8">
                  Read today's news
                </Button>
              </Link>
              <Link href="/register">
                <Button size="lg" className="px-8">
                  Create account
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
            </div>
          </div>
        </section>

        {/* ── Feature grid ───────────────────────────────────────────────── */}
        <section className="bg-muted py-20 px-4">
          <div className="container mx-auto max-w-6xl">
            <h2 className="text-3xl font-bold text-center mb-12">
              What makes DistillNews different
            </h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              <FeatureCard
                icon={<RefreshCw className="h-10 w-10 text-primary" />}
                title="Fresh every day"
                description="Our AI scans thousands of sources and updates your feed every 24 hours with fresh, relevant content."
              />
              <FeatureCard
                icon={<Filter className="h-10 w-10 text-primary" />}
                title="Your topics, your feed"
                description="Sign in to pick the topics you care about. Your feed will show only what's relevant to you."
              />
              <FeatureCard
                icon={<Shield className="h-10 w-10 text-primary" />}
                title="No bias, no spin"
                description="Our AI removes political bias and sensationalism, delivering balanced and factual news."
              />
              <FeatureCard
                icon={<Zap className="h-10 w-10 text-primary" />}
                title="Short, clear summaries"
                description="Every story is condensed into a quick read. Get the facts without the filler."
              />
              <FeatureCard
                icon={<Newspaper className="h-10 w-10 text-primary" />}
                title="Thousands of sources"
                description="We pull from outlets worldwide so you always get the full picture, not just one perspective."
              />
              <FeatureCard
                icon={<Lightbulb className="h-10 w-10 text-primary" />}
                title="Context included"
                description="Our AI adds background and context so every story makes sense, even if you're hearing about it for the first time."
              />
            </div>
          </div>
        </section>

        {/* ── Bottom CTA ─────────────────────────────────────────────────── */}
        {showBottomCta && (
          <section className="py-20 px-4">
            <div className="container mx-auto max-w-4xl text-center">
              <h2 className="text-3xl font-bold mb-6">Give it a try</h2>
              <p className="text-xl text-muted-foreground mb-10">
                Free to read. No sign-up required to start.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link href="/dashboard">
                  <Button size="lg" variant="outline" className="px-8">
                    Open the news feed
                  </Button>
                </Link>
                <Link href="/register">
                  <Button size="lg" className="px-8">
                    Sign in
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
              </div>
            </div>
          </section>
        )}
      </main>

      {/* ── Footer ─────────────────────────────────────────────────────── */}
      <footer className="border-t py-8">
        <div className="container mx-auto px-4 text-center text-muted-foreground">
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
