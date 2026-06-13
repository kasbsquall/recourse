"use client";

import { useState } from "react";

import { approveClaim, auditUrl } from "@/lib/api";
import type { Resolution } from "@/lib/types";

const DECISION: Record<string, { bg: string; fg: string; label: string }> = {
  APPROVED: { bg: "#16a34a", fg: "#ffffff", label: "Approved" },
  DENIED: { bg: "#ff3b30", fg: "#ffffff", label: "Denied" },
  PARTIAL: { bg: "#f5d90a", fg: "#0e0e0e", label: "Partial" },
  UNCLEAR: { bg: "#e9e6dd", fg: "#0e0e0e", label: "Unclear" },
};

const money = (v: string | null) =>
  v == null ? null : `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

export default function ResolutionPanel({
  claimId,
  resolution,
  onApproved,
}: {
  claimId: string;
  resolution: Resolution;
  onApproved: (r: Resolution) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [showReasoning, setShowReasoning] = useState(true);
  const d = DECISION[resolution.decision] ?? DECISION.UNCLEAR;
  const amt = money(resolution.approved_amount);

  const hash = (resolution.audit_trail?.transcript_sha256 as string) ?? null;
  const [err, setErr] = useState<string | null>(null);

  async function approve() {
    setBusy(true);
    setErr(null);
    try {
      const updated = await approveClaim(claimId, "Kevin Soto (Claims Officer)");
      if (updated.resolution) onApproved(updated.resolution);
    } catch {
      setErr("Couldn't record the approval — check the backend and retry.");
    } finally {
      setBusy(false);
    }
  }

  async function printRecord() {
    try {
      const a = await (await fetch(auditUrl(claimId))).json();
      const rows = (a.transcript ?? [])
        .map(
          (m: { agent: string; content: string }) =>
            `<div class="turn"><div class="who">${m.agent}</div><div class="body">${(m.content || "")
              .replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/\n/g, "<br>")}</div></div>`,
        )
        .join("");
      const r = a.resolution ?? {};
      const w = window.open("", "_blank");
      if (!w) return;
      w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Adjudication Record — ${a.claim_number}</title>
<style>
  body{font-family:Georgia,serif;color:#0e0e0e;max-width:760px;margin:40px auto;padding:0 24px;line-height:1.5}
  h1{font-size:30px;margin:0;letter-spacing:-.02em}.sub{font-family:monospace;font-size:12px;color:#555;margin:4px 0 20px}
  .verdict{border:3px solid #0e0e0e;padding:14px 18px;margin:18px 0;font-size:22px;font-weight:bold}
  .turn{border-left:3px solid #0e0e0e;padding:4px 0 10px 12px;margin:10px 0}
  .who{font-family:monospace;text-transform:uppercase;font-size:11px;font-weight:bold;letter-spacing:.06em}
  .body{font-size:14px;white-space:normal}
  .meta{font-family:monospace;font-size:11px;color:#555;border-top:1px solid #ccc;margin-top:24px;padding-top:12px;word-break:break-all}
  h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;font-family:monospace;margin-top:26px}
</style></head><body>
  <h1>Adjudication Record</h1>
  <div class="sub">RECOURSE · Crestview Mutual · Claim ${a.claim_number} · status: ${a.status}</div>
  <div class="verdict">${r.decision ?? "—"}${r.approved_amount != null ? " · $" + Number(r.approved_amount).toLocaleString("en-US", { minimumFractionDigits: 2 }) : ""}</div>
  <p>${(r.legal_reasoning || "").replace(/</g, "&lt;").replace(/\n/g, "<br>")}</p>
  <h2>Cited clauses</h2><p>${(r.cited_clauses ?? []).join(" · ") || "—"}</p>
  <h2>Adjudication transcript (Band room)</h2>${rows}
  <h2>Signature</h2><p>${r.approved_by ? "Approved by " + r.approved_by + (r.approved_at ? " · " + r.approved_at : "") : "Pending human approval"}</p>
  <div class="meta">Band room: ${a.band_room_id ?? "—"}<br>Tamper-evident hash (sha256): ${(r.audit_trail && r.audit_trail.transcript_sha256) || "—"}</div>
</body></html>`);
      w.document.close();
      w.focus();
      setTimeout(() => w.print(), 400);
    } catch {
      setErr("Couldn't build the record — check the backend.");
    }
  }

  return (
    <div className="brut animate-msg-in" style={{ boxShadow: "var(--shadow-lg)" }}>
      <div className="uppercase-mono border-b-[2.5px] border-[var(--ink)] bg-[var(--ink)] px-3 py-1.5 text-[11px] font-bold text-[var(--bg)]">
        ▣ Resolution · Legal Record
      </div>

      <div
        className="flex flex-wrap items-center gap-4 border-b-[2.5px] border-[var(--ink)] px-5 py-5"
        style={{ background: d.bg, color: d.fg }}
      >
        <span className="font-display text-3xl uppercase tracking-tight">{d.label}</span>
        {amt && <span className="font-mono text-3xl font-bold">{amt}</span>}
      </div>

      <div className="space-y-4 p-5">
        {resolution.cited_clauses.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {resolution.cited_clauses.map((c) => (
              <span
                key={c}
                className="font-mono px-2 py-1 text-[12px] font-bold"
                style={{ border: "2px solid var(--ink)", background: "var(--paper-2)" }}
              >
                {c}
              </span>
            ))}
          </div>
        )}

        <div>
          <button
            onClick={() => setShowReasoning((s) => !s)}
            className="uppercase-mono mb-2 text-[11px] font-bold text-[var(--muted)] hover:text-[var(--ink)]"
          >
            Legal Reasoning [{showReasoning ? "−" : "+"}]
          </button>
          {showReasoning && (
            <div
              className="whitespace-pre-wrap p-3 text-[13px] leading-relaxed"
              style={{ background: "var(--paper-2)", border: "2px solid var(--ink)" }}
            >
              {resolution.legal_reasoning}
            </div>
          )}
        </div>

        {hash && (
          <div className="font-mono break-all text-[10px] text-[var(--muted)]">
            ⛓ tamper-evident sha256 · {hash.slice(0, 32)}…
          </div>
        )}

        {err && (
          <div
            className="uppercase-mono px-3 py-2 text-[11px] font-bold"
            style={{ background: "#ff3b30", color: "#fff", border: "2px solid var(--ink)" }}
          >
            {err}
          </div>
        )}

        {resolution.approved_by ? (
          <div
            className="uppercase-mono px-4 py-3 text-[12px] font-bold"
            style={{ background: "#16a34a", color: "#fff", border: "2.5px solid var(--ink)" }}
          >
            ✓ Approved by {resolution.approved_by}
            {resolution.approved_at &&
              ` · ${new Date(resolution.approved_at).toLocaleString()}`}
          </div>
        ) : (
          <button
            onClick={approve}
            disabled={busy}
            className="brut-hover uppercase-mono w-full px-5 py-3 text-sm font-bold disabled:opacity-60"
            style={{ background: "#16a34a", color: "#fff", border: "2.5px solid var(--ink)", boxShadow: "var(--shadow)" }}
          >
            {busy ? "Approving…" : "✓ Approve Resolution"}
          </button>
        )}

        <div className="flex flex-wrap gap-3">
          <button
            onClick={printRecord}
            className="brut-hover uppercase-mono px-5 py-3 text-sm font-bold"
            style={{ background: "var(--signal)", border: "2.5px solid var(--ink)", boxShadow: "var(--shadow)" }}
          >
            📄 Print Record
          </button>
          <a
            href={auditUrl(claimId)}
            target="_blank"
            rel="noreferrer"
            className="brut-hover uppercase-mono px-5 py-3 text-sm font-bold"
            style={{ background: "var(--paper)", border: "2.5px solid var(--ink)", boxShadow: "var(--shadow)" }}
          >
            ⤓ Export JSON
          </a>
        </div>
      </div>
    </div>
  );
}
