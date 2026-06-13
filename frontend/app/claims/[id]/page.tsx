"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import DebateRoom from "@/components/DebateRoom";
import ResolutionPanel from "@/components/ResolutionPanel";
import SiteHeader from "@/components/SiteHeader";
import StatusBadge from "@/components/StatusBadge";
import { adjudicate, getClaim, streamDebate } from "@/lib/api";
import type { ClaimDetail, ClaimStatus, Message, Resolution } from "@/lib/types";

const money = (v: string) =>
  `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

export default function ClaimRoom() {
  const { id } = useParams<{ id: string }>();
  const [claim, setClaim] = useState<ClaimDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<ClaimStatus>("pending");
  const [resolution, setResolution] = useState<Resolution | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const unsubRef = useRef<(() => void) | null>(null);

  const mergeMessage = useCallback((m: Message) => {
    setMessages((prev) => (prev.some((x) => x.id === m.id) ? prev : [...prev, m]));
  }, []);

  const startStream = useCallback(
    (claimId: string) => {
      unsubRef.current?.();
      unsubRef.current = streamDebate(claimId, mergeMessage, async (finalStatus) => {
        setStatus(finalStatus as ClaimStatus);
        const fresh = await getClaim(claimId);
        setResolution(fresh.resolution);
        setMessages(fresh.messages);
      });
    },
    [mergeMessage],
  );

  useEffect(() => {
    if (!id) return;
    getClaim(id)
      .then((c) => {
        setClaim(c);
        setMessages(c.messages);
        setStatus(c.status);
        setResolution(c.resolution);
        if (c.status === "in_review") startStream(c.id);
      })
      .catch(() => setErr("Couldn't load this claim — is the backend running?"));
    return () => unsubRef.current?.();
  }, [id, startStream]);

  async function openRoom() {
    if (!claim) return;
    setErr(null);
    setMessages([]);
    setResolution(null);
    setStatus("in_review");
    try {
      await adjudicate(claim.id);
      startStream(claim.id);
    } catch {
      setStatus("pending");
      setErr("Couldn't reach the adjudication service — check the backend and retry.");
    }
  }

  if (!claim)
    return (
      <main className="min-h-screen">
        <SiteHeader />
        <div className="uppercase-mono mx-auto max-w-6xl px-6 py-16 text-sm text-[var(--muted)]">
          Loading…
        </div>
      </main>
    );

  return (
    <main className="min-h-screen">
      <SiteHeader subtitle="Adjudication Room" />
      <div className="mx-auto max-w-6xl px-6 py-8">
        <Link
          href="/"
          className="uppercase-mono mb-5 inline-block text-[11px] font-bold text-[var(--ink)] hover:text-[var(--muted)]"
        >
          ← Dashboard
        </Link>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,38%)_minmax(0,1fr)]">
          {/* LEFT — case file */}
          <aside className="space-y-5 lg:sticky lg:top-24 lg:self-start">
            <div className="brut p-5">
              <div className="mb-3 flex items-center justify-between">
                <span className="font-mono text-sm font-bold">{claim.claim_number}</span>
                <StatusBadge status={status} />
              </div>
              <h1 className="font-display text-3xl uppercase leading-none tracking-tight">
                {claim.policy?.insured_name}
              </h1>
              <p className="uppercase-mono mt-1.5 text-[10px] font-bold text-[var(--muted)]">
                {claim.policy?.policy_number} · {claim.policy?.insurance_company}
              </p>

              <dl className="mt-4 space-y-0">
                <Row k="Amount" v={money(claim.amount_requested)} />
                <Row k="Type" v={claim.incident_type} />
                <Row k="Incident" v={claim.incident_date} />
                <Row k="Location" v={claim.location ?? "—"} />
                {claim.policy && (
                  <Row
                    k="Coverage"
                    v={`${money(claim.policy.coverage_limit)} / $${Number(
                      claim.policy.deductible,
                    ).toLocaleString()} ded`}
                  />
                )}
              </dl>
            </div>

            <div className="brut" style={{ boxShadow: "var(--shadow)" }}>
              <div className="uppercase-mono border-b-[2.5px] border-[var(--ink)] bg-[#ff3b30] px-3 py-1.5 text-[11px] font-bold text-white">
                ✕ Original Denial
              </div>
              <p className="p-4 text-sm leading-relaxed">{claim.original_denial_reason}</p>
            </div>

            {claim.supporting_docs?.length > 0 && (
              <div className="brut p-5">
                <div className="uppercase-mono mb-3 text-[10px] font-bold text-[var(--muted)]">
                  Supporting Documents
                </div>
                <ul className="space-y-2.5">
                  {claim.supporting_docs.map((d) => {
                    const inner = (
                      <>
                        <div className="font-mono flex items-center gap-1.5 text-[11px] font-bold">
                          {d.type} · {d.ref}
                          {d.url && <span className="text-[var(--accent)]">↗ view</span>}
                        </div>
                        <div className="text-[var(--muted)]">{d.summary}</div>
                      </>
                    );
                    return d.url ? (
                      <li key={d.ref}>
                        <a
                          href={d.url}
                          target="_blank"
                          rel="noreferrer"
                          className="brut-hover block border-l-[3px] border-[var(--ink)] bg-[var(--paper-2)] py-2 pl-3 pr-2 text-sm"
                        >
                          {inner}
                        </a>
                      </li>
                    ) : (
                      <li key={d.ref} className="border-l-[3px] border-[var(--ink)] pl-3 text-sm">
                        {inner}
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </aside>

          {/* RIGHT — adjudication */}
          <section className="space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-2xl uppercase tracking-tight">
                Adjudication Room
              </h2>
              {status === "in_review" && (
                <span className="uppercase-mono flash flex items-center gap-2 text-[11px] font-bold text-[#2d5bff]">
                  <span className="h-2.5 w-2.5 bg-[#2d5bff]" />
                  In progress
                </span>
              )}
              {["approved", "denied", "partial"].includes(status) && (
                <button
                  onClick={openRoom}
                  className="brut-hover uppercase-mono px-3 py-1.5 text-[11px] font-bold"
                  style={{ background: "var(--paper)", border: "2px solid var(--ink)" }}
                >
                  ↻ Re-run
                </button>
              )}
            </div>

            {err && (
              <div
                className="uppercase-mono px-4 py-3 text-[12px] font-bold"
                style={{ background: "#ff3b30", color: "#fff", border: "2.5px solid var(--ink)" }}
              >
                {err}
              </div>
            )}

            {status === "pending" && messages.length === 0 ? (
              <div className="brut flex flex-col items-center gap-5 p-10 text-center">
                <p className="max-w-sm text-sm">
                  Convene Blake, Morgan, Alex, and Sam to debate this denial in a live Band
                  room.
                </p>
                <button
                  onClick={openRoom}
                  className="brut-hover font-display px-7 py-4 text-lg uppercase tracking-tight"
                  style={{ background: "var(--signal)", border: "2.5px solid var(--ink)", boxShadow: "var(--shadow)" }}
                >
                  ⚖ Open Adjudication Room
                </button>
              </div>
            ) : (
              <DebateRoom messages={messages} status={status} />
            )}

            {resolution && (
              <ResolutionPanel
                claimId={claim.id}
                resolution={resolution}
                onApproved={setResolution}
              />
            )}

            {!resolution && ["approved", "denied", "partial"].includes(status) && (
              <div className="brut p-6 text-center" style={{ boxShadow: "var(--shadow)" }}>
                <div className="uppercase-mono mb-2 text-[11px] font-bold text-[var(--muted)]">
                  Inconclusive
                </div>
                <p className="text-sm">
                  The panel didn&apos;t reach a recorded resolution. Re-run the adjudication.
                </p>
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-t-2 border-[var(--ink)] py-2 first:border-t-0">
      <dt className="uppercase-mono text-[10px] font-bold text-[var(--muted)]">{k}</dt>
      <dd className="text-right text-sm font-bold capitalize">{v}</dd>
    </div>
  );
}
