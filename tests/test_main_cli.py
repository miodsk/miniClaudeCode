# pyright: reportAny=false, reportExplicitAny=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnannotatedClassAttribute=false

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch


class _SerializableMessage:
    def __init__(self, payload: dict[str, Any]):
        self.payload: dict[str, Any] = payload

    def to_json(self):
        return self.payload


class MainCliLoopTests(unittest.TestCase):
    def test_loop_uses_cli_debug_session_store_and_backend_core(self):
        output_exists = False
        with TemporaryDirectory() as tmpdir:
            cli_store = MagicMock()
            cli_store.load.return_value = {
                "session_id": "cli-debug",
                "messages": [],
                "metadata": {},
            }
            turn_result = SimpleNamespace(
                assistant_text="已处理",
                tool_calls=[],
                team_responses={},
                needs_compact=False,
                messages=[_SerializableMessage({"type": "ai", "content": "已处理"})],
            )

            with (
                patch("main.SessionStore", return_value=cli_store) as mock_store_cls,
                patch(
                    "main.execute_lead_turn", return_value=turn_result
                ) as mock_execute,
                patch("builtins.input", side_effect=["你好", "q"]),
                patch("builtins.print"),
            ):
                import main

                previous_cwd = Path.cwd()
                try:
                    os.chdir(tmpdir)
                    main.loop()
                    output_exists = (Path(tmpdir) / "output.json").exists()
                finally:
                    os.chdir(previous_cwd)

        mock_store_cls.assert_called_once_with(
            session_file=Path(".sessions/cli-debug.json")
        )
        cli_store.load.assert_called_once_with()
        mock_execute.assert_called_once_with(
            user_message="你好",
            session_id="cli-debug",
            session_messages=[],
        )
        cli_store.save.assert_called_once_with(
            {
                "session_id": "cli-debug",
                "messages": [{"type": "ai", "content": "已处理"}],
                "metadata": {},
            }
        )
        self.assertTrue(output_exists)


if __name__ == "__main__":
    _ = unittest.main()
