from __future__ import annotations

# pyright: reportAny=false, reportMissingImports=false, reportUnannotatedClassAttribute=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnusedCallResult=false

import unittest
from unittest.mock import MagicMock, patch

from backend.core.memory_adapter import MemoryAdapter


class FakeMem0Client:
    created_with: dict[str, object] | None = None
    instance = MagicMock()

    @classmethod
    def from_config(cls, config: dict[str, object]) -> MagicMock:
        cls.created_with = config
        cls.instance = MagicMock()
        return cls.instance


class TestMemoryAdapter(unittest.TestCase):
    def test_adapter_stays_disabled_without_required_env(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            adapter = MemoryAdapter()

        self.assertFalse(adapter.is_enabled())
        self.assertEqual(adapter.search_relevant_memories(None, "user profile"), [])
        adapter.record_turn(None, "I like tea", "Got it")

    def test_adapter_uses_mem0_when_enabled(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "MEM0_ENABLED": "true",
                "DEEPSEEK_API_KEY": "deepseek-key",
                "OPENAI_API_KEY": "openai-key",
            },
            clear=False,
        ):
            with patch("backend.core.memory_adapter.Mem0Client", FakeMem0Client):
                adapter = MemoryAdapter()

        FakeMem0Client.instance.search.return_value = {
            "results": [{"memory": "User likes tea"}, {"memory": "Prefers calm tone"}]
        }

        self.assertTrue(adapter.is_enabled())
        self.assertEqual(
            adapter.search_relevant_memories(None, "What do you know?", limit=2),
            ["User likes tea", "Prefers calm tone"],
        )

        adapter.record_turn(None, "I like tea and quiet spaces", "Okay, noted.")

        self.assertIsNotNone(FakeMem0Client.created_with)
        FakeMem0Client.instance.search.assert_called_once_with(
            "What do you know?", user_id="default_user", limit=2
        )
        FakeMem0Client.instance.add.assert_called_once()
        add_args, add_kwargs = FakeMem0Client.instance.add.call_args
        self.assertEqual(add_kwargs["user_id"], "default_user")
        self.assertTrue(add_kwargs["metadata"]["condensed"])
        self.assertIn("Condensed durable memory summary", add_args[0][0]["content"])
        self.assertIn("I like tea and quiet spaces", add_args[0][0]["content"])

    def test_runtime_failures_degrade_safely(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "MEM0_ENABLED": "true",
                "DEEPSEEK_API_KEY": "deepseek-key",
                "OPENAI_API_KEY": "openai-key",
            },
            clear=False,
        ):
            with patch("backend.core.memory_adapter.Mem0Client", FakeMem0Client):
                adapter = MemoryAdapter()

        FakeMem0Client.instance.search.side_effect = RuntimeError("search boom")
        FakeMem0Client.instance.add.side_effect = RuntimeError("add boom")

        self.assertEqual(adapter.search_relevant_memories("user-1", "hello"), [])
        adapter.record_turn("user-1", "remember this", "done")


if __name__ == "__main__":
    unittest.main()
