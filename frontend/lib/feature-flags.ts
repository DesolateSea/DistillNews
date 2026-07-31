/**
 * LocalStorage-based Feature Flag System for DistillNews Frontend.
 *
 * Feature flags are stored and read directly from LocalStorage.
 */

export interface FeatureFlag {
  id: string;
  name: string;
  description: string;
  defaultEnabled: boolean;
}

// Master list of system feature flags
export const SYSTEM_FEATURE_FLAGS: FeatureFlag[] = [
  {
    id: "ai_chat",
    name: "AI Chat Assistant",
    description: "RAG AI news assistant drawer in the dashboard",
    defaultEnabled: true,
  },
  {
    id: "semantic_search",
    name: "Semantic Search",
    description: "AI-driven vector search bar in the news feed",
    defaultEnabled: true,
  },
  {
    id: "category_filters",
    name: "Category Filters",
    description: "Category pills bar for filtering news topics",
    defaultEnabled: true,
  },
  {
    id: "guest_banner",
    name: "Guest Notice Banner",
    description: "Informational banner displayed to unauthenticated guest users",
    defaultEnabled: true,
  },
  {
    id: "weather_widget",
    name: "Weather Forecast",
    description: "Location-based weather information widget",
    defaultEnabled: true,
  },
  {
    id: "infinite_scroll",
    name: "Infinite Scroll",
    description: "Auto-load more news articles on scroll",
    defaultEnabled: true,
  },
  {
    id: "newspaper_view",
    name: "Newspaper View Mode",
    description: "Print-style digital newspaper layout option",
    defaultEnabled: false,
  },
  {
    id: "dark_mode_toggle",
    name: "Dark Mode Theme Toggle",
    description: "Light/Dark theme switcher button in navigation header",
    defaultEnabled: true,
  },
];

const LOCAL_STORAGE_KEY = "distill_news_enabled_feature_flags";

/**
 * Get the list of currently enabled feature flag IDs from LocalStorage.
 * If none exist in LocalStorage, initializes with default enabled flags.
 */
export function getEnabledFeatureFlags(): string[] {
  if (typeof window === "undefined") {
    return SYSTEM_FEATURE_FLAGS.filter((f) => f.defaultEnabled).map((f) => f.id);
  }

  try {
    const item = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!item) {
      const defaultList = SYSTEM_FEATURE_FLAGS.filter((f) => f.defaultEnabled).map((f) => f.id);
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(defaultList));
      return defaultList;
    }
    return JSON.parse(item);
  } catch (err) {
    console.error("Error reading feature flags from localStorage:", err);
    return SYSTEM_FEATURE_FLAGS.filter((f) => f.defaultEnabled).map((f) => f.id);
  }
}

/**
 * Save the list of enabled feature flag IDs to LocalStorage.
 */
export function saveEnabledFeatureFlags(flags: string[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(flags));
    // Dispatch custom event so reactive listeners update immediately
    window.dispatchEvent(new Event("feature_flags_updated"));
  } catch (err) {
    console.error("Error writing feature flags to localStorage:", err);
  }
}

/**
 * Check if a specific feature flag is currently enabled in LocalStorage.
 */
export function isFeatureEnabled(flagId: string): boolean {
  const enabledFlags = getEnabledFeatureFlags();
  return enabledFlags.includes(flagId);
}

/**
 * Toggle a feature flag in LocalStorage and return its new enabled state.
 */
export function toggleFeatureFlag(flagId: string): boolean {
  const enabledFlags = getEnabledFeatureFlags();
  let updatedFlags: string[];
  let newState: boolean;

  if (enabledFlags.includes(flagId)) {
    updatedFlags = enabledFlags.filter((id) => id !== flagId);
    newState = false;
  } else {
    updatedFlags = [...enabledFlags, flagId];
    newState = true;
  }

  saveEnabledFeatureFlags(updatedFlags);
  return newState;
}

/**
 * Reset all feature flags in LocalStorage to system defaults.
 */
export function resetFeatureFlagsToDefault(): string[] {
  const defaultList = SYSTEM_FEATURE_FLAGS.filter((f) => f.defaultEnabled).map((f) => f.id);
  saveEnabledFeatureFlags(defaultList);
  return defaultList;
}
