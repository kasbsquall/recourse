"use client";

import { useEffect, useRef } from "react";

import type { SupportingDoc } from "@/lib/types";

/** Overlay viewer for a supporting document — keeps the adjudication room in place so the
 *  judge always has a way back (✕, click-outside, or Esc). Loads the doc HTML in a sandboxed
 *  iframe, traps keyboard focus, and restores focus to the trigger on close. */
export default function DocModal({
  doc,
  onClose,
}: {
  doc: SupportingDoc | null;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const open = !!doc?.url;

  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    const el = dialogRef.current;
    el?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key !== "Tab" || !el) return;
      const f = el.querySelectorAll<HTMLElement>(
        'button, a[href], iframe, [tabindex]:not([tabindex="-1"])',
      );
      if (!f.length) return;
      const first = f[0];
      const last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      prev?.focus?.();
    };
  }, [open, onClose]);

  if (!doc || !doc.url) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-8"
      style={{ background: "rgba(14,14,14,.55)" }}
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="docmodal-title"
        tabIndex={-1}
        className="brut flex h-full max-h-[88vh] w-full max-w-3xl flex-col overflow-hidden bg-[var(--paper)] focus:outline-none"
        style={{ boxShadow: "var(--shadow-lg)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b-[2.5px] border-[var(--ink)] bg-[var(--ink)] px-4 py-2">
          <span id="docmodal-title" className="uppercase-mono text-[11px] font-bold text-[var(--bg)]">
            {doc.type} · {doc.ref}
          </span>
          <div className="flex items-center gap-4">
            <a
              href={doc.url}
              target="_blank"
              rel="noreferrer"
              className="uppercase-mono text-[10px] font-bold text-[var(--bg)] underline opacity-80 hover:opacity-100"
            >
              Open in tab ↗
            </a>
            <button
              onClick={onClose}
              aria-label="Close document"
              className="uppercase-mono text-[15px] font-bold leading-none text-[var(--bg)] hover:text-[#dc2626]"
            >
              ✕
            </button>
          </div>
        </div>
        <iframe
          src={doc.url}
          title={`${doc.type} ${doc.ref}`}
          sandbox="allow-scripts allow-same-origin"
          className="w-full flex-1 bg-white"
        />
      </div>
    </div>
  );
}
