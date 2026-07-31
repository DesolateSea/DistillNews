"use client";

import { useFeatureFlags } from "@/lib/feature-flags-context";

/**
 * ChatFab — Floating Action Button for the AI chat.
 *
 * Two feature flags control this component:
 *  - "ai_chat"           → feature flag: is chat enabled at all?
 *                          (checked by FeatureFlagGuard in the parent page)
 *  - "ai_chat_robot_design" → design flag: animated robot (true) vs plain icon (false)
 */
interface ChatFabProps {
  onClick: () => void;
}

export function ChatFab({ onClick }: ChatFabProps) {
  const { isFeatureEnabled } = useFeatureFlags();

  // Design flag: which button style to render
  const useRobotDesign = isFeatureEnabled("ai_chat_robot_design");

  if (!useRobotDesign) {
    return <PlainChatButton onClick={onClick} />;
  }

  return <AnimatedRobotButton onClick={onClick} />;
}

/* ─── Plain design (ai_chat_robot_design = false) ─────────────────────────── */
function PlainChatButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="h-14 w-14 rounded-full bg-primary text-primary-foreground shadow-lg flex items-center justify-center hover:scale-105 transition-transform"
      aria-label="Open AI chat"
    >
      <MessageIcon />
    </button>
  );
}

/* ─── Robot design (ai_chat_robot_design = true) ──────────────────────────── */
function AnimatedRobotButton({ onClick }: { onClick: () => void }) {
  return (
    <div className="relative flex items-center justify-center" style={{ width: 72, height: 72 }}>
      {/* Outer pulse ring */}
      <span className="absolute inset-0 rounded-full bg-primary/30 animate-ping" />
      {/* Mid glow ring */}
      <span className="absolute inset-1 rounded-full bg-primary/20 animate-pulse" />

      {/* Main button */}
      <button
        onClick={onClick}
        className="relative z-10 h-16 w-16 rounded-full bg-primary text-primary-foreground shadow-2xl flex flex-col items-center justify-center gap-0.5 hover:scale-110 active:scale-95 transition-all duration-200 group"
        aria-label="Open AI chat"
      >
        <RobotSVG />
        <span className="text-[9px] font-bold tracking-wide opacity-90 leading-none">ASK AI</span>
      </button>
    </div>
  );
}

/* ─── SVG helpers ──────────────────────────────────────────────────────────── */
function RobotSVG() {
  return (
    <svg
      viewBox="0 0 32 32"
      className="w-7 h-7 group-hover:animate-bounce"
      fill="currentColor"
      aria-hidden
    >
      {/* Antenna */}
      <rect x="15" y="1" width="2" height="4" rx="1" opacity="0.9" />
      <circle cx="16" cy="1.5" r="1.5" opacity="0.9" />
      {/* Head */}
      <rect x="6" y="5" width="20" height="14" rx="4" opacity="0.95" />
      {/* Eye sockets */}
      <circle cx="11.5" cy="11" r="2.5" opacity="0.3" />
      <circle cx="20.5" cy="11" r="2.5" opacity="0.3" />
      {/* Pupils */}
      <circle cx="11.5" cy="11" r="1.2" className="fill-primary-foreground opacity-90" />
      <circle cx="20.5" cy="11" r="1.2" className="fill-primary-foreground opacity-90" />
      {/* Eye shine */}
      <circle cx="12.2" cy="10.3" r="0.4" className="fill-primary-foreground" />
      <circle cx="21.2" cy="10.3" r="0.4" className="fill-primary-foreground" />
      {/* Mouth */}
      <rect x="10" y="15" width="12" height="2" rx="1" className="fill-primary-foreground opacity-60" />
      {/* Body */}
      <rect x="9" y="20" width="14" height="9" rx="3" opacity="0.8" />
      {/* Arms */}
      <rect x="3" y="21" width="5" height="3" rx="1.5" opacity="0.7" />
      <rect x="24" y="21" width="5" height="3" rx="1.5" opacity="0.7" />
    </svg>
  );
}

function MessageIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
