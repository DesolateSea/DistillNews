"use client";

import type React from "react";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
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
  CheckCheck,
  RotateCcw,
} from "lucide-react";
import { preferencesApi } from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";

type DesignVariant = "minimal" | "classic";

const newsCategories = [
  { id: "Technology", label: "Technology", description: "AI, software, gadgets & tech news" },
  { id: "Business", label: "Business", description: "Markets, startups & global economy" },
  { id: "Science", label: "Science", description: "Space, physics & environmental research" },
  { id: "Health", label: "Health", description: "Medicine, wellness & healthcare" },
  { id: "Entertainment", label: "Entertainment", description: "Movies, music & culture" },
  { id: "Sports", label: "Sports", description: "Athletics, leagues & major tournaments" },
  { id: "World", label: "World News", description: "Global affairs & international news" },
];

export default function PreferencesPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingPrefs, setIsFetchingPrefs] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  // Feature Flag: Read directly from localStorage or env
  const [designVariant, setDesignVariant] = useState<DesignVariant>("minimal");

  useEffect(() => {
    setMounted(true);
    if (typeof window !== "undefined") {
      // Feature Flag Lookup from localStorage or env
      const storedVariant = localStorage.getItem("PREFERENCES_DESIGN_VARIANT") as DesignVariant | null;
      const envVariant = (process.env.NEXT_PUBLIC_PREFERENCES_DESIGN || "minimal").toLowerCase() as DesignVariant;
      const activeVariant = storedVariant || (envVariant === "classic" ? "classic" : "minimal");
      setDesignVariant(activeVariant);

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
    }
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
            <div className="flex items-center gap-3">
              <ThemeToggle />
              <Skeleton className="h-9 w-36 rounded-md" />
            </div>
          </div>
        </header>
        <main className="flex-1 container mx-auto max-w-2xl px-4 py-12">
          <div className="space-y-4">
            <Skeleton className="h-8 w-64 rounded-md" />
            <Skeleton className="h-4 w-96 rounded-md" />
            <div className="space-y-3 pt-4">
              {Array.from({ length: 7 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full rounded-xl" />
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

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link href="/dashboard">
              <Button variant="outline" size="sm" className="rounded-full">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Dashboard
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 container mx-auto max-w-2xl px-4 py-10">
        {!isLoggedIn ? (
          <Card className="w-full max-w-md mx-auto my-12 shadow-sm border-border/60 text-center rounded-2xl bg-card">
            <CardHeader className="space-y-3 pb-6 pt-8">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Sparkles className="h-6 w-6" />
              </div>
              <CardTitle className="text-2xl font-bold">Personalize Your Feed</CardTitle>
              <CardDescription className="text-sm">
                Sign in to customize your favorite news topics and train your personal AI feed.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 pb-8">
              <Link href="/register" className="w-full block">
                <Button size="lg" className="w-full font-semibold rounded-xl">
                  <LogIn className="mr-2 h-4 w-4" />
                  Sign In / Register
                </Button>
              </Link>
              <Link href="/dashboard" className="w-full block">
                <Button variant="outline" className="w-full rounded-xl">
                  Continue Browsing as Guest
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : designVariant === "classic" ? (
          /* ========================================================= */
          /* CLASSIC BACKWARD-COMPATIBLE DESIGN VARIANT               */
          /* ========================================================= */
          <Card className="w-full shadow-sm border-border/70 rounded-2xl">
            <CardHeader>
              <CardTitle className="text-2xl font-bold">Set Your News Preferences</CardTitle>
              <CardDescription>
                Select the topics you're interested in to personalize your news feed
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {newsCategories.map((category) => (
                    <div
                      key={category.id}
                      className="flex items-center space-x-3 p-2 rounded-lg hover:bg-muted/40 transition-colors"
                    >
                      <Checkbox
                        id={`classic-${category.id}`}
                        checked={selectedCategories.includes(category.id)}
                        onCheckedChange={() => handleCategoryToggle(category.id)}
                      />
                      <Label
                        htmlFor={`classic-${category.id}`}
                        className="text-sm font-medium cursor-pointer flex-1"
                      >
                        {category.label}
                      </Label>
                    </div>
                  ))}
                </div>
                <Button
                  type="submit"
                  className="w-full font-semibold rounded-xl"
                  disabled={isLoading || selectedCategories.length === 0}
                >
                  {isLoading ? "Saving..." : "Save Preferences"}
                </Button>
              </form>
            </CardContent>
          </Card>
        ) : (
          /* ========================================================= */
          /* CLEAN MINIMAL SLEEK DESIGN VARIANT (DEFAULT)             */
          /* ========================================================= */
          <Card className="w-full shadow-sm border-border/70 rounded-2xl overflow-hidden bg-card">
            <CardHeader className="border-b bg-muted/20 pb-6 pt-6">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <CardTitle className="text-2xl font-bold">News Preferences</CardTitle>
                  <CardDescription className="text-sm mt-1">
                    Toggle the topics you want to prioritize in your news feed.
                  </CardDescription>
                </div>
                <div className="flex items-center gap-1.5 bg-background p-1 rounded-lg border text-xs">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleSelectAll}
                    className="text-xs h-7 px-2.5 rounded text-muted-foreground hover:text-foreground"
                  >
                    <CheckCheck className="mr-1 h-3 w-3" />
                    All
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleClearAll}
                    className="text-xs h-7 px-2.5 rounded text-muted-foreground hover:text-foreground"
                  >
                    <RotateCcw className="mr-1 h-3 w-3" />
                    None
                  </Button>
                </div>
              </div>
            </CardHeader>

            <CardContent className="p-6">
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="divide-y divide-border/50 border rounded-xl overflow-hidden bg-background">
                  {newsCategories.map((cat) => {
                    const isSelected = selectedCategories.includes(cat.id);
                    return (
                      <div
                        key={cat.id}
                        onClick={() => handleCategoryToggle(cat.id)}
                        className={`p-4 flex items-center justify-between gap-4 cursor-pointer transition-colors ${
                          isSelected ? "bg-primary/[0.02]" : "hover:bg-muted/30"
                        }`}
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-foreground">
                            {cat.label}
                          </p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {cat.description}
                          </p>
                        </div>

                        <Switch
                          checked={isSelected}
                          onCheckedChange={() => handleCategoryToggle(cat.id)}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </div>
                    );
                  })}
                </div>

                <div className="pt-4 flex items-center justify-between gap-4">
                  <p className="text-xs text-muted-foreground">
                    {selectedCategories.length} of {newsCategories.length} topics selected
                  </p>

                  <div className="flex items-center gap-3">
                    <Link href="/dashboard">
                      <Button type="button" variant="outline" size="sm" className="rounded-xl px-5">
                        Cancel
                      </Button>
                    </Link>
                    <Button
                      type="submit"
                      disabled={isLoading || selectedCategories.length === 0}
                      size="sm"
                      className="rounded-xl px-6 font-semibold"
                    >
                      {isLoading ? (
                        <div className="flex items-center gap-2">
                          <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-primary-foreground" />
                          <span>Saving...</span>
                        </div>
                      ) : (
                        "Save Preferences"
                      )}
                    </Button>
                  </div>
                </div>
              </form>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
