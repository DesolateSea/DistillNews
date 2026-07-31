"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
  SYSTEM_FEATURE_FLAGS,
  FeatureFlag,
  getAllFeatureFlags,
  isFeatureEnabled as readFlag,
  toggleFeatureFlag as toggleFlagInStorage,
  resetFeatureFlagsToDefault,
} from "./feature-flags";

interface FeatureFlagsContextType {
  /** Map of flagId → enabled (kept in sync with localStorage) */
  flagMap: Record<string, boolean>;
  systemFlags: FeatureFlag[];
  isFeatureEnabled: (flagId: string) => boolean;
  toggleFeatureFlag: (flagId: string) => void;
  resetToDefaults: () => void;
  isLoaded: boolean;
}

const FeatureFlagsContext = createContext<FeatureFlagsContextType>({
  flagMap: {},
  systemFlags: SYSTEM_FEATURE_FLAGS,
  isFeatureEnabled: () => false,
  toggleFeatureFlag: () => {},
  resetToDefaults: () => {},
  isLoaded: false,
});

export function FeatureFlagsProvider({ children }: { children: React.ReactNode }) {
  const [flagMap, setFlagMap] = useState<Record<string, boolean>>({});
  const [isLoaded, setIsLoaded] = useState(false);

  const syncFromStorage = useCallback(() => {
    setFlagMap(getAllFeatureFlags());
    setIsLoaded(true);
  }, []);

  useEffect(() => {
    // Remove legacy single-array key from the old flag system
    localStorage.removeItem("distill_news_enabled_feature_flags");

    syncFromStorage();

    // React to cross-tab changes (native storage event)
    const handleStorageEvent = (e: StorageEvent) => {
      if (e.key?.startsWith("ff_") || e.key === null) {
        syncFromStorage();
      }
    };

    // React to same-tab changes (custom event dispatched by setFeatureFlag)
    const handleCustomEvent = () => syncFromStorage();

    window.addEventListener("storage", handleStorageEvent);
    window.addEventListener("feature_flag_changed", handleCustomEvent);

    return () => {
      window.removeEventListener("storage", handleStorageEvent);
      window.removeEventListener("feature_flag_changed", handleCustomEvent);
    };
  }, [syncFromStorage]);

  const isFeatureEnabled = useCallback(
    (flagId: string) => flagMap[flagId] ?? readFlag(flagId),
    [flagMap]
  );

  const toggleFeatureFlag = useCallback((flagId: string) => {
    toggleFlagInStorage(flagId);
    // syncFromStorage will be triggered by the feature_flag_changed event
  }, []);

  const resetToDefaults = useCallback(() => {
    resetFeatureFlagsToDefault();
  }, []);

  return (
    <FeatureFlagsContext.Provider
      value={{
        flagMap,
        systemFlags: SYSTEM_FEATURE_FLAGS,
        isFeatureEnabled,
        toggleFeatureFlag,
        resetToDefaults,
        isLoaded,
      }}
    >
      {children}
    </FeatureFlagsContext.Provider>
  );
}

/**
 * Hook to check if a specific feature flag is enabled.
 */
export function useFeatureFlag(flagId: string): boolean {
  const { isFeatureEnabled } = useContext(FeatureFlagsContext);
  return isFeatureEnabled(flagId);
}

/**
 * Hook to access full feature flags management state.
 */
export function useFeatureFlags() {
  return useContext(FeatureFlagsContext);
}

/**
 * Component wrapper: renders children only when the named flag is enabled.
 */
export function FeatureFlagGuard({
  name,
  fallback = null,
  children,
}: {
  name: string;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}) {
  const enabled = useFeatureFlag(name);
  if (!enabled) return <>{fallback}</>;
  return <>{children}</>;
}
