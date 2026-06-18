"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import AgentAvatar from "@/components/AgentAvatar";
import SiteFooter from "@/components/SiteFooter";
import SiteHeader from "@/components/SiteHeader";
import { ROSTER, getAgent } from "@/lib/agents";
import { createClaim, getPolicies } from "@/lib/api";
import type { Policy } from "@/lib/types";

const FIELD =
  "w-full border-[2.5px] border-[var(--ink)] bg-[var(--paper)] px-3 py-2.5 text-sm focus:outline-none focus:bg-[var(--signal)]";
const LABEL = "uppercase-mono mb-1.5 block text-[10px] font-bold text-[var(--muted)]";
const SECTION = "uppercase-mono mb-3 text-[10px] font-bold text-[var(--ink)]";

const money = (v: string | number) =>
  `$${Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;

export default function NewClaim() {
  const router = useRouter();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [policyId, setPolicyId] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getPolicies().then(setPolicies).catch(() => setErr("Backend unreachable."));
  }, []);

  const policy = useMemo(
    () => policies.find((p) => p.id === policyId) ?? null,
    [policies, policyId],
  );

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
      <div className="mx-auto max-w-5xl px-6 py-8">
        <Link
          href="/"
          className="uppercase-mono mb-5 inline-block text-[11px] font-bold hover:text-[var(--muted)]"
        >
          ← Dashboard
        </Link>
        <h1 className="font-display mb-1 text-4xl uppercase tracking-tight sm:text-5xl">
          File a Disputed Claim
        </h1>
        <p className="mb-6 max-w-lg text-sm text-[var(--muted)]">
          Submit a denied claim to convene the adjudication panel — the agents debate it through
          Band, and a fraud investigator is called in when misrepresentation is alleged. The debate
          becomes the legally-defensible record.
        </p>

        {err && (
          <div
            className="uppercase-mono mb-4 px-3 py-2 text-[11px] font-bold"
            style={{ background: "#dc2626", color: "#fff", border: "2px solid var(--ink)" }}
          >
            {err}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          {/* FORM */}
          <form onSubmit={submit} className="brut space-y-6 p-6" style={{ boxShadow: "var(--shadow)" }}>
            <div>
              <div className={SECTION}>① The policy</div>
              <label htmlFor="policy_id" className={LABEL}>
                Policyholder
              </label>
              <select
                id="policy_id"
                name="policy_id"
                required
                className={FIELD}
                value={policyId}
                onChange={(e) => setPolicyId(e.target.value)}
              >
                <option value="" disabled>
                  Select a policy…
                </option>
                {policies.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.policy_number} — {p.insured_name} ({p.policy_type})
                  </option>
                ))}
              </select>
              {policy && (
                <div
                  className="uppercase-mono mt-2 flex flex-wrap gap-x-4 gap-y-1 px-3 py-2 text-[10px] font-bold text-[var(--muted)]"
                  style={{ background: "var(--paper-2)", border: "2px solid var(--ink)" }}
                >
                  <span>
                    Limit <span className="text-[var(--ink)]">{money(policy.coverage_limit)}</span>
                  </span>
                  <span>
                    Deductible{" "}
                    <span className="text-[var(--ink)]">{money(policy.deductible)}</span>
                  </span>
                  <span>
                    State <span className="text-[var(--ink)]">{policy.state}</span>
                  </span>
                </div>
              )}
            </div>

            <div className="border-t-2 border-[var(--ink)] pt-5">
              <div className={SECTION}>② The incident</div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="incident_type" className={LABEL}>
                    Incident Type
                  </label>
                  <select id="incident_type" name="incident_type" required className={FIELD} defaultValue="collision">
                    <option value="collision">Collision</option>
                    <option value="comprehensive">Comprehensive</option>
                    <option value="theft">Theft</option>
                    <option value="liability">Liability</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="incident_date" className={LABEL}>
                    Incident Date
                  </label>
                  <input
                    id="incident_date"
                    name="incident_date"
                    type="date"
                    required
                    className={FIELD}
                    defaultValue="2024-10-15"
                  />
                </div>
                <div>
                  <label htmlFor="amount_requested" className={LABEL}>
                    Amount Requested ($)
                  </label>
                  <input
                    id="amount_requested"
                    name="amount_requested"
                    type="number"
                    min="0"
                    step="0.01"
                    required
                    className={FIELD}
                    placeholder="12500.00"
                  />
                </div>
                <div>
                  <label htmlFor="location" className={LABEL}>
                    Location
                  </label>
                  <input id="location" name="location" className={FIELD} placeholder="I-95 North, FL" />
                </div>
              </div>
              <div className="mt-4">
                <label htmlFor="incident_description" className={LABEL}>
                  Incident Description
                </label>
                <textarea
                  id="incident_description"
                  name="incident_description"
                  required
                  rows={4}
                  className={FIELD}
                  placeholder="What happened, with any supporting evidence (police report, mechanic report, witnesses)…"
                />
              </div>
            </div>

            <div className="border-t-2 border-[var(--ink)] pt-5">
              <div className={SECTION}>③ The denial under dispute</div>
              <label htmlFor="original_denial_reason" className={LABEL}>
                Original Denial Reason
              </label>
              <textarea
                id="original_denial_reason"
                name="original_denial_reason"
                rows={2}
                className={FIELD}
                placeholder="e.g. Denied because the insurer says the engine fault was a pre-existing mechanical problem, not caused by the crash."
              />
              <p className="mt-1.5 text-[11px] leading-snug text-[var(--muted)]">
                Plain English is fine — no jargon or clause numbers required. The agents map it to
                the policy themselves.
              </p>
            </div>

            <button
              type="submit"
              disabled={busy}
              className="brut-hover font-display w-full px-6 py-4 text-lg uppercase tracking-tight disabled:opacity-60"
              style={{ background: "var(--signal)", border: "2.5px solid var(--ink)", boxShadow: "var(--shadow)" }}
            >
              {busy ? "Convening the panel…" : "⚖ File & Open Adjudication"}
            </button>
          </form>

          {/* WHAT HAPPENS NEXT */}
          <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start">
            <div className="brut" style={{ boxShadow: "var(--shadow)" }}>
              <div className="uppercase-mono border-b-[2.5px] border-[var(--ink)] bg-[var(--ink)] px-3 py-1.5 text-[11px] font-bold text-[var(--bg)]">
                What happens next
              </div>
              <ol className="space-y-3 p-4">
                {ROSTER.map((slug, i) => {
                  const a = getAgent(slug);
                  return (
                    <li key={slug} className="flex items-center gap-3">
                      <AgentAvatar slug={slug} size={34} />
                      <div className="min-w-0">
                        <div className="font-display text-sm uppercase leading-none tracking-tight">
                          {a.name}
                        </div>
                        <div className="text-[11px] leading-snug text-[var(--muted)]">
                          {a.role}
                        </div>
                      </div>
                      {i < ROSTER.length - 1 && (
                        <span className="ml-auto text-[var(--muted)]">↓</span>
                      )}
                    </li>
                  );
                })}
              </ol>
              <div className="flex items-center gap-3 border-t-2 border-[var(--ink)] px-4 py-2.5">
                <AgentAvatar slug="quinn" size={34} />
                <div className="min-w-0">
                  <div className="font-display text-sm uppercase leading-none tracking-tight">
                    Quinn
                  </div>
                  <div className="text-[11px] leading-snug text-[var(--muted)]">
                    Special Investigations Unit — only if fraud is alleged
                  </div>
                </div>
              </div>
            </div>
            <div
              className="p-4 text-[12px] leading-relaxed text-[var(--muted)]"
              style={{ border: "2.5px dashed var(--ink)" }}
            >
              The moment you file, the panel convenes live in a Band room and debates the denial.
              You&apos;ll watch it unfold — and the transcript is sealed with a tamper-evident hash.
            </div>

            <div className="brut" style={{ boxShadow: "var(--shadow)" }}>
              <div className="uppercase-mono border-b-[2.5px] border-[var(--ink)] bg-[var(--paper-2)] px-3 py-1.5 text-[10px] font-bold text-[var(--muted)]">
                Glossary
              </div>
              <dl className="space-y-2 p-4 text-[12px] leading-snug">
                <div>
                  <dt className="font-mono font-bold">§ 7.3</dt>
                  <dd className="text-[var(--muted)]">A numbered clause (section) in the policy.</dd>
                </div>
                <div>
                  <dt className="font-bold">Collision vs Comprehensive</dt>
                  <dd className="text-[var(--muted)]">
                    Collision = crash damage. Comprehensive = non-crash loss (theft, fire, flood).
                  </dd>
                </div>
                <div>
                  <dt className="font-bold">Deductible</dt>
                  <dd className="text-[var(--muted)]">
                    What the insured pays before coverage applies.
                  </dd>
                </div>
              </dl>
            </div>
          </aside>
        </div>
      </div>

      <SiteFooter />
    </main>
  );
}
