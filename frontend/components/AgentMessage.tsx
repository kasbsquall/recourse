"use client";

import { AGENTS, getAgent, textOn } from "@/lib/agents";
import type { Message, SupportingDoc } from "@/lib/types";
import AgentAvatar from "./AgentAvatar";

const NAME_HEX: Record<string, string> = Object.fromEntries(
  Object.values(AGENTS).map((a) => [a.name.toLowerCase(), a.hex]),
);

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Phrase aliases per supporting-doc type, so prose like "the police report" is clickable too. */
const ALIAS_SRC: Record<string, string[]> = {
  police_report: ["police report", "FHP-\\d{4}-\\d+"],
  mechanic_report: ["mechanic'?s? report", "BM-AUTO-[\\w-]+"],
  photos: ["\\d+ photos?", "crash photos?", "the photos?", "photographs?"],
};

function fmtTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

/** Build a tokenizer that captures bold, italic, clause refs, @mentions, and any reference to a
 *  supporting document (by id or by phrase). Order matters: bold before italic. */
function buildTokenRegex(docs: SupportingDoc[]): RegExp {
  const fixed = ["\\*\\*[^*]+\\*\\*", "\\*[^*\\n]+\\*", "§\\s?\\d+\\.\\d+", "@[A-Za-z]+"];
  const docParts: string[] = [];
  for (const d of docs) {
    docParts.push(escapeRe(d.ref));
    for (const p of ALIAS_SRC[d.type] ?? []) docParts.push(p);
  }
  docParts.sort((a, b) => b.length - a.length); // longest alternative first
  return new RegExp([...fixed, ...docParts].join("|"), "gi");
}

