"""Launch each Recourse agent in its OWN process (isolated event loop).

    python -m agents.run_agents            # blake, morgan, alex, sam
    python -m agents.run_agents alex sam   # only specific agents

Why separate processes (not asyncio.gather in one loop): the agents share nothing, and
running them in a single event loop lets one agent's blocking work (e.g. a synchronous
sentence-transformers embed, or heavy concurrent room polling) stall the loop and drop
another agent's reply mid-send. One process per agent = one event loop per agent = no
cross-agent contention. This also matches how they'd be deployed.

Leave this running, then start a debate (scripts/start_debate.py) in another terminal.
Ctrl+C stops all of them.
"""
import subprocess
import sys

from config import settings

_MODULES = {
    "blake": "agents.blake_claims_evaluator",
    "morgan": "agents.morgan_policy_analyst",
    "alex": "agents.alex_devils_advocate",
    "sam": "agents.sam_resolution_notary",
    "quinn": "agents.quinn_siu_investigator",  # SIU — dynamically recruited when fraud is alleged
}


def main(slugs: list[str]) -> None:
    procs: list[tuple[str, subprocess.Popen]] = []
    for slug in slugs:
        p = subprocess.Popen([sys.executable, "-u", "-m", _MODULES[slug]])
        procs.append((slug, p))
        print(f"[{slug}] spawned (pid {p.pid})")
    print(f"Running {len(procs)} agent process(es). Ctrl+C to stop all.")
    try:
        for _, p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("\nStopping agents ...")
        for _, p in procs:
            p.terminate()
        for _, p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    requested = [s.lower() for s in sys.argv[1:]]
    if not requested:
        # Default: the standing 4-agent panel, plus Quinn (SIU) only when it's configured.
        requested = ["blake", "morgan", "alex", "sam"]
        if settings.quinn_enabled:
            requested.append("quinn")
    unknown = [s for s in requested if s not in _MODULES]
    if unknown:
        sys.exit(f"Unknown agent(s): {unknown}. Choose from {list(_MODULES)}")
    main(requested)
