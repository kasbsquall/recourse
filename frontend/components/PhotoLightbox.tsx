"use client";

import { useEffect, useRef, useState } from "react";

export type LightboxPhoto = { src: string; caption: string };

/** Full-size single-photo viewer with prev/next + caption. Opening from a thumbnail shows that
 *  exact image; arrows or ←/→ browse the rest. Mount with key={startIndex} so each open starts
 *  on the chosen photo. Traps focus and restores it to the trigger on close. */
export default function PhotoLightbox({
  photos,
  startIndex,
  onClose,
}: {
  photos: LightboxPhoto[];
  startIndex: number | null;
  onClose: () => void;
}) {
  const [i, setI] = useState(startIndex ?? 0);
  const dialogRef = useRef<HTMLDivElement>(null);
  const open = startIndex !== null;

  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    const el = dialogRef.current;
    el?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") return onClose();
      if (e.key === "ArrowRight") return setI((v) => (v + 1) % photos.length);
      if (e.key === "ArrowLeft") return setI((v) => (v - 1 + photos.length) % photos.length);
      if (e.key !== "Tab" || !el) return;
      const f = el.querySelectorAll<HTMLElement>('button, a[href], [tabindex]:not([tabindex="-1"])');
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
  }, [open, onClose, photos.length]);

  if (!open) return null;
  const p = photos[i];
  if (!p) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-8"
      style={{ background: "rgba(14,14,14,.7)" }}
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="lightbox-title"
        tabIndex={-1}
        className="brut flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden bg-[var(--paper)] focus:outline-none"
        style={{ boxShadow: "var(--shadow-lg)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b-[2.5px] border-[var(--ink)] bg-[var(--ink)] px-4 py-2">
          <span id="lightbox-title" className="uppercase-mono text-[11px] font-bold text-[var(--bg)]">
            Crash photo {i + 1} / {photos.length}
          </span>
          <button
            onClick={onClose}
            aria-label="Close photo viewer"
            className="uppercase-mono text-[15px] font-bold leading-none text-[var(--bg)] hover:text-[#dc2626]"
          >
            ✕
          </button>
        </div>

        <div
          className="relative flex flex-1 items-center justify-center"
          style={{ minHeight: 0, background: "#0e0e0e" }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={p.src} alt={p.caption} className="max-h-[68vh] w-full object-contain" />
          {photos.length > 1 && (
            <>
              <button
                onClick={() => setI((v) => (v - 1 + photos.length) % photos.length)}
                aria-label="Previous photo"
                className="brut-hover absolute left-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center text-xl font-bold leading-none"
                style={{ background: "var(--paper)", border: "2.5px solid var(--ink)" }}
              >
                ‹
              </button>
              <button
                onClick={() => setI((v) => (v + 1) % photos.length)}
                aria-label="Next photo"
                className="brut-hover absolute right-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center text-xl font-bold leading-none"
                style={{ background: "var(--paper)", border: "2.5px solid var(--ink)" }}
              >
                ›
              </button>
            </>
          )}
        </div>

        <div className="border-t-[2.5px] border-[var(--ink)] bg-[var(--paper-2)] px-4 py-2.5 text-[13px] font-bold">
          {p.caption}
        </div>
      </div>
    </div>
  );
}