function resolveDoc(tok: string, docs: SupportingDoc[]): SupportingDoc | null {
  const t = tok.toLowerCase().trim();
  for (const d of docs) if (d.ref.toLowerCase() === t) return d;
  for (const d of docs) {
    if (d.type === "police_report" && (/^police report$/i.test(tok) || /^fhp-/i.test(tok))) return d;
    if (d.type === "mechanic_report" && (/^mechanic'?s? report$/i.test(tok) || /^bm-auto-/i.test(tok)))
      return d;
    if (d.type === "photos" && (/photos?$/i.test(t) || /photographs?$/i.test(t))) return d;
  }
  return null;
}

function ClausePill({ label, hex }: { label: string; hex: string }) {
  return (
    <span
      className="font-mono mx-0.5 px-1.5 text-[12px] font-bold"
      style={{ background: hex, color: textOn(hex), border: "1.5px solid var(--ink)" }}
    >
      {label}
    </span>
  );
}

function renderInline(
  text: string,
  hex: string,
  docs: SupportingDoc[],
  onOpenDoc?: (doc: SupportingDoc) => void,
): React.ReactNode[] {
  const re = buildTokenRegex(docs);
  const out: React.ReactNode[] = [];
  let last = 0;
  let key = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(<span key={key++}>{text.slice(last, m.index)}</span>);
    const tok = m[0];
    last = m.index + tok.length;
    if (re.lastIndex === m.index) re.lastIndex++;

    if (/^\*\*[\s\S]+\*\*$/.test(tok)) {
      out.push(
        <strong key={key++} className="font-extrabold">
          {tok.slice(2, -2)}
        </strong>,
      );
    } else if (/^\*[\s\S]+\*$/.test(tok)) {
      out.push(<em key={key++}>{tok.slice(1, -1)}</em>);
    } else if (/^§/.test(tok)) {
      out.push(<ClausePill key={key++} label={tok} hex={hex} />);
    } else if (tok.startsWith("@")) {
      const mh = NAME_HEX[tok.slice(1).toLowerCase()];
      if (mh) {
        out.push(
          <span
            key={key++}
            className="mx-0.5 px-1.5 text-[13px] font-bold"
            style={{ background: mh, color: textOn(mh), border: "1.5px solid var(--ink)" }}
          >
            {tok}
          </span>,
        );
      } else {
        out.push(<span key={key++}>{tok}</span>);
      }
    } else {
      const doc = resolveDoc(tok, docs);
      if (doc?.url && onOpenDoc) {
        out.push(
          <button
            key={key++}
            type="button"
            onClick={() => onOpenDoc(doc)}
            className="brut-hover mx-0.5 inline px-1 text-[14px] font-bold underline decoration-dotted underline-offset-2"
            style={{ background: "var(--paper-2)", border: "1.5px solid var(--ink)" }}
            title={`Open ${doc.type} · ${doc.ref}`}
          >
            📎 {tok}
          </button>,
        );
      } else {
        out.push(<span key={key++}>{tok}</span>);
      }
    }
  }
  if (last < text.length) out.push(<span key={key++}>{text.slice(last)}</span>);
  return out;
}

/** Detect a leading label — an ALL-CAPS heading ("DECISION:", "LEGAL REASONING:") or a single
 *  capitalised word ("Blake:") followed by a colon — so it can render bold like a real heading. */
function splitLabel(text: string): { label: string; rest: string } | null {
  const m = text.match(/^([A-Za-z][A-Za-z0-9 ./'’&()—-]{0,38}?:)(.*)$/);
  if (!m) return null;
  const core = m[1].slice(0, -1);
  const allCaps = /^[A-Z0-9 ./'’&()—-]+$/.test(core) && /[A-Z]{2,}/.test(core);
  const singleWord = /^[A-Z][A-Za-z]+$/.test(core);
  return allCaps || singleWord ? { label: m[1], rest: m[2] } : null;
}

function renderRich(
  text: string,
  hex: string,
  docs: SupportingDoc[],
  onOpenDoc?: (doc: SupportingDoc) => void,
): React.ReactNode {
  const lab = splitLabel(text);
  if (lab) {
    return (
      <>
        <strong className="font-extrabold">{lab.label}</strong>
        {renderInline(lab.rest, hex, docs, onOpenDoc)}
      </>
    );
  }
  return renderInline(text, hex, docs, onOpenDoc);
}

function FormattedContent({
  text,
  hex,
  docs,
  onOpenDoc,
}: {
  text: string;
  hex: string;
  docs: SupportingDoc[];
  onOpenDoc?: (doc: SupportingDoc) => void;
}) {
  const lines = text.split("\n");
  return (
    <div className="space-y-1.5 text-[15px] leading-relaxed">
      {lines.map((raw, i) => {
        const line = raw.replace(/\s+$/, "");
        if (!line.trim()) return <div key={i} className="h-1" />;

        const bullet = line.match(/^\s*[-•*]\s+(.*)$/);
        if (bullet) {
          return (
            <div key={i} className="flex gap-2">
              <span className="select-none pt-0.5" style={{ color: hex }}>
                ▸
              </span>
              <p className="flex-1">{renderRich(bullet[1], hex, docs, onOpenDoc)}</p>
            </div>
          );
        }
        const num = line.match(/^\s*(\d+)[.)]\s+(.*)$/);
        if (num) {
          return (
            <div key={i} className="flex gap-2">
              <span className="font-mono select-none font-bold" style={{ color: hex }}>
                {num[1]}.
              </span>
              <p className="flex-1">{renderRich(num[2], hex, docs, onOpenDoc)}</p>
            </div>
          );
        }
        return <p key={i}>{renderRich(line, hex, docs, onOpenDoc)}</p>;
      })}
    </div>
  );
}

export default function AgentMessage({
  message,
  docs = [],
  onOpenDoc,
  anchorId,
}: {
  message: Message;
  docs?: SupportingDoc[];
  onOpenDoc?: (doc: SupportingDoc) => void;
  anchorId?: string;
}) {
  const agent = getAgent(message.agent_slug);

  if (message.message_type === "case_file") {
    const coord = getAgent("coordinator");
    return (
      <div id={anchorId} className="animate-msg-in flex scroll-mt-[72px] gap-3">
        <div className="hidden sm:block">
          <AgentAvatar slug="coordinator" size={44} />
        </div>
        <div className="brut min-w-0 flex-1" style={{ background: "var(--paper-2)" }}>
          <div
            className="uppercase-mono flex items-center justify-between border-b-[2.5px] border-[var(--ink)] px-3 py-1.5 text-[11px] font-bold"
            style={{ background: coord.hex, color: textOn(coord.hex) }}
          >
            <span>{coord.name} · opened the case</span>
            <span className="opacity-80">▸ Case File · Intake</span>
          </div>
          <div className="p-4">
            <FormattedContent text={message.content} hex={coord.hex} docs={docs} onOpenDoc={onOpenDoc} />
          </div>
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
    <div id={anchorId} className="animate-msg-in flex scroll-mt-[72px] gap-3">
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
          <span className="flex items-center gap-2">
            <span className="opacity-80">{agent.role}</span>
            {message.sent_at && (
              <span className="font-mono text-[10px] opacity-70">{fmtTime(message.sent_at)}</span>
            )}
          </span>
        </div>
        <div className="p-4">
          <FormattedContent text={message.content} hex={agent.hex} docs={docs} onOpenDoc={onOpenDoc} />
        </div>
      </div>
    </div>
  );
}
