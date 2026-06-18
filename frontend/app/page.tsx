"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import AgentAvatar from "@/components/AgentAvatar";
import SiteFooter from "@/components/SiteFooter";
import SiteHeader from "@/components/SiteHeader";
import StatusBadge from "@/components/StatusBadge";
import { getClaims } from "@/lib/api";
import { ROSTER, getAgent, textOn } from "@/lib/agents";
import type { Claim } from "@/lib/types";

const money0 = (v: number) =>
  `$${v.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
const day = (v: string) =>
  new Date(v + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

const RESOLVED = ["approved", "denied", "partial"];
const TABLE_COLS = "grid-cols-[1.3fr_1.2fr_1fr_0.9fr_1fr_0.9fr]";
const PANEL_MIN_H = "min-h-[132px]"; // every panel card matches the "Why adversarial" card

function Stat({
  label,
  value,
  sub,
  bg,
  flash,
}: {
  label: string;
  value: string;
  sub?: string;
  bg: string;
  flash?: boolean;
}) {
  return (
    <div className="brut px-4 py-3.5" style={{ background: bg, color: textOn(bg) }}>
      <div className="font-display flex items-center gap-2 text-4xl leading-none">
        {flash && <span className="flash h-2.5 w-2.5" style={{ background: textOn(bg) }} />}
        {value}
      </div>
      <div className="uppercase-mono mt-2 text-[10px] font-bold">{label}</div>
      {sub && <div className="mt-0.5 text-[11px] opacity-75">{sub}</div>}
    </div>
  );
}

function Step({
  n,
  title,
  body,
  accent,
}: {
  n: string;
  title: string;
  body: React.ReactNode;
  accent: string;
}) {
  return (
    <div className="brut-hover brut relative p-5" style={{ boxShadow: "var(--shadow)" }}>
      <div
        className="font-display absolute -right-3 -top-4 flex h-9 w-9 items-center justify-center text-lg"
        style={{ background: accent, color: textOn(accent), border: "2.5px solid var(--ink)" }}
      >
        {n}
      </div>
      <h3 className="font-display text-xl uppercase tracking-tight">{title}</h3>
      <p className="mt-2 text-[13px] leading-relaxed text-[var(--muted)]">{body}</p>
    </div>
  );
}

function PanelCard({ slug }: { slug: string }) {
  const a = getAgent(slug);
  return (
    <div className={`brut-hover brut flex ${PANEL_MIN_H} flex-col overflow-hidden`}>
      <div className="h-2 shrink-0" style={{ background: a.hex }} />
      <div className="flex flex-1 items-center gap-3.5 p-4" style={{ background: "var(--paper-2)" }}>
        <AgentAvatar slug={slug} size={60} />
        <div className="min-w-0">
          <div className="font-display text-lg uppercase leading-none tracking-tight">
            {a.name}
          </div>
          <div
            className="uppercase-mono mt-1.5 inline-block px-1.5 py-0.5 text-[9px] font-bold"
            style={{ background: a.hex, color: textOn(a.hex) }}
          >
            {a.role}
          </div>
          <div className="mt-2 text-[11px] leading-snug text-[var(--ink)]">{a.tagline}</div>
        </div>
      </div>
    </div>
  );
}

/** Quinn (SIU) — the 6th agent, shown as recruited-on-demand (not a standing panelist). */
function QuinnCard() {
  const a = getAgent("quinn");
  return (
    <div className={`brut-hover brut relative flex ${PANEL_MIN_H} flex-col overflow-hidden`}>
      <div
        className="uppercase-mono absolute right-0 top-0 px-2 py-1 text-[8px] font-bold"
        style={{
          background: a.hex,
          color: textOn(a.hex),
          borderLeft: "2.5px solid var(--ink)",
          borderBottom: "2.5px solid var(--ink)",
        }}
      >
        Recruited on demand
      </div>
      <div className="h-2 shrink-0" style={{ background: a.hex }} />
      <div className="flex flex-1 items-center gap-3.5 p-4" style={{ background: "var(--paper-2)" }}>
        <AgentAvatar slug="quinn" size={60} />
        <div className="min-w-0">
          <div className="font-display text-lg uppercase leading-none tracking-tight">{a.name}</div>
          <div
            className="uppercase-mono mt-1.5 inline-block px-1.5 py-0.5 text-[9px] font-bold"
            style={{ background: a.hex, color: textOn(a.hex) }}
          >
            {a.role}
          </div>
          <div className="mt-2 text-[11px] leading-snug text-[var(--ink)]">
            The Coordinator pulls Quinn into the room only when fraud or misrepresentation is
            alleged.
          </div>
        </div>
      </div>
    </div>
  );
}

function ClaimsDocket({ claims, err }: { claims: Claim[] | null; err: string | null }) {
  return (
    <section className="mt-12">
      <h2 className="font-display mb-5 text-2xl uppercase tracking-tight">Case docket</h2>

      {err && (
        <div
          className="uppercase-mono px-4 py-3 text-[12px] font-bold"
          style={{ background: "#dc2626", color: "#fff", border: "2.5px solid var(--ink)" }}
        >
          Backend unreachable — start the API on :8000. ({err})
        </div>
      )}

      {!claims && !err && (
        <div className="brut uppercase-mono px-5 py-6 text-xs text-[var(--muted)]">Loading…</div>
      )}

      {claims && claims.length === 0 && (
        <div className="brut flex flex-col items-center gap-4 p-10 text-center">
          <p className="text-sm text-[var(--muted)]">No claims yet.</p>
          <Link
            href="/new-claim"
            className="brut-hover uppercase-mono px-4 py-2 text-[12px] font-bold"
            style={{ background: "var(--signal)", border: "2.5px solid var(--ink)" }}
          >
            + File the first claim
          </Link>
        </div>
      )}

      {claims && claims.length > 0 && (
        <>
          {/* desktop table */}
          <div className="brut hidden md:block" style={{ boxShadow: "var(--shadow)" }}>
            <div
              className={`uppercase-mono grid ${TABLE_COLS} gap-4 border-b-[2.5px] border-[var(--ink)] bg-[var(--ink)] px-5 py-2.5 text-[10px] font-bold text-[var(--bg)]`}
            >
              <span>Claim №</span>
              <span>Insured</span>
              <span>Amount</span>
              <span>Type</span>
              <span>Status</span>
              <span className="text-right">Date</span>
            </div>
            {claims.map((c, i) => (
              <Link
                key={c.id}
                href={`/claims/${c.id}`}
                className={`grid ${TABLE_COLS} items-center gap-4 px-5 py-3.5 transition-colors hover:bg-[var(--signal)] ${
                  i > 0 ? "border-t-2 border-[var(--ink)]" : ""
                }`}
              >
                <span className="font-mono text-sm font-bold">{c.claim_number}</span>
                <span className="text-sm">{c.insured_name ?? "—"}</span>
                <span className="font-mono text-sm font-bold tabular-nums">
                  {money0(Number(c.amount_requested))}
                </span>
                <span className="uppercase-mono text-[10px] font-bold">{c.incident_type}</span>
                <StatusBadge status={c.status} />
                <span className="font-mono text-right text-[11px] text-[var(--muted)]">
                  {day(c.incident_date)}
                </span>
              </Link>
            ))}
          </div>

          {/* mobile cards */}
          <div className="flex flex-col gap-3 md:hidden">
            {claims.map((c) => (
              <Link key={c.id} href={`/claims/${c.id}`} className="brut-hover brut block p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-sm font-bold">{c.claim_number}</span>
                  <StatusBadge status={c.status} />
                </div>
                <div className="mt-1 font-display text-lg uppercase leading-none tracking-tight">
                  {c.insured_name ?? "—"}
                </div>
                <div className="uppercase-mono mt-2 flex items-center justify-between text-[10px] font-bold text-[var(--muted)]">
                  <span>
                    {c.incident_type} · {day(c.incident_date)}
                  </span>
                  <span className="font-mono text-sm text-[var(--ink)]">
                    {money0(Number(c.amount_requested))}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

/** A "start here" callout for hackathon judges: one click to a finished verdict (instant),
 *  one to a live run. Data-driven — picks the first resolved case and the first pending case. */
function JudgeBanner({ claims }: { claims: Claim[] | null }) {
  if (!claims || claims.length === 0) return null;
  const done = claims.find((c) => RESOLVED.includes(c.status));
  const pendings = claims.filter((c) => c.status === "pending");
  // Prefer a fraud/misrepresentation case for the live CTA so the run showcases the dynamic
  // SIU recruitment (Quinn); otherwise fall back to the first open case.
  const FRAUD = /fraud|misrepresent|undisclosed|rideshare|commercial|staged|intentional/i;
  const open = pendings.find((c) => FRAUD.test(c.original_denial_reason ?? "")) ?? pendings[0];
  if (!done && !open) return null;
  return (
    <div className="brut mb-9 p-5" style={{ background: "var(--signal)", boxShadow: "var(--shadow-lg)" }}>
      <div className="uppercase-mono flex items-center gap-2 text-[11px] font-bold">
        <span className="flash h-2.5 w-2.5" style={{ background: "var(--ink)" }} />
        Judges — try it in 30 seconds
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {done && (
          <Link
            href={`/claims/${done.id}`}
            className="brut-hover block p-4"
            style={{ background: "var(--paper)", border: "2.5px solid var(--ink)" }}
          >
            <div className="font-display text-lg uppercase tracking-tight">📄 See a finished verdict</div>
            <div className="mt-1 text-[13px] leading-snug text-[var(--muted)]">
              Open <b className="text-[var(--ink)]">{done.insured_name ?? done.claim_number}</b> — a
              completed adjudication where a fraud allegation pulled in a 6th SIU agent: the full
              debate, the signed resolution, and a one-click tamper-evident record.{" "}
              <b className="text-[var(--ink)]">Instant.</b>
            </div>
          </Link>
        )}
        {open && (
          <Link
            href={`/claims/${open.id}`}
            className="brut-hover block p-4"
            style={{ background: "var(--paper)", border: "2.5px solid var(--ink)" }}
          >
            <div className="font-display text-lg uppercase tracking-tight">▶ Run one live yourself</div>
            <div className="mt-1 text-[13px] leading-snug text-[var(--muted)]">
              Open <b className="text-[var(--ink)]">{open.insured_name ?? open.claim_number}</b> → click{" "}
              <b className="text-[var(--ink)]">“Open Adjudication Room”</b> and watch the agents debate
              it live through Band (~90s){FRAUD.test(open.original_denial_reason ?? "") ? ", including the SIU investigator pulled in for the fraud allegation" : ""}. A real run, not a recording.
            </div>
          </Link>
        )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [claims, setClaims] = useState<Claim[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const load = () => getClaims().then(setClaims).catch((e) => setErr(String(e)));
    load();
    // Re-fetch whenever the dashboard regains focus/visibility (covers the browser back button
    // and bfcache) so a claim that's mid-re-run shows "In Review", not a stale "Approved".
    const onShow = () => {
      if (document.visibilityState === "visible") load();
    };
    window.addEventListener("focus", onShow);
    window.addEventListener("pageshow", onShow);
    document.addEventListener("visibilitychange", onShow);
    return () => {
      window.removeEventListener("focus", onShow);
      window.removeEventListener("pageshow", onShow);
      document.removeEventListener("visibilitychange", onShow);
    };
  }, []);

  const all = claims ?? [];
  const resolved = all.filter((c) => RESOLVED.includes(c.status));
  const overturned = resolved.filter((c) => ["approved", "partial"].includes(c.status));
  const overturnRate = resolved.length
    ? Math.round((overturned.length / resolved.length) * 100)
    : 0;
  const inReview = all.filter((c) => c.status === "in_review").length;
  const inDispute = all.reduce((s, c) => s + Number(c.amount_requested || 0), 0);

  return (
    <main className="min-h-screen">
      <SiteHeader />

      <div className="mx-auto max-w-6xl px-6 py-10">
        {/* JUDGES — start here */}
        <JudgeBanner claims={claims} />

        {/* HERO */}
        <section className="grid items-end gap-8 lg:grid-cols-[1.4fr_1fr]">
          <div>
            <span
              className="uppercase-mono inline-block px-2 py-1 text-[10px] font-bold"
              style={{ background: "var(--ink)", color: "var(--bg)" }}
            >
              Crestview Mutual · Claims Desk
            </span>
            <h1 className="font-display mt-4 text-6xl uppercase leading-[0.92] tracking-tight sm:text-7xl">
              Adversarial
              <br />
              Adjudication
            </h1>
            <p className="mt-4 max-w-md text-[15px] leading-relaxed">
              Four AI adjudicators debate every disputed denial through Band — one fights for the
              insured, and an SIU investigator is recruited when fraud is alleged. The conversation{" "}
              <span className="font-extrabold">is</span> the legally-defensible audit trail.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Link
                href="/new-claim"
                className="brut-hover font-display px-6 py-3.5 text-lg uppercase tracking-tight"
                style={{ background: "var(--signal)", border: "2.5px solid var(--ink)", boxShadow: "var(--shadow)" }}
              >
                + File a Claim
              </Link>
              <a
                href="#panel"
                className="uppercase-mono px-2 py-1 text-[11px] font-bold text-[var(--muted)] hover:text-[var(--ink)]"
              >
                Meet the panel ↓
              </a>
            </div>
          </div>

          {/* roster cluster */}
          <div className="brut p-5" style={{ boxShadow: "var(--shadow-lg)" }}>
            <div className="uppercase-mono mb-3 text-[10px] font-bold text-[var(--muted)]">
              The standing panel
            </div>
            <div className="flex items-end gap-1">
              {[...ROSTER, "quinn"].map((slug) => {
                const a = getAgent(slug);
                return (
                  <div key={slug} className="flex flex-1 flex-col items-center gap-1.5">
                    <AgentAvatar slug={slug} size={48} />
                    <span className="uppercase-mono whitespace-nowrap text-[9px] font-bold">
                      {a.name}
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="mt-4 border-t-2 border-[var(--ink)] pt-3 text-[11px] leading-snug text-[var(--muted)]">
              Coordinator opens → Blake &amp; Morgan weigh coverage → Alex challenges → Sam rules →
              a human signs off. <span className="text-[var(--ink)]">Quinn (SIU) is pulled in only
              when fraud is alleged.</span>
            </div>
          </div>
        </section>

        {/* KPIs */}
        <section className="mt-10 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Stat label="Disputes filed" value={String(all.length)} bg="#ffffff" />
          <Stat
            label="Denials overturned"
            value={`${overturnRate}%`}
            sub={`${overturned.length} of ${resolved.length || 0} resolved`}
            bg="#15803d"
          />
          <Stat label="Value in dispute" value={money0(inDispute)} bg="#f5d90a" />
          <Stat
            label="In live review"
            value={String(inReview)}
            bg={inReview > 0 ? "#2d5bff" : "#ffffff"}
            flash={inReview > 0}
          />
        </section>

        {/* CASE DOCKET — most relevant, kept high */}
        <ClaimsDocket claims={claims} err={err} />

        {/* HOW IT WORKS — dark band so the white step cards pop */}
        <section className="mt-14">
          <div className="brut p-6 sm:p-8" style={{ background: "var(--ink)", boxShadow: "var(--shadow-lg)" }}>
            <h2 className="font-display text-2xl uppercase tracking-tight text-[var(--bg)]">
              How a verdict is reached
            </h2>
            <div className="mt-7 grid gap-6 md:grid-cols-3">
              <Step
                n="1"
                title="Intake"
                accent="#0e7490"
                body="A disputed denial enters. The Coordinator opens the case file — policy, evidence, the original denial — and convenes the panel in a live Band room."
              />
              <Step
                n="2"
                title="Adversarial debate"
                accent="#2d5bff"
                body={
                  <>
                    Blake checks coverage, Morgan quotes the policy verbatim, Alex fights for the
                    insured, Sam rules. Every message is recorded —{" "}
                    <span className="font-bold text-[var(--ink)]">the conversation is the audit trail.</span>
                  </>
                }
              />
              <Step
                n="3"
                title="Human sign-off"
                accent="#15803d"
                body="A claims officer ratifies the verdict or overrides it. The record is sealed with a tamper-evident SHA-256 hash — defensible to any regulator."
              />
            </div>
          </div>
        </section>

        {/* MEET THE PANEL */}
        <section id="panel" className="mt-14 scroll-mt-24">
          <div className="flex items-baseline justify-between">
            <h2 className="font-display text-2xl uppercase tracking-tight">Meet the panel</h2>
            <span className="uppercase-mono text-[10px] font-bold text-[var(--muted)]">
              5 standing + 1 on-call · 2 model providers
            </span>
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {ROSTER.map((slug) => (
              <PanelCard key={slug} slug={slug} />
            ))}
            <QuinnCard />
            <div
              className={`flex ${PANEL_MIN_H} flex-col justify-center p-4 text-[12px] leading-relaxed text-[var(--muted)]`}
              style={{ border: "2.5px dashed var(--ink)" }}
            >
              <span className="uppercase-mono text-[10px] font-bold text-[var(--ink)]">
                Why adversarial?
              </span>
              <p className="mt-1.5">
                A lone model rubber-stamps. A panel that must <span className="font-bold text-[var(--ink)]">argue</span>{" "}
                surfaces the exception a single pass would miss — and leaves a record of why.
              </p>
            </div>
          </div>
        </section>
      </div>

      <SiteFooter />
    </main>
  );
}
