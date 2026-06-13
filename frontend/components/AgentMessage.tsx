import { AGENTS, getAgent, textOn } from "@/lib/agents";
import type { Message } from "@/lib/types";
import AgentAvatar from "./AgentAvatar";

const NAME_HEX: Record<string, string> = Object.fromEntries(
  Object.values(AGENTS).map((a) => [a.name.toLowerCase(), a.hex]),
);

function FormattedContent({ text, hex }: { text: string; hex: string }) {
  const lines = text.split("\n");
  return (
    <div className="space-y-1.5 text-[15px] leading-relaxed">
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-1" />;
        const parts = line
          .split(/(\*\*[^*]+\*\*|§\s?\d+\.\d+|@[A-Za-z]+)/g)
          .filter(Boolean);
        return (
          <p key={i}>
            {parts.map((p, j) => {
              if (p.startsWith("**") && p.endsWith("**"))
                return (
                  <strong key={j} className="font-extrabold">
                    {p.slice(2, -2)}
                  </strong>
                );
              if (/^§\s?\d+\.\d+$/.test(p))
                return (
                  <span
                    key={j}
                    className="font-mono mx-0.5 px-1.5 text-[12px] font-bold"
                    style={{ background: hex, color: textOn(hex), border: "1.5px solid var(--ink)" }}
                  >
                    {p}
                  </span>
                );
              if (p.startsWith("@") && NAME_HEX[p.slice(1).toLowerCase()]) {
                const mh = NAME_HEX[p.slice(1).toLowerCase()];
                return (
                  <span
                    key={j}
                    className="mx-0.5 px-1.5 text-[13px] font-bold"
                    style={{ background: mh, color: textOn(mh), border: "1.5px solid var(--ink)" }}
                  >
                    {p}
                  </span>
                );
              }
              return <span key={j}>{p}</span>;
            })}
          </p>
        );
      })}
    </div>
  );
}

export default function AgentMessage({ message }: { message: Message }) {
  const agent = getAgent(message.agent_slug);

  if (message.message_type === "case_file") {
    return (
      <div className="brut animate-msg-in" style={{ background: "var(--paper-2)" }}>
        <div className="uppercase-mono border-b-[2.5px] border-[var(--ink)] bg-[var(--ink)] px-3 py-1.5 text-[11px] font-bold text-[var(--bg)]">
          ▸ Case File · Intake
        </div>
        <div className="whitespace-pre-wrap p-4 font-mono text-[12.5px] leading-relaxed text-[var(--ink)]">
          {message.content}
        </div>
      </div>
    );
  }

  if (message.message_type === "error") {
    return (
      <div className="uppercase-mono animate-msg-in border-2 border-dashed border-[var(--muted)] px-3 py-2 text-[11px] text-[var(--muted)]">
        ⚠ {message.content}
      </div>
    );
  }

  const isResolution = message.message_type === "resolution";

  return (
    <div className="animate-msg-in flex gap-3">
      <div className="hidden sm:block">
        <AgentAvatar slug={message.agent_slug} size={44} />
      </div>
      <div
        className="brut min-w-0 flex-1"
        style={isResolution ? { boxShadow: "var(--shadow-lg)" } : undefined}
      >
        <div
          className="uppercase-mono flex items-center justify-between border-b-[2.5px] border-[var(--ink)] px-3 py-1.5 text-[11px] font-bold"
          style={{ background: agent.hex, color: textOn(agent.hex) }}
        >
          <span>{agent.name}</span>
          <span className="opacity-80">{agent.role}</span>
        </div>
        <div className="p-4">
          <FormattedContent text={message.content} hex={agent.hex} />
        </div>
      </div>
    </div>
  );
}
