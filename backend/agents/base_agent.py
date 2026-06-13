"""Factory for Band remote agents.

Each Recourse agent is a long-running process that connects to Band over WebSocket,
wraps an LLM via the LangGraph adapter, and responds when @mentioned in a room.

Provider wiring (partner prizes):
  - aimlapi     -> Blake, Morgan, Sam  (AI/ML API, OpenAI-compatible)
  - featherless -> Alex                (Featherless AI, OpenAI-compatible)

Both providers expose an OpenAI-compatible API, so a single ChatOpenAI client with a
swapped base_url/key/model powers all four.
"""
from __future__ import annotations

import logging
import os
from typing import Any

if os.getenv("BAND_DEBUG"):
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    logging.getLogger("band").setLevel(logging.DEBUG)

if os.getenv("LC_DEBUG"):
    from langchain_core.globals import set_debug

    set_debug(True)

from band import Agent, AgentConfig
from band.adapters import LangGraphAdapter
from langchain_openai import ChatOpenAI

from config import settings


def build_llm(provider: str) -> ChatOpenAI:
    """Return an OpenAI-compatible chat model for the given provider.

    disable_streaming=True: the agent's reply is sent in one shot via band_send_message, so
    we don't need token streaming — and it avoids langchain_openai's per-chunk stream timeout,
    which Featherless free-tier models trip on cold starts (StreamChunkTimeoutError).
    """
    # max_tokens cap: replies are <250 words, and Featherless Hermes-8B has only an 8K
    # context window — an unbounded (default ~4096) output reservation overflows it once
    # the orchestrator passes accumulated debate context. 900 leaves ample room.
    if provider == "featherless":
        return ChatOpenAI(
            base_url=settings.featherless_base_url,
            api_key=settings.featherless_api_key,
            model=settings.featherless_model,
            temperature=0.4,
            timeout=120,
            max_retries=2,
            max_tokens=900,
            disable_streaming=True,
        )
    if provider == "aimlapi":
        return ChatOpenAI(
            base_url=settings.aimlapi_base_url,
            api_key=settings.aimlapi_api_key,
            model=settings.aimlapi_model,
            temperature=0.3,
            timeout=120,
            max_retries=2,
            max_tokens=900,
            disable_streaming=True,
        )
    raise ValueError(f"Unknown LLM provider: {provider!r}")


def create_band_agent(
    slug: str,
    system_prompt: str,
    tools: list[Any] | None = None,
) -> Agent:
    """Build (but do not start) a Band agent for the given slug.

    `slug` keys into settings.band_agents for the agent_id / api_key / provider.
    `system_prompt` becomes the agent's personality (LangGraph adapter custom section).
    `tools` are LangChain tools the agent may call (e.g. Morgan's clause search).
    """
    cfg = settings.band_agents.get(slug)
    if cfg is None:
        raise ValueError(f"Unknown agent slug: {slug!r}")
    if not cfg["agent_id"] or not cfg["api_key"]:
        raise RuntimeError(
            f"Missing Band credentials for {slug!r}. Check BAND_{slug.upper()}_AGENT_ID / _API_KEY in .env"
        )

    adapter = LangGraphAdapter(
        llm=build_llm(cfg["provider"]),
        custom_section=system_prompt,
        additional_tools=tools or [],
    )
    return Agent.create(
        adapter=adapter,
        agent_id=cfg["agent_id"],
        api_key=cfg["api_key"],
        ws_url=settings.band_ws_url,
        rest_url=settings.band_rest_url,
        # Don't re-sync every historical room on startup — only handle rooms the agent
        # is actively added to. Keeps the runtime focused on the live debate.
        config=AgentConfig(auto_subscribe_existing_rooms=False),
    )


async def run_agent(slug: str, system_prompt: str, tools: list[Any] | None = None) -> None:
    """Create and run an agent until interrupted (Ctrl+C). Used by each agent's __main__."""
    agent = create_band_agent(slug, system_prompt, tools)
    print(f"[{slug}] connecting to Band as {settings.band_agents[slug]['handle']} ...")
    await agent.run()
