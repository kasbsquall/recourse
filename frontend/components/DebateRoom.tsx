"use client";

import { useEffect, useRef } from "react";

import { ADJUDICATORS, getAgent } from "@/lib/agents";
import type { ClaimStatus, Message } from "@/lib/types";
import AgentAvatar from "./AgentAvatar";
import AgentMessage from "./AgentMessage";

function TypingBubble({ slug }: { slug: string }) {
  const a = getAgent(slug);
  return (
    <div className="flex items-center gap-3">
      <div className="hidden sm:block">
        <AgentAvatar slug={slug} size={44} active />
      </div>
      <div className="brut-flat uppercase-mono flex items-center gap-2 px-3 py-2.5 text-[11px] font-bold">
        <span>{a.name} is reviewing</span>
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

export default function DebateRoom({
  messages,
  status,
}: {
  messages: Message[];
  status: ClaimStatus;
}) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, status]);

  const posted = new Set(messages.map((m) => m.agent_slug));
  const thinking =
    status === "in_review" ? ADJUDICATORS.find((s) => !posted.has(s)) : undefined;

  return (
    <div className="flex flex-col gap-5">
      {messages.map((m) => (
        <AgentMessage key={m.id} message={m} />
      ))}
      {thinking && <TypingBubble slug={thinking} />}
      <div ref={endRef} />
    </div>
  );
}
