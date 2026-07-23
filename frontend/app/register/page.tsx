"use client";

import type React from "react";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Newspaper } from "lucide-react";
import { authApi } from "@/lib/api";

export default function AuthPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const data = isLogin
        ? await authApi.login(email, password)
        : await authApi.register(email, password);

      // Save JWT token
      localStorage.setItem("SNAPtoken", data.access_token);

      // Redirect based on login/register
      if (isLogin) {
        router.push("/dashboard");
      } else {
        router.push("/preferences");
      }
    } catch (error) {
      alert(error instanceof Error ? error.message : "Unable to complete the request.");
      console.error("Auth error:", error);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-muted/30">
      <header className="border-b bg-background/80 backdrop-blur">
        <div className="container mx-auto flex max-w-6xl items-center px-4 py-5">
          <Link href="/" className="flex items-center gap-2">
            <Newspaper className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold tracking-tight">DistillNews</h1>
          </Link>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <Card className="w-full max-w-md border-border/60 shadow-xl shadow-primary/5">
          <CardHeader className="space-y-3 pb-6">
            <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
              <Newspaper className="h-5 w-5" />
            </div>
            <CardTitle className="text-2xl tracking-tight">
              {isLogin ? "Welcome Back" : "Create an Account"}
            </CardTitle>
            <CardDescription>
              {isLogin
                ? "Sign in to access your personalized news feed"
                : "Join DistillNews to start receiving tailored news updates"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-5">
                <div className="space-y-2.5">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="your@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2.5">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
                <Button type="submit" className="h-11 w-full" disabled={isLoading}>
                  {isLoading
                    ? "Processing..."
                    : isLogin
                    ? "Sign In"
                    : "Create Account"}
                </Button>
              </div>
            </form>
          </CardContent>
          <CardFooter>
            <div className="text-center w-full">
              {isLogin ? (
                <p>
                  Don't have an account?{" "}
                  <Button
                    variant="link"
                    className="p-0"
                    onClick={() => setIsLogin(false)}
                  >
                    Sign up
                  </Button>
                </p>
              ) : (
                <p>
                  Already have an account?{" "}
                  <Button
                    variant="link"
                    className="p-0"
                    onClick={() => setIsLogin(true)}
                  >
                    Sign in
                  </Button>
                </p>
              )}
            </div>
          </CardFooter>
        </Card>
      </main>
    </div>
  );
}
