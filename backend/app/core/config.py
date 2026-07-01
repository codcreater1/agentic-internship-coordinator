"""Runtime configuration — every tunable lives here, sourced from environment.

Override any value via the PDFSIGN_ prefix:
    PDFSIGN_MAX_PDF_BYTES=10485760 uvicorn app.main:app

Or via a .env file (gitignored) for local development.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Per-process fallback secret, used to sign download tokens when no explicit
# api_secret_key is configured. Regenerated each restart — fine because tokens
# are short-lived (default 10 min TTL).
_FALLBACK_SECRET = secrets.token_hex(32)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PDFSIGN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Storage
    # ------------------------------------------------------------------ #
    storage_root: Path = Field(
        default=Path(__file__).resolve().parent.parent.parent / "tmp",
        description="Root directory for per-task working directories.",
    )

    db_path: Path = Field(
        default=Path(__file__).resolve().parent.parent.parent / "applications.db",
        description="SQLite file storing processed applications.",
    )

    # ------------------------------------------------------------------ #
    # Upload limits
    # ------------------------------------------------------------------ #
    max_pdf_bytes: int = Field(
        default=15 * 1024 * 1024,  # 15 MB
        description="Maximum accepted PDF upload size in bytes.",
    )

    max_image_bytes: int = Field(
        default=5 * 1024 * 1024,  # 5 MB
        description="Maximum accepted signature image size in bytes.",
    )

    read_chunk_bytes: int = Field(
        default=256 * 1024,  # 256 KB
        description="Chunk size for streaming uploads to disk.",
    )

    # ------------------------------------------------------------------ #
    # Task lifecycle
    # ------------------------------------------------------------------ #
    task_ttl_seconds: int = Field(
        default=3600,  # 1 hour
        description="Age in seconds after which orphaned task dirs are purged at startup.",
    )

    # ------------------------------------------------------------------ #
    # API surface
    # ------------------------------------------------------------------ #
    api_prefix: str = Field(default="/api/v1")

    cors_origins: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        description="Allowed browser origins. Override via PDFSIGN_CORS_ORIGINS.",
    )

    app_title: str = "Agentic Internship Coordinator"
    app_version: str = "2.0.0"

    # ------------------------------------------------------------------ #
    # AI / LLM (OpenAI-compatible — defaults to Groq's free API)
    # ------------------------------------------------------------------ #
    llm_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/",
        description="OpenAI-compatible API base URL (Google Gemini by default).",
    )

    llm_model: str = Field(
        default="gemini-2.0-flash",
        description="Model used for CV evaluation and email drafting.",
    )

    report_language: str = Field(
        default="English",
        description="Language the model writes reports and candidate emails in.",
    )

    # ------------------------------------------------------------------ #
    # Security
    # ------------------------------------------------------------------ #
    api_secret_key: str = Field(
        default="",
        description="If non-empty, the /applications/from-n8n endpoint requires "
                    "'Authorization: Bearer <key>'. Also signs download tokens.",
    )

    @property
    def signing_secret(self) -> str:
        """Secret used to sign download tokens — the configured api_secret_key,
        or a per-process random fallback so tokens are never signed with ''."""
        return self.api_secret_key or _FALLBACK_SECRET

    # ------------------------------------------------------------------ #
    # Validators
    # ------------------------------------------------------------------ #
    @field_validator("storage_root", "db_path", mode="before")
    @classmethod
    def _resolve_path(cls, v: str | Path) -> Path:
        return Path(v).resolve()

    @field_validator(
        "max_pdf_bytes",
        "max_image_bytes",
        "read_chunk_bytes",
        "task_ttl_seconds",
        mode="before",
    )
    @classmethod
    def _positive_int(cls, v) -> int:
        try:
            value = int(float(v))
        except (TypeError, ValueError):
            raise ValueError("must be a positive integer")

        if value <= 0:
            raise ValueError("must be a positive integer")

        return value


# Module-level singleton — import this everywhere.
settings = Settings()