import Link from "next/link";

export default function SiteHeader({ subtitle }: { subtitle?: string }) {
  return (
    <header className="sticky top-0 z-20 border-b-[3px] border-[var(--ink)] bg-[var(--bg)]">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link href="/" className="flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/recourse-logo-dark.png" alt="RECOURSE" className="h-6 w-auto" />
          <span className="uppercase-mono hidden text-[10px] font-bold text-[var(--ink)] sm:block">
            {subtitle ?? "Adversarial Claims Adjudication"}
          </span>
        </Link>
        <div className="uppercase-mono flex items-center gap-2 text-[10px] font-bold text-[var(--ink)]">
          <span className="h-2 w-2 bg-[#16a34a]" />
          Crestview Mutual / Desk
        </div>
      </div>
    </header>
  );
}
