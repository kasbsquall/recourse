"use client";

import { useEffect, useRef } from "react";

import { getAgent } from "@/lib/agents";
import type { ClaimStatus, Message, SupportingDoc } from "@/lib/types";
import AgentAvatar from "./AgentAvatar";
import AgentMessage from "./AgentMessage";

function TypingBubble({ slug, verb }: { slug: string; verb: string }) {
  const a = getAgent(slug);
  return (
    <div className="flex items-center gap-3">
      <div className="hidden sm:block">
        <AgentAvatar slug={slug} size={44} active />
      </div>
      <div className="brut-flat uppercase-mono flex items-center gap-2 px-3 py-2.5 text-[11px] font-bold">
        <span>
          {a.name} is {verb}
        </span>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="typing-dot h-1.5 w-1.5"
            style={{ background: a.hex, animationDelay: `${i * 0.18}s` }}
          />
        ))}
      </div>
    </div>
  );
}

/** Who are we waiting on next, following the real turn order (Coordinator opens → Blake →
 *  Morgan → Alex → Coordinator compiles → Sam). Returns null once the panel is done. */
function nextThinking(messages: Message[]): { slug: string; verb: string } | null {
  const has = (slug: string) => messages.some((m) => m.agent_slug === slug);
  const coordCount = messages.filter((m) => m.agent_slug === "coordinator").length;

  if (!has("coordinator")) return { slug: "coordinator", verb: "opening the case" };
  if (!has("blake")) return { slug: "blake", verb: "reviewing coverage" };
  if (!has("morgan")) return { slug: "morgan", verb: "checking the policy" };
  if (!has("alex")) return { slug: "alex", verb: "challenging the denial" };
  if (coordCount < 2) return { slug: "coordinator", verb: "compiling the record" };
  if (!has("sam")) return { slug: "sam", verb: "ruling" };
  return null;
}

export default function DebateRoom({
  messages,
  status,
  docs = [],
  onOpenDoc,
}: {
  messages: Message[];
  status: ClaimStatus;
  docs?: SupportingDoc[];
  onOpenDoc?: (doc: SupportingDoc) => void;
}) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, status]);

  const thinking = status === "in_review" ? nextThinking(messages) : null;

  // First message of each agent gets a `seek-<slug>` anchor so the timeline can jump to it.
  const anchored = new Set<string>();

  return (
    <div className="flex flex-col gap-5">
      {messages.map((m) => {
        let anchorId: string | undefined;
        if (!anchored.has(m.agent_slug)) {
          anchored.add(m.agent_slug);
          anchorId = `seek-${m.agent_slug}`;
        }
        return (
          <AgentMessage
            key={m.id}
            message={m}
            docs={docs}
            onOpenDoc={onOpenDoc}
            anchorId={anchorId}
          />
        );
      })}
      {thinking && <TypingBubble slug={thinking.slug} verb={thinking.verb} />}
      <div ref={endRef} />
    </div>
  );
}
