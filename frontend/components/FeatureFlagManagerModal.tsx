"use client";

import React, { useState } from "react";
import { useFeatureFlags } from "@/lib/feature-flags-context";
import { Button } from "@/components/ui/button";
import { Sliders, X, RotateCcw, Check, Zap } from "lucide-react";

export function FeatureFlagManagerModal() {
  const [isOpen, setIsOpen] = useState(false);
  const { systemFlags, isFeatureEnabled, toggleFeatureFlag, resetToDefaults } = useFeatureFlags();

  return (
    <>
      {/* Floating Toggle Button */}
      <div className="fixed bottom-6 left-6 z-50">
        <Button
          onClick={() => setIsOpen(!isOpen)}
          variant="outline"
          size="sm"
          className="rounded-full shadow-lg bg-background/90 backdrop-blur border border-primary/30 hover:border-primary text-xs font-semibold flex items-center gap-2 px-3 py-2"
        >
          <Sliders className="h-4 w-4 text-primary" />
          <span>Feature Flags</span>
        </Button>
      </div>

      {/* Modal Dialog */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-card border rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden flex flex-col max-h-[85vh]">
            {/* Header */}
            <div className="p-5 border-b flex justify-between items-center bg-muted/30">
              <div className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-primary" />
                <div>
                  <h3 className="font-bold text-base">Frontend Feature Flags</h3>
                  <p className="text-xs text-muted-foreground">Stored in & read directly from LocalStorage</p>
                </div>
              </div>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setIsOpen(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* List of Flags */}
            <div className="p-5 overflow-y-auto space-y-3 flex-1">
              {systemFlags.map((flag) => {
                const enabled = isFeatureEnabled(flag.id);
                return (
                  <div
                    key={flag.id}
                    className={`p-4 rounded-xl border transition-all flex items-center justify-between gap-4 ${
                      enabled
                        ? "bg-primary/5 border-primary/30"
                        : "bg-background border-border/60 opacity-80"
                    }`}
                  >
                    <div className="flex-1 pr-2">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm">{flag.name}</span>
                        <code className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
                          {flag.id}
                        </code>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{flag.description}</p>
                    </div>

                    {/* Switch Toggle */}
                    <button
                      onClick={() => toggleFeatureFlag(flag.id)}
                      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                        enabled ? "bg-primary" : "bg-muted-foreground/30"
                      }`}
                      role="switch"
                      aria-checked={enabled}
                    >
                      <span
                        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-background shadow ring-0 transition duration-200 ease-in-out ${
                          enabled ? "translate-x-5" : "translate-x-0"
                        }`}
                      />
                    </button>
                  </div>
                );
              })}
            </div>

            {/* Footer */}
            <div className="p-4 border-t bg-muted/20 flex justify-between items-center">
              <Button
                variant="outline"
                size="sm"
                onClick={resetToDefaults}
                className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Reset Defaults
              </Button>
              <Button size="sm" onClick={() => setIsOpen(false)} className="text-xs px-4">
                <Check className="h-3.5 w-3.5 mr-1" />
                Done
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
