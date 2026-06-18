"use client";

import { useState } from "react";

import { approveClaim, auditUrl, overrideClaim } from "@/lib/api";
import type { ClaimDetail, Resolution } from "@/lib/types";

const OFFICER = "Kevin Soto (Claims Officer)";

/** Escape agent/officer-sourced strings before writing them into the print window's raw HTML. */
const esc = (s: string) =>
  (s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

const DECISION: Record<string, { bg: string; fg: string; label: string }> = {
  APPROVED: { bg: "#15803d", fg: "#ffffff", label: "Approved" },
  DENIED: { bg: "#dc2626", fg: "#ffffff", label: "Denied" },
  PARTIAL: { bg: "#f5d90a", fg: "#0e0e0e", label: "Partial" },
  UNCLEAR: { bg: "#e9e6dd", fg: "#0e0e0e", label: "Unclear" },
};

const money = (v: string | null) =>
  v == null ? null : `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

export default function ResolutionPanel({
  claimId,
  resolution,
  onResolved,
}: {
  claimId: string;
  resolution: Resolution;
  onResolved: (claim: ClaimDetail) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [showReasoning, setShowReasoning] = useState(true);
  const [overriding, setOverriding] = useState(false);
  const [reason, setReason] = useState("");
  const d = DECISION[resolution.decision] ?? DECISION.UNCLEAR;
  const amt = money(resolution.approved_amount);

  const hash = (resolution.audit_trail?.transcript_sha256 as string) ?? null;
  const override = resolution.audit_trail?.officer_override as
    | { by?: string; reason?: string }
    | undefined;
  const [err, setErr] = useState<string | null>(null);

  async function approve() {
    setBusy(true);
    setErr(null);
    try {
      const updated = await approveClaim(claimId, OFFICER);
      onResolved(updated);
    } catch {
      setErr("Couldn't record the approval — check the backend and retry.");
    } finally {
      setBusy(false);
    }
  }

  async function confirmOverride() {
    setBusy(true);
    setErr(null);
    try {
      const updated = await overrideClaim(claimId, OFFICER, reason.trim());
      onResolved(updated);
      setOverriding(false);
    } catch {
      setErr("Couldn't record the override — check the backend and retry.");
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
            `<div class="turn"><div class="who">${esc(m.agent)}</div><div class="body">${esc(
              m.content,
            ).replace(/\n/g, "<br>")}</div></div>`,
        )
        .join("");
      const r = a.resolution ?? {};
      const fmt = (v: number | null | undefined) =>
        v == null ? "—" : `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;
      const ov = r.audit_trail?.officer_override as { by?: string; reason?: string; at?: string } | undefined;
      const sha = (r.audit_trail && r.audit_trail.transcript_sha256) || "—";
      const sig = ov
        ? `Panel recommendation <b>OVERRIDDEN &amp; DENIED</b> by ${esc(ov.by ?? "officer")}${ov.at ? " · " + esc(ov.at) : ""}${ov.reason ? `<br><i>Reason: ${esc(ov.reason)}</i>` : ""}`
        : r.approved_by
          ? `Reviewed, approved &amp; <b>signed</b> by ${esc(r.approved_by)}${r.approved_at ? " · " + esc(r.approved_at) : ""}`
          : "Pending human officer sign-off";
      const w = window.open("", "_blank");
      if (!w) return;
      w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Adjudication Record — ${a.claim_number}</title>
<style>
  body{font-family:Georgia,serif;color:#0e0e0e;max-width:760px;margin:36px auto;padding:0 24px;line-height:1.5}
  .brand{font-family:'Arial Black',Arial,sans-serif;font-weight:900;letter-spacing:-.03em;font-size:13px}
  .rule{height:6px;background:#0e0e0e;margin:6px 0 2px}
  h1{font-size:30px;margin:14px 0 0;letter-spacing:-.02em}
  .sub{font-family:monospace;font-size:12px;color:#555;margin:4px 0 18px}
  .grid{font-family:monospace;font-size:12px;border:2px solid #0e0e0e;padding:10px 14px;margin:14px 0;line-height:1.7}
  .grid b{display:inline-block;min-width:130px;color:#555;font-weight:normal}
  .verdict{border:3px solid #0e0e0e;padding:14px 18px;margin:18px 0;font-size:23px;font-weight:bold;background:#f5d90a22}
  .math{font-family:monospace;font-size:13px;border-left:5px solid #f5d90a;padding:6px 0 6px 12px;margin:12px 0}
  .turn{border-left:3px solid #0e0e0e;padding:4px 0 10px 12px;margin:10px 0}
  .who{font-family:monospace;text-transform:uppercase;font-size:11px;font-weight:bold;letter-spacing:.06em}
  .body{font-size:14px;white-space:normal}
  .sigbox{border:2px solid #0e0e0e;padding:12px 16px;margin-top:14px;font-size:14px}
  .meta{font-family:monospace;font-size:11px;color:#555;border-top:1px solid #ccc;margin-top:24px;padding-top:12px;word-break:break-all}
  h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;font-family:monospace;margin-top:26px}
</style></head><body>
  <div class="brand">RECOURSE — ADVERSARIAL CLAIMS ADJUDICATION</div>
  <div class="rule"></div>
  <h1>Adjudication Record</h1>
  <div class="sub">Tamper-evident · machine-verifiable · regulator-filable · generated ${esc(a.generated_at ?? "")}</div>
  <div class="grid">
    <b>Insurer</b> ${esc(a.insurance_company ?? "—")}<br>
    <b>Insured</b> ${esc(a.insured_name ?? "—")}<br>
    <b>Claim</b> ${esc(a.claim_number)} &nbsp;·&nbsp; <b style="min-width:0">Policy</b> ${esc(a.policy_number ?? "—")}<br>
    <b>Incident</b> ${esc(a.incident_type ?? "—")} on ${esc(a.incident_date ?? "—")}${a.location ? " · " + esc(a.location) : ""}<br>
    <b>Status</b> ${esc(a.status)}
  </div>
  <div class="verdict">${r.decision ?? "—"}${r.approved_amount != null ? " · " + fmt(r.approved_amount) : ""}</div>
  <div class="math">Amount requested ${fmt(a.amount_requested)} − Deductible ${fmt(a.deductible)} = <b>Payable if covered ${fmt(a.payable_if_covered)}</b></div>
  <h2>Legal reasoning</h2>
  <p>${esc(r.legal_reasoning).replace(/\n/g, "<br>")}</p>
  <h2>Cited clauses</h2><p>${(r.cited_clauses ?? []).map(esc).join(" · ") || "—"}</p>
  <h2>Adjudication transcript — full debate (Band room)</h2>${rows}
  <h2>Human officer sign-off</h2>
  <div class="sigbox">${sig}</div>
  <div class="meta">
    Band room: ${esc(a.band_room_id ?? "—")}<br>
    Tamper-evident transcript hash (SHA-256): ${esc(sha)}<br>
    Any edit to the recorded debate${r.audit_trail?.message_count ? ` (${esc(String(r.audit_trail.message_count))} messages)` : ""} changes this hash — the record is self-verifying.
  </div>
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
        className="border-b-[2.5px] border-[var(--ink)] px-5 py-4"
        style={{ background: d.bg, color: d.fg }}
      >
        <div className="uppercase-mono text-[10px] font-bold opacity-80">
          {override
            ? "Panel recommendation — overridden by officer"
            : resolution.approved_by
              ? "Officer-ratified decision"
              : "Panel recommendation · pending officer sign-off"}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-4">
          <span className="font-display text-3xl uppercase tracking-tight">{d.label}</span>
          {amt && <span className="font-mono text-3xl font-bold">{amt}</span>}
        </div>
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
            style={{ background: "#dc2626", color: "#fff", border: "2px solid var(--ink)" }}
          >
            {err}
          </div>
        )}

        {resolution.approved_by ? (
          override ? (
            <div
              className="px-4 py-3"
              style={{ background: "#dc2626", color: "#fff", border: "2.5px solid var(--ink)" }}
            >
              <div className="uppercase-mono text-[12px] font-bold">
                ⊘ Overridden &amp; denied by {resolution.approved_by}
              </div>
              {override.reason && (
                <div className="mt-1 text-[12px] opacity-90">“{override.reason}”</div>
              )}
              {resolution.approved_at && (
                <div className="uppercase-mono mt-1 text-[10px] opacity-80">
                  {new Date(resolution.approved_at).toLocaleString()}
                </div>
              )}
            </div>
          ) : (
            <div
              className="uppercase-mono px-4 py-3 text-[12px] font-bold"
              style={{ background: "#15803d", color: "#fff", border: "2.5px solid var(--ink)" }}
            >
              ✓ Signed off by {resolution.approved_by}
              {resolution.approved_at &&
                ` · ${new Date(resolution.approved_at).toLocaleString()}`}
            </div>
          )
        ) : overriding ? (
          <div
            className="space-y-2 p-3"
            style={{ background: "var(--paper-2)", border: "2.5px solid var(--ink)" }}
          >
            <div className="uppercase-mono text-[11px] font-bold text-[#dc2626]">
              ⊘ Override &amp; deny — state your reason for the record
            </div>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
              placeholder="e.g. Mechanic report unsigned; evidence insufficient to overturn §7.3."
              className="w-full resize-none p-2 text-[13px]"
              style={{ background: "var(--paper)", border: "2px solid var(--ink)" }}
            />
            <div className="flex flex-wrap gap-2">
              <button
                onClick={confirmOverride}
                disabled={busy || !reason.trim()}
                className="brut-hover uppercase-mono px-4 py-2 text-[12px] font-bold disabled:opacity-50"
                style={{ background: "#dc2626", color: "#fff", border: "2.5px solid var(--ink)" }}
              >
                {busy ? "Recording…" : "⊘ Confirm override & deny"}
              </button>
              <button
                onClick={() => setOverriding(false)}
                disabled={busy}
                className="brut-hover uppercase-mono px-4 py-2 text-[12px] font-bold"
                style={{ background: "var(--paper)", border: "2.5px solid var(--ink)" }}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              onClick={approve}
              disabled={busy}
              className="brut-hover uppercase-mono flex-1 px-5 py-3 text-sm font-bold disabled:opacity-60"
              style={{ background: "#15803d", color: "#fff", border: "2.5px solid var(--ink)", boxShadow: "var(--shadow)" }}
            >
              {busy ? "Signing off…" : "✓ Approve & sign off"}
            </button>
            <button
              onClick={() => setOverriding(true)}
              disabled={busy}
              className="brut-hover uppercase-mono px-5 py-3 text-sm font-bold text-[#dc2626]"
              style={{ background: "var(--paper)", border: "2.5px solid var(--ink)" }}
            >
              ⊘ Override &amp; deny
            </button>
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          <button
            onClick={printRecord}
            className="brut-hover uppercase-mono px-5 py-3 text-sm font-bold"
            style={{ background: "var(--signal)", border: "2.5px solid var(--ink)", boxShadow: "var(--shadow)" }}
          >
            ⤓ Download Signed Record
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
