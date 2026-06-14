import RecourseLogo from "./RecourseLogo";

/** Insurer-console footer. Carries the product tagline and partner/track attribution —
 *  the latter matters for hackathon partner prizes (Band, AI/ML API, Featherless). */
export default function SiteFooter() {
  return (
    <footer className="mt-12 border-t-[3px] border-[var(--ink)] bg-[var(--bg)]">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <RecourseLogo className="h-5 w-auto text-[var(--ink)]" />
          <span className="text-[11px] text-[var(--muted)]">
            The conversation <span className="font-extrabold text-[var(--ink)]">is</span> the
            audit trail.
          </span>
        </div>

        <div className="uppercase-mono flex flex-col gap-1.5 text-[10px] font-bold text-[var(--muted)] md:items-end">
          <span>
            Built on <span className="text-[var(--ink)]">Band</span> · Reasoning by{" "}
            <span className="text-[var(--ink)]">AI/ML API</span> +{" "}
            <span className="text-[var(--ink)]">Featherless AI</span>
          </span>
          <span>Band of Agents Hackathon · Track 3 — Regulated &amp; High-Stakes</span>
        </div>
      </div>
    </footer>
  );
}
