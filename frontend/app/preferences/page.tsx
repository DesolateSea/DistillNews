"use client";

import type React from "react";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Newspaper, ArrowLeft } from "lucide-react"; // Import ArrowLeft icon (optional)
import { preferencesApi } from "@/lib/api";

const newsCategories = [
  { id: "Technology", label: "Technology" },
  { id: "Business", label: "Business" },
  { id: "Science", label: "Science" },
  { id: "Health", label: "Health" },
  { id: "Entertainment", label: "Entertainment" },
  { id: "Sports", label: "Sports" },
  { id: "World", label: "World News" },
];

export default function PreferencesPage() {
  const router = useRouter();
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingPrefs, setIsFetchingPrefs] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("SNAPtoken");
    if (!token) {
      router.push("/register");
      return;
    }

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
          alert("Could not load your saved preferences. Please try again.");
        }
      } finally {
        setIsFetchingPrefs(false);
      }
    };

    fetchUserPreferences();
  }, [router]);

  const handleCategoryChange = (category: string) => {
    setSelectedCategories((prev) =>
      prev.includes(category)
        ? prev.filter((c) => c !== category)
        : [...prev, category]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (selectedCategories.length === 0) {
      alert("Please select at least one category");
      return;
    }

    setIsLoading(true);
    const token = localStorage.getItem("SNAPtoken");

    if (!token) {
      alert("Authentication error. Please log in again.");
      router.push("/register");
      setIsLoading(false);
      return;
    }

    try {
      await preferencesApi.save(selectedCategories, token);

      router.push("/dashboard"); // Navigate to dashboard after successful save
    } catch (error) {
      alert(
        "Failed to connect to the server to save preferences. Please try again."
      );
      console.error("Save preferences error:", error);
      setIsLoading(false);
    }
  };

  if (isFetchingPrefs) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading your preferences...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* ===== HEADER MODIFICATION ===== */}
      <header className="border-b sticky top-0 bg-background z-10">
        {" "}
        {/* Optional: make header sticky */}
        {/* Apply flex layout to the container */}
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          {/* Logo and Title */}
          <Link href="/" className="flex items-center gap-2">
            <Newspaper className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold">DistillNews</h1>
          </Link>

          {/* Back Button */}
          <Link href="/dashboard" passHref>
            <Button variant="outline" size="sm">
              {" "}
              {/* Use Button component, maybe smaller size */}
              <ArrowLeft className="mr-2 h-4 w-4" /> {/* Optional Icon */}
              Back to Dashboard
            </Button>
          </Link>
        </div>
      </header>
      {/* ===== END HEADER MODIFICATION ===== */}

      <main className="flex-1 flex items-center justify-center p-4 mt-4">
        {" "}
        {/* Add margin-top if header is sticky */}
        <Card className="w-full max-w-lg">
          <CardHeader>
            <CardTitle>Set Your News Preferences</CardTitle>
            <CardDescription>
              Select the topics you're interested in to personalize your news
              feed
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                {newsCategories.map((category) => (
                  <div
                    key={category.id}
                    className="flex items-center space-x-2"
                  >
                    <Checkbox
                      id={category.id}
                      checked={selectedCategories.includes(category.id)}
                      onCheckedChange={() => handleCategoryChange(category.id)}
                      // disabled={isFetchingPrefs || isLoading} // Keep disabled state if needed
                    />
                    <Label htmlFor={category.id}>{category.label}</Label>
                  </div>
                ))}
              </div>
              <Button
                type="submit"
                className="w-full"
                disabled={isLoading || isFetchingPrefs}
              >
                {isLoading ? "Saving..." : "Save Preferences"}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="flex justify-center">
            <p className="text-sm text-muted-foreground">
              You can always update your preferences later
            </p>
          </CardFooter>
        </Card>
      </main>
    </div>
  );
}
