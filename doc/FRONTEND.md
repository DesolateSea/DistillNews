# Frontend Architecture & Documentation

The Next.js 14 web application in `frontend/` provides the modern web user interface for DistillNews.

---

## Technical Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript / React 18
- **Styling**: Tailwind CSS, Lucide Icons, Custom CSS Dark Theme Tokens (`globals.css`)
- **Theme Management**: `next-themes` (Class-based dark/light mode with SSR hydration-safety)
- **Feature Flags**: LocalStorage-based per-flag architecture (`lib/feature-flags.ts` & `lib/feature-flags-context.tsx`)

---

## App Router Structure (`frontend/app/`)

| Path | Description |
|:---|:---|
| `app/page.tsx` | Landing page featuring hero banner, `HeadlinesBanner` ticker & hero card, "What makes DistillNews different" grid, and CTA buttons. |
| `app/dashboard/page.tsx` | Main article news feed with semantic vector search, category filter pills, `HeadlinesBanner` full variant, infinite scroll, and floating `ChatFab`. |
| `app/[newsId]/page.tsx` | Article reader page with full markdown content, map location view, `HeadlinesBanner` ticker, and AI chat assistant. |
| `app/preferences/page.tsx` | User topic preferences configuration page. Implements direct redirect to `/register` for guest users. |
| `app/register/page.tsx` | Authentication page supporting Email/Password, Email OTP verification, and Google Sign-In. |
| `app/layout.tsx` | Root layout configuring `ThemeProvider` and `FeatureFlagsProvider`. |

---

## Core Components (`frontend/components/`)

### 1. `HeadlinesBanner.tsx`
- **Variants**: `ticker` (compact animated headline bar), `hero` (featured article card with image), `full` (both ticker + hero card).
- **Behavior**: Auto-fetches top 30 articles, filters for articles possessing valid image URLs, and auto-rotates featured stories every 5 seconds.
- **Feature Flag**: Self-guarded via `top_headlines` (`ff_top_headlines`).

### 2. `ChatFab.tsx`
- Floating AI chat action button.
- **Design Flag**: `ai_chat_robot_design` (`ff_ai_chat_robot_design`). When enabled, renders an animated robot avatar with `animate-ping` and `animate-pulse` glow rings. When disabled, falls back to a minimal icon button.
- **Feature Flag**: `ai_chat` (`ff_ai_chat`). Controls chat availability.

### 3. `ThemeToggle.tsx`
- Hydration-safe light/dark mode switcher icon button using `next-themes`.
- **Feature Flag**: `dark_mode_toggle` (`ff_dark_mode_toggle`).

---

## Feature Flag Architecture (`lib/feature-flags.ts`)

Feature flags use a **per-flag key design in LocalStorage** (`ff_<id> = "true" | "false"`).

### Active System Flags

| Flag ID | Name | Default | Description |
|:---|:---|:---|:---|
| `ai_chat` | AI Chat Assistant | `true` | Enables AI news assistant drawer |
| `ai_chat_robot_design` | AI Chat Robot Button | `true` | Toggles animated robot button vs plain icon |
| `top_headlines` | Top Headlines Banner | `true` | Toggles breaking news ticker and hero banner |
| `semantic_search` | Semantic Search | `true` | AI-driven vector search bar |
| `category_filters` | Category Filters | `true` | Topic pills bar for filtering feeds |
| `guest_banner` | Guest Notice Banner | `true` | Guest user notification banner |
| `weather_widget` | Weather Forecast | `true` | Location-based weather widget |
| `infinite_scroll` | Infinite Scroll | `true` | Auto-load articles on scroll |
| `dark_mode_toggle` | Dark Mode Switcher | `true` | Header theme toggle button |
| `landing_hero_badge` | Landing Hero Badge | `true` | Hero section badge |
| `landing_sample_articles`| Landing Sample Cards | `true` | Sample article cards preview |
| `landing_how_it_works` | Landing Feature Grid | `true` | "What makes DistillNews different" grid |

### Programmatic API & Storage Inspection

```typescript
import { isFeatureEnabled, setFeatureFlag } from "@/lib/feature-flags";

// Check flag in code
const isChatEnabled = isFeatureEnabled("ai_chat");

// Set flag in browser console or devtools
localStorage.setItem("ff_ai_chat", "false");
```

---

## Local Development Setup

```bash
cd frontend
npm ci
printf 'NEXT_PUBLIC_API_URL=http://localhost:8000\n' > .env.local
npm run dev
```

App starts on `http://localhost:3000`.
