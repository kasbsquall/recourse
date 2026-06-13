import { getAgent, textOn } from "@/lib/agents";

export default function AgentAvatar({
  slug,
  size = 40,
  active = false,
}: {
  slug: string;
  size?: number;
  active?: boolean;
}) {
  const agent = getAgent(slug);
  const frame = {
    width: size,
    height: size,
    border: "2.5px solid var(--ink)",
    boxShadow: "var(--shadow-sm)",
  } as const;

  if (agent.img) {
    return (
      <div
        className={`shrink-0 overflow-hidden ${active ? "flash" : ""}`}
        style={{ ...frame, background: agent.hex }}
        title={`${agent.name} — ${agent.role}`}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={agent.img}
          alt={agent.name}
          className="h-full w-full"
          style={{ objectFit: "cover", objectPosition: "top center" }}
        />
      </div>
    );
  }

  return (
    <div
      className={`font-display flex shrink-0 items-center justify-center ${active ? "flash" : ""}`}
      style={{
        ...frame,
        fontSize: size * 0.46,
        lineHeight: 1,
        background: agent.hex,
        color: textOn(agent.hex),
      }}
      title={`${agent.name} — ${agent.role}`}
    >
      {agent.name.charAt(0)}
    </div>
  );
}
