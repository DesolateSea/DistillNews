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
import { authApi, preferencesApi } from "@/lib/api";

export default function AuthPage() {
  const router = useRouter();
  const [step, setStep] = useState<"email" | "otp">("email");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [sessionToken, setSessionToken] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const res = await authApi.sendOtp(email);
      setSessionToken(res.session_token);
      setStep("otp");
    } catch (error) {
      alert(error instanceof Error ? error.message : "Unable to send verification code. Please try again.");
      console.error("Send OTP error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const data = await authApi.verifyOtp(email, otp, sessionToken);
      
      // Save JWT token
      localStorage.setItem("SNAPtoken", data.access_token);

      // Check if user already has preferences to decide redirect target
      try {
        const prefRes = await preferencesApi.get(data.access_token);
        if (prefRes.preferences && prefRes.preferences.length > 0) {
          router.push("/dashboard");
        } else {
          router.push("/preferences");
        }
      } catch (err) {
        router.push("/preferences");
      }
    } catch (error) {
      alert(error instanceof Error ? error.message : "Invalid or expired verification code.");
      console.error("Verify OTP error:", error);
    } finally {
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
              {step === "email" ? "Sign In / Register" : "Verify Email"}
            </CardTitle>
            <CardDescription>
              {step === "email"
                ? "Join DistillNews or sign in to receive tailored daily news updates"
                : `We sent a 6-digit verification code to ${email}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {step === "email" ? (
              <form onSubmit={handleSendOtp} className="space-y-5">
                <div className="space-y-2.5">
                  <Label htmlFor="email">Email Address</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="your@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
                <Button type="submit" className="h-11 w-full" disabled={isLoading}>
                  {isLoading ? "Sending Code..." : "Send Verification Code"}
                </Button>
              </form>
            ) : (
              <form onSubmit={handleVerifyOtp} className="space-y-5">
                <div className="space-y-2.5">
                  <Label htmlFor="otp">Verification Code (OTP)</Label>
                  <Input
                    id="otp"
                    type="text"
                    placeholder="123456"
                    maxLength={6}
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    required
                  />
                </div>
                <Button type="submit" className="h-11 w-full" disabled={isLoading}>
                  {isLoading ? "Verifying..." : "Verify & Continue"}
                </Button>
                <div className="text-center mt-4">
                  <Button
                    variant="link"
                    type="button"
                    className="text-sm p-0"
                    onClick={() => {
                      setStep("email");
                      setOtp("");
                    }}
                  >
                    Change Email / Re-send Code
                  </Button>
                </div>
              </form>
            )}
          </CardContent>
          <CardFooter className="flex justify-center border-t pt-4 text-xs text-muted-foreground">
            By continuing, you agree to our Terms and Privacy Policy.
          </CardFooter>
        </Card>
      </main>
    </div>
  );
}
