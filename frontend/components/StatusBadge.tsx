import type { ClaimStatus } from "@/lib/types";

const STYLES: Record<
  ClaimStatus,
  { label: string; bg: string; fg: string; flash?: boolean }
> = {
  pending: { label: "Pending", bg: "#e9e6dd", fg: "#0e0e0e" },
  in_review: { label: "In Review", bg: "#2d5bff", fg: "#ffffff", flash: true },
  approved: { label: "Approved", bg: "#16a34a", fg: "#ffffff" },
  denied: { label: "Denied", bg: "#ff3b30", fg: "#ffffff" },
  partial: { label: "Partial", bg: "#f5d90a", fg: "#0e0e0e" },
};

export default function StatusBadge({ status }: { status: ClaimStatus }) {
  const s = STYLES[status] ?? STYLES.pending;
  return (
    <span
      className={`uppercase-mono inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-bold ${
        s.flash ? "flash" : ""
      }`}
      style={{
        background: s.bg,
        color: s.fg,
        border: "2px solid var(--ink)",
      }}
    >
      {s.flash && (
        <span className="h-1.5 w-1.5" style={{ background: s.fg }} />
      )}
      {s.label}
    </span>
  );
}
