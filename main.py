import json
from pathlib import Path
from typing import cast

from dotenv import load_dotenv

from backend.core.chat_engine import execute_lead_turn
from backend.core.session_store import SessionStore

_ = load_dotenv()

CLI_SESSION_ID = "cli-debug"
CLI_SESSION_FILE = Path(".sessions/cli-debug.json")
OUTPUT_FILE = Path("output.json")


def loop():
    cli_store = SessionStore(session_file=CLI_SESSION_FILE)

    while True:
        query = input("请输入你的问题：")
        if query.lower() in ("q", "exit", "退出"):
            break

        session = cli_store.load()
        session_messages = cast(list[object], session.get("messages", []))
        result = execute_lead_turn(
            user_message=query,
            session_id=CLI_SESSION_ID,
            session_messages=session_messages,
        )
        print(f"AI 回复: {result.assistant_text}\n工具调用: {result.tool_calls}")

        readable_history = [message.to_json() for message in result.messages]
        cli_store.save(
            {
                "session_id": CLI_SESSION_ID,
                "messages": readable_history,
                "metadata": {},
            }
        )
        _ = OUTPUT_FILE.write_text(
            json.dumps(readable_history, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )


if __name__ == "__main__":
    loop()
