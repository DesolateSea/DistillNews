"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
  SYSTEM_FEATURE_FLAGS,
  FeatureFlag,
  getEnabledFeatureFlags,
  saveEnabledFeatureFlags,
  toggleFeatureFlag as toggleFlagInStorage,
  resetFeatureFlagsToDefault,
} from "./feature-flags";

interface FeatureFlagsContextType {
  enabledFlags: string[];
  systemFlags: FeatureFlag[];
  isFeatureEnabled: (flagId: string) => boolean;
  toggleFeatureFlag: (flagId: string) => void;
  setFeatureFlags: (flagIds: string[]) => void;
  resetToDefaults: () => void;
  isLoaded: boolean;
}

const FeatureFlagsContext = createContext<FeatureFlagsContextType>({
  enabledFlags: [],
  systemFlags: SYSTEM_FEATURE_FLAGS,
  isFeatureEnabled: () => false,
  toggleFeatureFlag: () => {},
  setFeatureFlags: () => {},
  resetToDefaults: () => {},
  isLoaded: false,
});

export function FeatureFlagsProvider({ children }: { children: React.ReactNode }) {
  const [enabledFlags, setEnabledFlags] = useState<string[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  const loadFlagsFromStorage = useCallback(() => {
    const flags = getEnabledFeatureFlags();
    setEnabledFlags(flags);
    setIsLoaded(true);
  }, []);

  useEffect(() => {
    loadFlagsFromStorage();

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === "distill_news_enabled_feature_flags" || !e.key) {
        loadFlagsFromStorage();
      }
    };

    const handleCustomUpdate = () => {
      loadFlagsFromStorage();
    };

    window.addEventListener("storage", handleStorageChange);
    window.addEventListener("feature_flags_updated", handleCustomUpdate);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
      window.removeEventListener("feature_flags_updated", handleCustomUpdate);
    };
  }, [loadFlagsFromStorage]);

  const isFeatureEnabled = useCallback(
    (flagId: string) => {
      return enabledFlags.includes(flagId);
    },
    [enabledFlags]
  );

  const toggleFeatureFlag = useCallback((flagId: string) => {
    toggleFlagInStorage(flagId);
  }, []);

  const setFeatureFlags = useCallback((flagIds: string[]) => {
    saveEnabledFeatureFlags(flagIds);
  }, []);

  const resetToDefaults = useCallback(() => {
    resetFeatureFlagsToDefault();
  }, []);

  return (
    <FeatureFlagsContext.Provider
      value={{
        enabledFlags,
        systemFlags: SYSTEM_FEATURE_FLAGS,
        isFeatureEnabled,
        toggleFeatureFlag,
        setFeatureFlags,
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
 * Component wrapper to render children only if specified feature flag is enabled.
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
