from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from graph.message_compaction import auto_compact, estimate_tokens, micro_compact


def prepare_main_messages(
    messages: list[Any],
    llm: Any,
    system_prompt: str,
    threshold: int,
    transcript_dir: Path,
    keep_recent: int,
    bg_manager: Any,
) -> None:
    micro_compact(messages, keep_recent=keep_recent)

    if estimate_tokens(messages) > threshold:
        print("[auto_compact] token 超阈值，开始压缩对话...")
        messages[:] = auto_compact(
            messages,
            llm=llm,
            system_prompt=system_prompt,
            transcript_dir=transcript_dir,
        )

    notifs = bg_manager.drain_notifications()
    if notifs:
        notif_text = "\n".join(
            f"[bg:{n['task_id']}] {n['status']} - {n['command']}\n{n['preview']}"
            for n in notifs
        )
        messages.append(
            HumanMessage(
                content=f"<background-results>\n{notif_text}\n</background-results>"
            )
        )
