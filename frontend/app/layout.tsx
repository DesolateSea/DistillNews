import type React from "react";
import type { Metadata } from "next";
import Script from "next/script"; // <-- Add this
import { Inter } from "next/font/google";
import "./globals.css";
import { FeatureFlagsProvider } from "@/lib/feature-flags-context";
import { LanguageProvider } from "@/lib/i18n-context";
import { ThemeProvider } from "@/components/theme-provider";
import { ScrollToTop } from "@/components/ScrollToTop";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "DistillNews - AI-Powered News Aggregator",
  description: "Get personalized, unbiased news updates curated by AI",
  generator: "v0.dev",
  verification: {
    google: "bXi3KBr2xxscbMEqu8L-9YpLCoJZfGcvd45r-NcThHc",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Script
          src="/runtime-env.js"
          strategy="beforeInteractive"
        />

        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <FeatureFlagsProvider>
            <LanguageProvider>
              {children}
              <ScrollToTop />
            </LanguageProvider>
          </FeatureFlagsProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}