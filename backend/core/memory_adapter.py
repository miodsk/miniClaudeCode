from __future__ import annotations

# pyright: reportAny=false, reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportOptionalCall=false, reportOptionalMemberAccess=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

import logging
import os

try:
    from mem0 import Memory as Mem0Client
except ImportError:  # pragma: no cover - optional dependency fallback
    try:
        from mem0 import MemoryClient as Mem0Client  # type: ignore[attr-defined]
    except ImportError:  # pragma: no cover - optional dependency fallback
        Mem0Client = None  # type: ignore[assignment]


LOGGER = logging.getLogger(__name__)
DEFAULT_USER_ID = os.getenv("BACKEND_DEFAULT_USER_ID", "default_user")


class MemoryAdapter:
    def __init__(self, default_user_id: str = DEFAULT_USER_ID) -> None:
        self._default_user_id: str = default_user_id
        self._client: object | None = None
        self._enabled: bool = False
        self._initialize_client()

    def _initialize_client(self) -> None:
        if os.getenv("MEM0_ENABLED") != "true":
            return

        if not os.getenv("DEEPSEEK_API_KEY"):
            LOGGER.warning("mem0 adapter disabled because DEEPSEEK_API_KEY is missing")
            return

        if Mem0Client is None:
            LOGGER.warning("mem0 adapter disabled because mem0 is unavailable")
            return

        try:
            self._client = self._create_client()
            self._enabled = self._client is not None
        except Exception as exc:  # pragma: no cover - exercised by tests via mocks
            LOGGER.warning("mem0 adapter disabled during initialization: %s", exc)
            self._client = None
            self._enabled = False

    def _create_client(self) -> object:
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or ""
        openai_api_key = os.getenv("OPENAI_API_KEY") or ""
        llm_config: dict[str, str] = {
            "model": os.getenv("MEM0_DEEPSEEK_MODEL", "deepseek-chat"),
            "api_key": deepseek_api_key,
        }
        embedder_config: dict[str, str] = {
            "model": os.getenv("MEM0_EMBEDDER_MODEL", "text-embedding-3-small"),
            "api_key": openai_api_key,
        }
        config: dict[str, object] = {
            "llm": {
                "provider": "deepseek",
                "config": llm_config,
            },
            "embedder": {
                "provider": "openai",
                "config": embedder_config,
            },
        }

        deepseek_base_url = os.getenv("DEEPSEEK_API_BASE")
        if deepseek_base_url:
            llm_config["deepseek_base_url"] = deepseek_base_url

        openai_base_url = os.getenv("OPENAI_API_BASE")
        if openai_base_url:
            embedder_config["base_url"] = openai_base_url

        if hasattr(Mem0Client, "from_config"):
            return Mem0Client.from_config(config)

        return Mem0Client()

    def _resolve_user_id(self, user_id: str | None) -> str:
        return user_id or self._default_user_id

    def is_enabled(self) -> bool:
        return self._enabled

    def search_relevant_memories(
        self,
        user_id: str | None = None,
        query: str = "",
        limit: int = 5,
    ) -> list[str]:
        if not self._enabled or not query.strip() or self._client is None:
            return []

        try:
            response = self._client.search(
                query.strip(),
                user_id=self._resolve_user_id(user_id),
                limit=limit,
            )
        except Exception as exc:
            LOGGER.warning("mem0 search failed: %s", exc)
            return []

        results = (
            response.get("results", response) if isinstance(response, dict) else []
        )
        if not isinstance(results, list):
            return []

        memories: list[str] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            fact = item.get("memory") or item.get("fact") or item.get("text")
            if isinstance(fact, str) and fact.strip():
                memories.append(fact.strip())

        return memories

    def record_turn(
        self,
        user_id: str | None = None,
        user_message: str = "",
        assistant_text: str = "",
    ) -> None:
        if not self._enabled or self._client is None:
            return

        condensed_summary = self._build_condensed_summary(user_message, assistant_text)
        if not condensed_summary:
            return

        try:
            self._client.add(
                [
                    {
                        "role": "user",
                        "content": condensed_summary,
                    }
                ],
                user_id=self._resolve_user_id(user_id),
                metadata={"source": "lead_turn", "condensed": True},
            )
        except Exception as exc:
            LOGGER.warning("mem0 record_turn failed: %s", exc)

    def _build_condensed_summary(self, user_message: str, assistant_text: str) -> str:
        user_summary = " ".join(user_message.strip().split())[:400]
        assistant_summary = " ".join(assistant_text.strip().split())[:200]
        if not user_summary and not assistant_summary:
            return ""

        lines = ["Condensed durable memory summary from the latest turn."]
        if user_summary:
            lines.append(f"User facts/preferences to remember: {user_summary}")
        if assistant_summary:
            lines.append(f"Assistant confirmation/context: {assistant_summary}")
        return "\n".join(lines)


__all__ = ["MemoryAdapter"]
