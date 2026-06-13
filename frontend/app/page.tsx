"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import AgentAvatar from "@/components/AgentAvatar";
import SiteHeader from "@/components/SiteHeader";
import StatusBadge from "@/components/StatusBadge";
import { getClaims } from "@/lib/api";
import { ROSTER, getAgent, textOn } from "@/lib/agents";
import type { Claim } from "@/lib/types";

const money = (v: string) =>
  `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 0 })}`;
const day = (v: string) =>
  new Date(v + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

function Stat({ label, value, bg }: { label: string; value: number; bg: string }) {
  return (
    <div
      className="brut px-4 py-3"
      style={{ background: bg, color: textOn(bg) }}
    >
      <div className="font-display text-4xl leading-none">{value}</div>
      <div className="uppercase-mono mt-1.5 text-[10px] font-bold">{label}</div>
    </div>
  );
}

export default function Dashboard() {
  const [claims, setClaims] = useState<Claim[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getClaims().then(setClaims).catch((e) => setErr(String(e)));
  }, []);

  const stats = {
    total: claims?.length ?? 0,
    in_review: claims?.filter((c) => c.status === "in_review").length ?? 0,
    approved: claims?.filter((c) => c.status === "approved").length ?? 0,
    denied: claims?.filter((c) => ["denied", "partial"].includes(c.status)).length ?? 0,
  };

  return (
    <main className="min-h-screen">
      <SiteHeader />
      <div className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-7 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="font-display text-5xl uppercase leading-[0.95] tracking-tight">
              Adjudication
              <br />
              Dashboard
            </h1>
            <p className="mt-3 max-w-md text-sm text-[var(--ink)]">
              Four agents debate every disputed denial through Band. The conversation{" "}
              <span className="font-extrabold">is</span> the audit trail.
            </p>
          </div>
          <div className="flex flex-col items-start gap-3 md:items-end">
            <Link
              href="/new-claim"
              className="brut-hover uppercase-mono px-4 py-2 text-[12px] font-bold"
              style={{ background: "var(--signal)", border: "2.5px solid var(--ink)", boxShadow: "var(--shadow-sm)" }}
            >
              + New Claim
            </Link>
            <div className="flex gap-3">
            {ROSTER.map((slug) => {
              const a = getAgent(slug);
              return (
                <div key={slug} className="flex flex-col items-center gap-1.5">
                  <AgentAvatar slug={slug} size={48} />
                  <span className="uppercase-mono text-[9px] font-bold">{a.name}</span>
                </div>
              );
            })}
            </div>
          </div>
        </div>

        <div className="mb-7 grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat label="Total Claims" value={stats.total} bg="#ffffff" />
          <Stat label="In Review" value={stats.in_review} bg="#2d5bff" />
          <Stat label="Approved" value={stats.approved} bg="#16a34a" />
          <Stat label="Denied / Partial" value={stats.denied} bg="#ff3b30" />
        </div>

        <div className="brut">
          <div className="uppercase-mono grid grid-cols-[1.3fr_1.2fr_1fr_0.9fr_1fr_0.9fr] gap-4 border-b-[2.5px] border-[var(--ink)] bg-[var(--ink)] px-5 py-2.5 text-[10px] font-bold text-[var(--bg)]">
            <span>Claim №</span>
            <span>Insured</span>
            <span>Amount</span>
            <span>Type</span>
            <span>Status</span>
            <span className="text-right">Date</span>
          </div>

          {err && <div className="font-mono px-5 py-6 text-sm text-[#ff3b30]">Backend unreachable: {err}</div>}
          {!claims && !err && (
            <div className="uppercase-mono px-5 py-6 text-xs text-[var(--muted)]">Loading…</div>
          )}
          {claims?.map((c, i) => (
            <Link
              key={c.id}
              href={`/claims/${c.id}`}
              className={`grid grid-cols-[1.3fr_1.2fr_1fr_0.9fr_1fr_0.9fr] items-center gap-4 px-5 py-3.5 transition-colors hover:bg-[var(--signal)] ${
                i > 0 ? "border-t-2 border-[var(--ink)]" : ""
              }`}
            >
              <span className="font-mono text-sm font-bold">{c.claim_number}</span>
              <span className="text-sm">{c.insured_name ?? "—"}</span>
              <span className="font-mono text-sm font-bold tabular-nums">
                {money(c.amount_requested)}
              </span>
              <span className="uppercase-mono text-[10px] font-bold">{c.incident_type}</span>
              <StatusBadge status={c.status} />
              <span className="font-mono text-right text-[11px] text-[var(--muted)]">
                {day(c.incident_date)}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
