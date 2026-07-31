"use client";

import type React from "react";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Newspaper,
  ArrowLeft,
  LogIn,
  Sparkles,
  Laptop,
  Briefcase,
  Atom,
  HeartPulse,
  Film,
  Trophy,
  Globe,
  Check,
  CheckCheck,
  RotateCcw,
  Sliders,
} from "lucide-react";
import { preferencesApi } from "@/lib/api";

const newsCategories = [
  { id: "Technology", label: "Technology", description: "AI, gadgets, software & big tech", icon: Laptop, color: "text-blue-500 bg-blue-500/10 border-blue-500/20" },
  { id: "Business", label: "Business", description: "Markets, economy, startups & finance", icon: Briefcase, color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20" },
  { id: "Science", label: "Science", description: "Space, physics, climate & discovery", icon: Atom, color: "text-purple-500 bg-purple-500/10 border-purple-500/20" },
  { id: "Health", label: "Health", description: "Medicine, wellness, fitness & research", icon: HeartPulse, color: "text-rose-500 bg-rose-500/10 border-rose-500/20" },
  { id: "Entertainment", label: "Entertainment", description: "Movies, music, culture & streaming", icon: Film, color: "text-amber-500 bg-amber-500/10 border-amber-500/20" },
  { id: "Sports", label: "Sports", description: "Football, basketball, Olympics & games", icon: Trophy, color: "text-orange-500 bg-orange-500/10 border-orange-500/20" },
  { id: "World", label: "World News", description: "Geopolitics, diplomacy & global events", icon: Globe, color: "text-cyan-500 bg-cyan-500/10 border-cyan-500/20" },
];

export default function PreferencesPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingPrefs, setIsFetchingPrefs] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setMounted(true);
    const token = localStorage.getItem("SNAPtoken") || localStorage.getItem("token");
    if (!token) {
      setIsLoggedIn(false);
      setIsFetchingPrefs(false);
      return;
    }

    setIsLoggedIn(true);
    const fetchUserPreferences = async () => {
      setIsFetchingPrefs(true);
      try {
        const data = await preferencesApi.get(token);
        if (Array.isArray(data.preferences)) setSelectedCategories(data.preferences);
      } catch (error) {
        if (error instanceof Error && error.message.includes("404")) {
          console.log("No preferences found for user, starting fresh.");
        } else {
          console.error("Failed to fetch preferences:", error);
        }
      } finally {
        setIsFetchingPrefs(false);
      }
    };

    fetchUserPreferences();
  }, []);

  const handleCategoryToggle = (category: string) => {
    setSelectedCategories((prev) =>
      prev.includes(category)
        ? prev.filter((c) => c !== category)
        : [...prev, category]
    );
  };

  const handleSelectAll = () => {
    setSelectedCategories(newsCategories.map((c) => c.id));
  };

  const handleClearAll = () => {
    setSelectedCategories([]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (selectedCategories.length === 0) {
      alert("Please select at least one topic to personalize your feed");
      return;
    }

    setIsLoading(true);
    const token = localStorage.getItem("SNAPtoken") || localStorage.getItem("token");

    if (!token) {
      alert("Authentication error. Please log in again.");
      router.push("/register");
      setIsLoading(false);
      return;
    }

    try {
      await preferencesApi.save(selectedCategories, token);
      router.push("/dashboard");
    } catch (error) {
      alert("Failed to save preferences. Please try again.");
      console.error("Save preferences error:", error);
      setIsLoading(false);
    }
  };

  if (!mounted || isFetchingPrefs) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <header className="border-b bg-background/95 backdrop-blur">
          <div className="container mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Newspaper className="h-6 w-6 text-primary" />
              <h1 className="text-2xl font-bold">DistillNews</h1>
            </div>
            <Skeleton className="h-9 w-36 rounded-md" />
          </div>
        </header>
        <main className="flex-1 container mx-auto max-w-3xl px-4 py-12 flex flex-col items-center justify-center">
          <div className="w-full space-y-6">
            <div className="text-center space-y-2">
              <Skeleton className="h-8 w-64 mx-auto rounded-md" />
              <Skeleton className="h-4 w-96 mx-auto rounded-md" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-24 w-full rounded-xl" />
              ))}
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="border-b sticky top-0 bg-background/95 backdrop-blur z-40">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Newspaper className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold">DistillNews</h1>
          </Link>

          <Link href="/dashboard">
            <Button variant="outline" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Dashboard
            </Button>
          </Link>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 container mx-auto max-w-4xl px-4 py-10 flex flex-col justify-center">
        {!isLoggedIn ? (
          <Card className="w-full max-w-md mx-auto shadow-xl border-border/60 text-center rounded-2xl overflow-hidden bg-card/80 backdrop-blur">
            <CardHeader className="space-y-3 pb-6 pt-8">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary border border-primary/20 shadow-inner">
                <Sparkles className="h-7 w-7" />
              </div>
              <CardTitle className="text-2xl font-bold">Personalize Your News Feed</CardTitle>
              <CardDescription className="text-sm px-2">
                Sign in to customize your news interests, train your personalized AI recommendation engine, and discover what matters to you.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 pb-8">
              <Link href="/register" className="w-full block">
                <Button size="lg" className="w-full font-semibold shadow-md">
                  <LogIn className="mr-2 h-4 w-4" />
                  Sign In / Register
                </Button>
              </Link>
              <Link href="/dashboard" className="w-full block">
                <Button variant="outline" className="w-full">
                  Continue Browsing as Guest
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-8">
            {/* Header Title Section */}
            <div className="text-center max-w-xl mx-auto space-y-2">
              <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20 mb-1">
                <Sliders className="h-3.5 w-3.5" />
                <span>AI Recommendation Engine</span>
              </div>
              <h2 className="text-3xl font-extrabold tracking-tight">Tune Your News Topics</h2>
              <p className="text-sm text-muted-foreground">
                Select your favorite topics below. Our AI will curate and prioritize stories tailored to your reading profile.
              </p>
            </div>

            {/* Quick Actions Bar */}
            <div className="flex items-center justify-between border-b pb-4">
              <span className="text-xs font-medium text-muted-foreground">
                {selectedCategories.length} of {newsCategories.length} topics selected
              </span>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleSelectAll}
                  className="text-xs h-8 text-primary hover:text-primary"
                >
                  <CheckCheck className="mr-1.5 h-3.5 w-3.5" />
                  Select All
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleClearAll}
                  className="text-xs h-8 text-muted-foreground hover:text-foreground"
                >
                  <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
                  Clear All
                </Button>
              </div>
            </div>

            {/* Category Cards Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {newsCategories.map((cat) => {
                const IconComponent = cat.icon;
                const isSelected = selectedCategories.includes(cat.id);
                return (
                  <div
                    key={cat.id}
                    onClick={() => handleCategoryToggle(cat.id)}
                    className={`relative cursor-pointer p-4 rounded-xl border transition-all duration-200 flex items-start gap-3.5 select-none ${
                      isSelected
                        ? "bg-primary/5 border-primary shadow-md ring-1 ring-primary/30"
                        : "bg-card hover:bg-accent/50 border-border/60 hover:border-border"
                    }`}
                  >
                    <div className={`p-2.5 rounded-lg border flex-shrink-0 ${cat.color}`}>
                      <IconComponent className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0 pr-6">
                      <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                        {cat.label}
                      </h3>
                      <p className="text-xs text-muted-foreground mt-0.5 leading-snug line-clamp-2">
                        {cat.description}
                      </p>
                    </div>
                    <div
                      className={`absolute top-3.5 right-3.5 h-5 w-5 rounded-full border flex items-center justify-center transition-all ${
                        isSelected
                          ? "bg-primary border-primary text-primary-foreground scale-100"
                          : "border-muted-foreground/30 bg-background scale-95"
                      }`}
                    >
                      {isSelected && <Check className="h-3 w-3 stroke-[3]" />}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Action Bar */}
            <div className="pt-4 flex flex-col sm:flex-row items-center justify-between gap-4 border-t">
              <p className="text-xs text-muted-foreground">
                You can adjust your news topic preferences anytime from your dashboard.
              </p>
              <div className="flex items-center gap-3 w-full sm:w-auto">
                <Link href="/dashboard" className="w-full sm:w-auto">
                  <Button type="button" variant="outline" className="w-full sm:w-auto">
                    Cancel
                  </Button>
                </Link>
                <Button
                  type="submit"
                  disabled={isLoading || selectedCategories.length === 0}
                  className="w-full sm:w-auto px-8 font-semibold shadow-md"
                >
                  {isLoading ? (
                    <div className="flex items-center gap-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-foreground" />
                      <span>Saving...</span>
                    </div>
                  ) : (
                    "Save Preferences"
                  )}
                </Button>
              </div>
            </div>
          </form>
        )}
      </main>
    </div>
  );
}
