"use client";

import type React from "react";

import { useState, useEffect } from "react";
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
import { ThemeToggle } from "@/components/ThemeToggle";

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

  useEffect(() => {
    // Load Google Identity Services script dynamically
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => {
      const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
      if (clientId && (window as any).google?.accounts?.id) {
        (window as any).google.accounts.id.initialize({
          client_id: clientId,
          callback: handleGoogleCredentialResponse,
        });
      }
    };
    document.body.appendChild(script);

    // Check if returning from Google OAuth popup/redirect hash
    if (typeof window !== "undefined" && window.location.hash) {
      const params = new URLSearchParams(window.location.hash.substring(1));
      const accessToken = params.get("access_token");
      if (accessToken) {
        handleGoogleAccessToken(accessToken);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleGoogleCredentialResponse = async (response: any) => {
    setIsLoading(true);
    try {
      const data = await authApi.googleLogin({ id_token: response.credential });
      localStorage.setItem("SNAPtoken", data.access_token);
      await redirectAfterAuth(data.access_token);
    } catch (err) {
      console.error("Google login error:", err);
      alert("Google Sign-In failed. Please verify your account and try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleAccessToken = async (accessToken: string) => {
    setIsLoading(true);
    try {
      const data = await authApi.googleLogin({ access_token: accessToken });
      localStorage.setItem("SNAPtoken", data.access_token);
      await redirectAfterAuth(data.access_token);
    } catch (err) {
      console.error("Google login error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const redirectAfterAuth = async (token: string) => {
    try {
      const prefRes = await preferencesApi.get(token);
      if (prefRes.preferences && prefRes.preferences.length > 0) {
        router.push("/dashboard");
      } else {
        router.push("/preferences");
      }
    } catch (err) {
      router.push("/preferences");
    }
  };

  const getGoogleClientId = () => {
    const id = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "409464577852-upad91eg01utvi9cplmd06ket3hvihm7.apps.googleusercontent.com";
    if (id && !id.startsWith("http") && (id.includes(".apps.googleusercontent.com") || id.length > 20)) {
      return id;
    }
    return "409464577852-upad91eg01utvi9cplmd06ket3hvihm7.apps.googleusercontent.com";
  };

  const handleGoogleSignIn = () => {
    const clientId = getGoogleClientId();
    if (!clientId) {
      alert(
        "Invalid Google Client ID configuration.\n\n" +
        "Please update NEXT_PUBLIC_GOOGLE_CLIENT_ID in your .env file to your actual Google Cloud OAuth Client ID (e.g., 1234567890-xxx.apps.googleusercontent.com) instead of a URL."
      );
      return;
    }

    if ((window as any).google?.accounts?.oauth2) {
      const client = (window as any).google.accounts.oauth2.initTokenClient({
        client_id: clientId,
        scope: "email profile openid",
        callback: (tokenResponse: any) => {
          if (tokenResponse.access_token) {
            handleGoogleAccessToken(tokenResponse.access_token);
          }
        },
      });
      client.requestAccessToken();
    } else {
      const redirectUri = encodeURIComponent(`${window.location.origin}/register`);
      const oauthUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${encodeURIComponent(clientId)}&redirect_uri=${redirectUri}&response_type=token&scope=openid%20email%20profile`;
      window.location.href = oauthUrl;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-muted/30">
      <header className="border-b bg-background/80 backdrop-blur">
        <div className="container mx-auto flex max-w-6xl items-center justify-between px-4 py-5">
          <Link href="/" className="flex items-center gap-2">
            <Newspaper className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold tracking-tight">DistillNews</h1>
          </Link>
          <ThemeToggle />
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
              <div className="space-y-5">
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

                <div className="relative my-4">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-border" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-card px-2 text-muted-foreground font-medium">Or continue with</span>
                  </div>
                </div>

                <Button
                  type="button"
                  variant="outline"
                  onClick={handleGoogleSignIn}
                  disabled={isLoading}
                  className="h-11 w-full flex items-center justify-center gap-2.5 font-medium border-border shadow-xs hover:bg-accent hover:text-accent-foreground"
                >
                  <svg className="h-5 w-5" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.29v3.14C3.26 21.3 7.31 24 12 24z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.59H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.41l3.99-3.14z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.59l3.99 3.14c.95-2.83 3.6-4.98 6.72-4.98z"
                    />
                  </svg>
                  <span>Sign in with Google</span>
                </Button>
              </div>
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
          <CardFooter className="flex flex-col items-center gap-2 border-t pt-4 text-xs text-muted-foreground">
            <Link href="/dashboard" className="text-sm font-medium text-primary hover:underline">
              Continue reading as Guest &rarr;
            </Link>
            <span>By continuing, you agree to our Terms and Privacy Policy.</span>
          </CardFooter>
        </Card>
      </main>
    </div>
  );
}
