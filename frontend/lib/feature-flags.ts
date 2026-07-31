/**
 * LocalStorage-based Feature Flag System for DistillNews Frontend.
 *
 * Each flag is stored as its own individual key in localStorage:
 *   ff_ai_chat           = "true" | "false"
 *   ff_semantic_search   = "true" | "false"
 *   ff_ai_chat_robot_design = "true" | "false"
 *   ... etc.
 */

export interface FeatureFlag {
  id: string;
  name: string;
  description: string;
  defaultEnabled: boolean;
}

// Master list of all system feature flags
export const SYSTEM_FEATURE_FLAGS: FeatureFlag[] = [
  {
    id: "ai_chat",
    name: "AI Chat Assistant",
    description: "RAG AI news assistant drawer in the dashboard",
    defaultEnabled: true,
  },
  {
    id: "ai_chat_robot_design",
    name: "AI Chat: Robot Button Design",
    description: "Show animated robot avatar button for chat. When off, shows a plain icon button instead.",
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
  {
    id: "landing_hero_badge",
    name: "Landing: Hero Badge",
    description: "Shows the 'AI-summarised news, updated daily' pill above the hero headline",
    defaultEnabled: true,
  },
  {
    id: "landing_sample_articles",
    name: "Landing: Sample Articles",
    description: "Shows example news cards on the landing page so users preview the feed",
    defaultEnabled: true,
  },
  {
    id: "landing_how_it_works",
    name: "Landing: How It Works",
    description: "Shows the 3-step explanation section on the landing page",
    defaultEnabled: true,
  },
  {
    id: "landing_auto_vanish_info",
    name: "Landing: Auto-Vanishing Info Banner",
    description: "Auto-fades out the DistillNews description text after a few seconds",
    defaultEnabled: true,
  },
  {
    id: "ai_chat_robot_design",
    name: "AI Chat: Robot Button Design",
    description: "Show animated robot avatar button for chat. When off, shows a plain icon button instead.",
    defaultEnabled: true,
  },
];

/** localStorage key prefix for individual flag entries */
const FLAG_KEY_PREFIX = "ff_";

function storageKey(flagId: string): string {
  return `${FLAG_KEY_PREFIX}${flagId}`;
}

/**
 * Read a single flag from localStorage.
 * Falls back to the flag's defaultEnabled if the key doesn't exist yet.
 */
export function isFeatureEnabled(flagId: string): boolean {
  if (typeof window === "undefined") {
    const flag = SYSTEM_FEATURE_FLAGS.find((f) => f.id === flagId);
    return flag?.defaultEnabled ?? false;
  }
  const raw = localStorage.getItem(storageKey(flagId));
  if (raw === null) {
    // First visit — write the default and return it
    const flag = SYSTEM_FEATURE_FLAGS.find((f) => f.id === flagId);
    const defaultVal = flag?.defaultEnabled ?? false;
    localStorage.setItem(storageKey(flagId), String(defaultVal));
    return defaultVal;
  }
  return raw === "true";
}

/**
 * Set a single flag explicitly.
 */
export function setFeatureFlag(flagId: string, enabled: boolean): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(storageKey(flagId), String(enabled));
  window.dispatchEvent(new CustomEvent("feature_flag_changed", { detail: { flagId, enabled } }));
}

/**
 * Toggle a single flag and return its new state.
 */
export function toggleFeatureFlag(flagId: string): boolean {
  const newState = !isFeatureEnabled(flagId);
  setFeatureFlag(flagId, newState);
  return newState;
}

/**
 * Return the enabled state of all known flags as a plain object.
 */
export function getAllFeatureFlags(): Record<string, boolean> {
  return Object.fromEntries(
    SYSTEM_FEATURE_FLAGS.map((f) => [f.id, isFeatureEnabled(f.id)])
  );
}

/**
 * Reset all flags to their system defaults.
 */
export function resetFeatureFlagsToDefault(): void {
  SYSTEM_FEATURE_FLAGS.forEach((f) => {
    setFeatureFlag(f.id, f.defaultEnabled);
  });
}
