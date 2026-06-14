"use client";

import { Fragment } from "react";

import { getAgent, textOn } from "@/lib/agents";
import type { ClaimStatus, Message } from "@/lib/types";

type Stage = { slug: string; label: string; node: string };

const STAGES: Stage[] = [
  { slug: "coordinator", label: "Intake", node: "C" },
  { slug: "blake", label: "Evaluate", node: "B" },
  { slug: "morgan", label: "Policy", node: "M" },
  { slug: "alex", label: "Challenge", node: "A" },
  { slug: "sam", label: "Rule", node: "S" },
  { slug: "verdict", label: "Verdict", node: "⚖" },
];

const TERMINAL = ["approved", "denied", "partial"];

function stageColor(slug: string, status: ClaimStatus): string {
  if (slug !== "verdict") return getAgent(slug).hex;
  if (status === "approved") return "#15803d";
  if (status === "denied") return "#dc2626";
  if (status === "partial") return "#f5d90a";
  return "#0e0e0e";
}

/** Live progress stepper for the adjudication. Marks each stage done as its agent posts, pulses
 *  the one in progress, and (with onSeek) lets you click a stage to jump to that agent's message. */
export default function DebateTimeline({
  messages,
  status,
  onSeek,
}: {
  messages: Message[];
  status: ClaimStatus;
  onSeek?: (slug: string) => void;
}) {
  const has = (slug: string) => messages.some((m) => m.agent_slug === slug);
  const terminal = TERMINAL.includes(status);
  const done: Record<string, boolean> = {
    coordinator: has("coordinator"),
    blake: has("blake"),
    morgan: has("morgan"),
    alex: has("alex"),
    sam: has("sam"),
    verdict: terminal,
  };
  const activeIdx = status === "in_review" ? STAGES.findIndex((s) => !done[s.slug]) : -1;

  return (
    <div className="flex items-center gap-1 sm:gap-1.5" aria-label="Adjudication progress">
      {STAGES.map((s, i) => {
        const isDone = done[s.slug];
        const isActive = i === activeIdx;
        const lit = isDone || isActive;
        const color = stageColor(s.slug, status);
        const seekable = !!onSeek && lit;
        return (
          <Fragment key={s.slug}>
            {i > 0 && (
              <div
                className="h-[3px] flex-1"
                style={{
                  background: done[STAGES[i - 1].slug] ? "var(--ink)" : "var(--muted)",
                  opacity: done[STAGES[i - 1].slug] ? 1 : 0.3,
                }}
              />
            )}
            <button
              type="button"
              data-stage={s.slug}
              aria-label={seekable ? `Jump to ${s.label}` : s.label}
              onClick={() => seekable && onSeek?.(s.slug)}
              disabled={!seekable}
              title={seekable ? `Jump to ${s.label}` : s.label}
              className={`group flex flex-col items-center gap-1 ${
                seekable ? "cursor-pointer" : "cursor-default"
              }`}
            >
              <div
                className={`flex h-8 w-8 items-center justify-center text-[13px] font-bold leading-none transition-transform ${
                  isActive ? "flash" : ""
                } ${seekable ? "group-hover:-translate-y-0.5" : ""}`}
                style={{
                  border: "2.5px solid var(--ink)",
                  background: lit ? color : "var(--paper-2)",
                  color: lit ? textOn(color) : "var(--muted)",
                  boxShadow: isActive ? "var(--shadow-sm)" : "none",
                }}
              >
                {isDone ? "✓" : s.node}
              </div>
              <span
                className="uppercase-mono text-[8px] font-bold sm:text-[9px]"
                style={{ color: isActive ? "var(--ink)" : "var(--muted)" }}
              >
                {s.label}
              </span>
            </button>
          </Fragment>
        );
      })}
    </div>
  );
}
