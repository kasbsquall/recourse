"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import DebateRoom from "@/components/DebateRoom";
import DebateTimeline from "@/components/DebateTimeline";
import DocModal from "@/components/DocModal";
import PhotoLightbox, { type LightboxPhoto } from "@/components/PhotoLightbox";
import ResolutionPanel from "@/components/ResolutionPanel";
import SiteHeader from "@/components/SiteHeader";
import StatusBadge from "@/components/StatusBadge";
import { adjudicate, getClaim, streamDebate } from "@/lib/api";
import type {
  ClaimDetail,
  ClaimStatus,
  Message,
  Resolution,
  SupportingDoc,
} from "@/lib/types";

const money = (v: string) =>
  `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

const ADJUDICATOR_SLUGS = ["blake", "morgan", "alex", "sam"];

const CRASH_PHOTOS: LightboxPhoto[] = [
  { src: "/docs/crash-1.jpg", caption: "Front-end crush — driver side quarter" },
  { src: "/docs/crash-2.jpg", caption: "Engine compartment — impact damage to oil pan" },
  { src: "/docs/crash-3.jpg", caption: "Guardrail contact point — I-95 MM26" },
  { src: "/docs/crash-4.jpg", caption: "Deployed airbags — cabin" },
];

export default function ClaimRoom() {
  const { id } = useParams<{ id: string }>();
  const [claim, setClaim] = useState<ClaimDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<ClaimStatus>("pending");
  const [resolution, setResolution] = useState<Resolution | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [activeDoc, setActiveDoc] = useState<SupportingDoc | null>(null);
  const [photoIndex, setPhotoIndex] = useState<number | null>(null);
  const unsubRef = useRef<(() => void) | null>(null);

  const turnsPosted = new Set(
    messages.filter((m) => ADJUDICATOR_SLUGS.includes(m.agent_slug)).map((m) => m.agent_slug),
  ).size;

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

  const closeDoc = useCallback(() => setActiveDoc(null), []);
  const closePhoto = useCallback(() => setPhotoIndex(null), []);

  const scrollToAgent = useCallback((slug: string) => {
    // The seek targets carry `scroll-mt-[120px]`, so this lands the message cleanly below the
    // sticky header + timeline bars. Smooth in real browsers; instant where motion is unsupported.
    document
      .getElementById(`seek-${slug}`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

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

        <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
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
              <div className="uppercase-mono border-b-[2.5px] border-[var(--ink)] bg-[#dc2626] px-3 py-1.5 text-[11px] font-bold text-white">
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
                        <div className="flex items-start justify-between gap-2">
                          <span className="font-mono text-[11px] font-bold">
                            {d.type} · {d.ref}
                          </span>
                          {d.url && (
                            <span
                              className="uppercase-mono shrink-0 px-1.5 py-0.5 text-[9px] font-bold leading-none"
                              style={{ background: "var(--signal)", border: "1.5px solid var(--ink)" }}
                            >
                              View ↗
                            </span>
                          )}
                        </div>
                        <div className="mt-1 text-[var(--muted)]">{d.summary}</div>
                      </>
                    );
                    return d.url ? (
                      <li key={d.ref}>
                        <button
                          onClick={() => setActiveDoc(d)}
                          className="brut-hover block w-full border-l-[3px] border-[var(--ink)] bg-[var(--paper-2)] py-2 pl-3 pr-2 text-left text-sm"
                        >
                          {inner}
                        </button>
                        {d.type === "photos" && (
                          <div className="mt-2 grid grid-cols-4 gap-1.5">
                            {[1, 2, 3, 4].map((n) => (
                              <button
                                key={n}
                                onClick={() => setPhotoIndex(n - 1)}
                                className="brut-hover overflow-hidden"
                                style={{ border: "2px solid var(--ink)", aspectRatio: "4 / 3" }}
                                title={CRASH_PHOTOS[n - 1]?.caption}
                              >
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                  src={`/docs/crash-${n}.jpg`}
                                  alt={`Crash photo ${n}`}
                                  loading="lazy"
                                  className="h-full w-full object-cover"
                                />
                              </button>
                            ))}
                          </div>
                        )}
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
                <span className="uppercase-mono flex items-center gap-2 text-[11px] font-bold text-[#2d5bff]">
                  <span className="flash flex items-center gap-2">
                    <span className="h-2.5 w-2.5 bg-[#2d5bff]" />
                    Live · debating
                  </span>
                  {turnsPosted > 0 && (
                    <span className="text-[var(--muted)]">· {turnsPosted} turns in</span>
                  )}
                </span>
              )}
              {["approved", "denied", "partial"].includes(status) &&
                !resolution?.approved_by && (
                  <button
                    onClick={openRoom}
                    className="brut-hover uppercase-mono px-3 py-1.5 text-[11px] font-bold"
                    style={{ background: "var(--paper)", border: "2px solid var(--ink)" }}
                  >
                    ↻ Re-run
                  </button>
                )}
              {resolution?.approved_by && (
                <span className="uppercase-mono flex items-center gap-2 text-[11px] font-bold text-[#15803d]">
                  <span className="h-2.5 w-2.5 bg-[#15803d]" />
                  Final · signed off
                </span>
              )}
            </div>

            {err && (
              <div
                className="uppercase-mono px-4 py-3 text-[12px] font-bold"
                style={{ background: "#dc2626", color: "#fff", border: "2.5px solid var(--ink)" }}
              >
                {err}
              </div>
            )}

            {(status === "in_review" || messages.length > 0) && (
              <div className="brut px-3 py-3" style={{ boxShadow: "var(--shadow-sm)" }}>
                <DebateTimeline messages={messages} status={status} onSeek={scrollToAgent} />
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
              <DebateRoom
                messages={messages}
                status={status}
                docs={claim.supporting_docs}
                onOpenDoc={setActiveDoc}
              />
            )}

            {resolution && (
              <div id="seek-verdict" className="scroll-mt-[72px]">
                <ResolutionPanel
                  claimId={claim.id}
                  resolution={resolution}
                  onResolved={(c) => {
                    setResolution(c.resolution);
                    setStatus(c.status);
                  }}
                />
              </div>
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

      <DocModal doc={activeDoc} onClose={closeDoc} />
      <PhotoLightbox
        key={photoIndex}
        photos={CRASH_PHOTOS}
        startIndex={photoIndex}
        onClose={closePhoto}
      />
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
