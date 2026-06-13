"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import SiteHeader from "@/components/SiteHeader";
import { createClaim, getPolicies } from "@/lib/api";
import type { Policy } from "@/lib/types";

const FIELD =
  "w-full border-[2.5px] border-[var(--ink)] bg-[var(--paper)] px-3 py-2.5 text-sm focus:outline-none focus:bg-[var(--signal)]";
const LABEL = "uppercase-mono mb-1.5 block text-[10px] font-bold text-[var(--muted)]";

export default function NewClaim() {
  const router = useRouter();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getPolicies().then(setPolicies).catch(() => setErr("Backend unreachable."));
  }, []);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    const f = new FormData(e.currentTarget);
    try {
      const claim = await createClaim({
        policy_id: String(f.get("policy_id")),
        incident_date: String(f.get("incident_date")),
        incident_type: String(f.get("incident_type")),
        location: String(f.get("location") || ""),
        incident_description: String(f.get("incident_description")),
        amount_requested: Number(f.get("amount_requested")),
        original_denial_reason: String(f.get("original_denial_reason") || ""),
      });
      router.push(`/claims/${claim.id}`);
    } catch {
      setErr("Couldn't create the claim — check the backend and try again.");
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen">
      <SiteHeader subtitle="New Claim" />
      <div className="mx-auto max-w-2xl px-6 py-8">
        <Link href="/" className="uppercase-mono mb-5 inline-block text-[11px] font-bold hover:text-[var(--muted)]">
          ← Dashboard
        </Link>
        <h1 className="font-display mb-1 text-4xl uppercase tracking-tight">File a Disputed Claim</h1>
        <p className="mb-6 text-sm text-[var(--muted)]">
          Submit a denial to convene the adjudication panel.
        </p>

        {err && (
          <div className="uppercase-mono mb-4 px-3 py-2 text-[11px] font-bold" style={{ background: "#ff3b30", color: "#fff", border: "2px solid var(--ink)" }}>
            {err}
          </div>
        )}

        <form onSubmit={submit} className="brut space-y-4 p-6">
          <div>
            <label className={LABEL}>Policy</label>
            <select name="policy_id" required className={FIELD} defaultValue="">
              <option value="" disabled>Select a policy…</option>
              {policies.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.policy_number} — {p.insured_name} ({p.policy_type})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={LABEL}>Incident Type</label>
              <select name="incident_type" required className={FIELD} defaultValue="collision">
                <option value="collision">Collision</option>
                <option value="comprehensive">Comprehensive</option>
                <option value="theft">Theft</option>
                <option value="liability">Liability</option>
              </select>
            </div>
            <div>
              <label className={LABEL}>Incident Date</label>
              <input name="incident_date" type="date" required className={FIELD} defaultValue="2024-10-15" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={LABEL}>Amount Requested ($)</label>
              <input name="amount_requested" type="number" min="0" step="0.01" required className={FIELD} placeholder="12500.00" />
            </div>
            <div>
              <label className={LABEL}>Location</label>
              <input name="location" className={FIELD} placeholder="I-95 North, FL" />
            </div>
          </div>

          <div>
            <label className={LABEL}>Incident Description</label>
            <textarea name="incident_description" required rows={4} className={FIELD} placeholder="What happened, with any supporting evidence (police report, mechanic report, witnesses)…" />
          </div>

          <div>
            <label className={LABEL}>Original Denial Reason</label>
            <textarea name="original_denial_reason" rows={2} className={FIELD} placeholder="e.g. Denied per §7.3 — Mechanical Failure Exclusion." />
          </div>

          <button
            type="submit"
            disabled={busy}
            className="brut-hover font-display w-full px-6 py-4 text-lg uppercase tracking-tight disabled:opacity-60"
            style={{ background: "var(--signal)", border: "2.5px solid var(--ink)", boxShadow: "var(--shadow)" }}
          >
            {busy ? "Filing…" : "⚖ File & Open Adjudication"}
          </button>
        </form>
      </div>
    </main>
  );
}
