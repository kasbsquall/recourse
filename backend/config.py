"""Centralized settings loaded from the repo-root `.env`."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/config.py -> backend/ -> repo root
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/recourse"

    # Band — platform URLs (SDK defaults) + the user/account API key (Human API)
    band_rest_url: str = "https://app.band.ai"
    band_ws_url: str = "wss://app.band.ai/api/v1/socket/websocket"
    band_user_api_key: str = ""  # band_u_... — backend uses this to create rooms / read transcripts

    # Band agents (Agent API keys, band_a_...)
    band_blake_agent_id: str = ""
    band_blake_api_key: str = ""
    band_blake_handle: str = ""
    band_morgan_agent_id: str = ""
    band_morgan_api_key: str = ""
    band_morgan_handle: str = ""
    band_alex_agent_id: str = ""
    band_alex_api_key: str = ""
    band_alex_handle: str = ""
    band_sam_agent_id: str = ""
    band_sam_api_key: str = ""
    band_sam_handle: str = ""

    # Coordinator — the 5th agent. Intakes the claim, creates the room, adds the 4
    # adjudicators, and posts the case file mentioning @blake. It only acts proactively
    # (never needs to receive a mention), which sidesteps the "room creator isn't
    # auto-subscribed" limitation that blocks any debating agent from orchestrating.
    band_coordinator_agent_id: str = ""
    band_coordinator_api_key: str = ""
    band_coordinator_handle: str = ""

    # Quinn — the 6th agent (Special Investigations Unit). NOT a standing panelist: the
    # Coordinator dynamically RECRUITS Quinn into the room mid-debate (add_participant) ONLY
    # when fraud / misrepresentation / a material inconsistency is alleged — demonstrating
    # Band's dynamic agent discovery. Feature-flagged: if these are unset, the debate runs
    # exactly as before (the standing 5-agent panel), so it is safe to deploy unconfigured.
    band_quinn_agent_id: str = ""
    band_quinn_api_key: str = ""
    band_quinn_handle: str = ""

    # AI/ML API (Blake + Morgan)
    aimlapi_api_key: str = ""
    aimlapi_base_url: str = "https://api.aimlapi.com/v1"
    aimlapi_model: str = "gpt-4o"

    # Featherless (Alex)
    featherless_api_key: str = ""
    featherless_base_url: str = "https://api.featherless.ai/v1"
    featherless_model: str = "NousResearch/Hermes-2-Pro-Llama-3-8B"

    # App
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def band_agents(self) -> dict[str, dict]:
        """Registry of the 4 agents: slug -> identity + which LLM provider powers it.

        provider determines the partner prize wiring:
          - aimlapi:     Blake + Morgan (AI/ML API partner prize)
          - featherless: Alex (Featherless partner prize)
          - Sam runs on AI/ML API (strong reasoning for the final resolution).
        """
        return {
            "blake": {
                "name": "Blake", "role": "Claims Evaluator",
                "agent_id": self.band_blake_agent_id, "api_key": self.band_blake_api_key,
                "handle": self.band_blake_handle, "provider": "aimlapi",
            },
            "morgan": {
                "name": "Morgan", "role": "Policy Analyst",
                "agent_id": self.band_morgan_agent_id, "api_key": self.band_morgan_api_key,
                "handle": self.band_morgan_handle, "provider": "aimlapi",
            },
            "alex": {
                "name": "Alex", "role": "Devil's Advocate",
                "agent_id": self.band_alex_agent_id, "api_key": self.band_alex_api_key,
                "handle": self.band_alex_handle, "provider": "featherless",
            },
            "sam": {
                "name": "Sam", "role": "Resolution Notary",
                "agent_id": self.band_sam_agent_id, "api_key": self.band_sam_api_key,
                "handle": self.band_sam_handle, "provider": "aimlapi",
            },
        }

    @property
    def coordinator(self) -> dict:
        """The 5th agent: claim intake + room orchestration (not a debating agent)."""
        return {
            "name": "Coordinator", "role": "Claims Intake", "slug": "coordinator",
            "agent_id": self.band_coordinator_agent_id,
            "api_key": self.band_coordinator_api_key,
            "handle": self.band_coordinator_handle,
        }

    @property
    def quinn(self) -> dict:
        """The 6th agent (SIU). Dynamically recruited mid-debate when fraud is alleged."""
        return {
            "name": "Quinn", "role": "Special Investigations Unit", "slug": "quinn",
            "agent_id": self.band_quinn_agent_id,
            "api_key": self.band_quinn_api_key,
            "handle": self.band_quinn_handle,
            "provider": "aimlapi",
        }

    @property
    def quinn_enabled(self) -> bool:
        """True only when Quinn's Band identity is fully configured. When False, the debate
        runs as the standing 5-agent panel (no dynamic recruitment) — safe default."""
        return bool(
            self.band_quinn_agent_id
            and self.band_quinn_api_key
            and self.band_quinn_handle
        )

    @property
    def orchestrator(self) -> dict:
        """The identity that drives the room (creates it + posts the case file)."""
        return self.coordinator


settings = Settings()
