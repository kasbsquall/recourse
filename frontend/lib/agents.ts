/** Agent identities + dark-theme palette. Single source of truth for the UI. */
export type AgentSlug =
  | "coordinator"
  | "blake"
  | "morgan"
  | "alex"
  | "sam"
  | "human_officer";

export interface AgentMeta {
  name: string;
  role: string;
  tagline: string;
  /** Vivid hex used for avatar, accents, and the message left-border on dark surfaces. */
  hex: string;
  emoji: string;
  /** Generated character portrait (in /public/agents). Falls back to a color square if absent. */
  img?: string;
}

export const AGENTS: Record<AgentSlug, AgentMeta> = {
  coordinator: {
    name: "Coordinator",
    role: "Claims Intake",
    tagline: "Intake · Orchestration · Routing",
    hex: "#0e7490",
    emoji: "◆",
    img: "/agents/coordinator.png",
  },
  blake: {
    name: "Blake",
    role: "Claims Evaluator",
    tagline: "Analytical · Data-driven · Impartial",
    hex: "#2d5bff",
    emoji: "■",
    img: "/agents/blake.png",
  },
  morgan: {
    name: "Morgan",
    role: "Policy Analyst",
    tagline: "Meticulous · Quote-first · Precise",
    hex: "#7c3aed",
    emoji: "❝",
    img: "/agents/morgan.png",
  },
  alex: {
    name: "Alex",
    role: "Devil's Advocate",
    tagline: "Combative · Insured-first · Relentless",
    hex: "#dc2626",
    emoji: "▲",
    img: "/agents/alex.png",
  },
  sam: {
    name: "Sam",
    role: "Resolution Notary",
    tagline: "Calm · Definitive · Final word",
    hex: "#15803d",
    emoji: "§",
    img: "/agents/sam.png",
  },
  human_officer: {
    name: "Claims Officer",
    role: "Human Review",
    tagline: "Human · Authority · Final approval",
    hex: "#0e0e0e",
    emoji: "☆",
  },
};

const FALLBACK: AgentMeta = {
  name: "Agent",
  role: "",
  tagline: "",
  hex: "#9aa7c2",
  emoji: "•",
};

export function getAgent(slug: string): AgentMeta {
  return AGENTS[slug as AgentSlug] ?? { ...FALLBACK, name: slug };
}

/** The four adjudicators, in debate order. */
export const ADJUDICATORS: AgentSlug[] = ["blake", "morgan", "alex", "sam"];

/** Full cast for the roster strip: 4 adjudicators + the Coordinator (intake/orchestrator). */
export const ROSTER: AgentSlug[] = ["blake", "morgan", "alex", "sam", "coordinator"];

/** Pick ink or paper text for legibility on a given agent color. */
export function textOn(hex: string): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.6 ? "#0e0e0e" : "#ffffff";
}
