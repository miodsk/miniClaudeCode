from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
import json
from graph.tools.load_skill import SKILL_LOADER
from graph.tool_policy import get_static_tools_for_agent
import os
from pathlib import Path
from graph.tools.background_task import BG_MANAGER
from graph.execute_tool_calls import execute_tool_calls
from graph.prepare_main_messages import prepare_main_messages
from graph.message_compaction import auto_compact
from team import TeamManager

load_dotenv()

deepseek = ChatDeepSeek(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0.2,
)

SYSTEM_PROMPT = f"""你是团队负责人 lead，负责理解用户需求、拆解任务、必要时委派给 researcher 或 coder，并基于队友结果给出最终答复。

工作规则：
1. 你直接面对用户，最终答复由你给出。
2. 做多步任务时，先用 task_create、task_update、task_list、task_get 管理计划和状态。
3. 当任务需要调研、阅读文件、查找信息时，优先考虑委派给 researcher。
4. 当任务需要改文件、落地实现或执行后台命令时，优先考虑委派给 coder。
5. 委派时要写清楚目标、范围和期望输出。
6. 只有在收到 researcher 或 coder 的回报后，才能把其结果当作已完成事实使用。
7. 如果任务不需要委派，你也可以自己直接完成。
8. 遇到不熟悉的领域时，先用 load_skill 工具加载相关技能知识。
9. 遇到耗时命令时，优先使用 background_run；需要时用 background_check 查看状态。
10. 当需要委派给 researcher 或 coder 时，使用 send_message 发送清晰的子任务。
11. 如需让某位队友优雅停止工作，使用 request_shutdown 发起请求，等待其明确响应。
12. 如果 coder 提交了 merge_request，审查后使用 respond_merge_request 给出批准或拒绝。
13. 如需查看当前未读团队邮件摘要，可使用 check_mail。

可用技能:
{SKILL_LOADER.get_descriptions()}"""

KEEP_RECENT = 3  # 保留最近的 tool_result 数量
THRESHOLD = 50000  # token 阈值
TRANSCRIPT_DIR = Path(".transcripts")


def loop():
    team = TeamManager(lead_system_prompt=SYSTEM_PROMPT)
    messages = team.agents["lead"].messages
    lead_tools = get_static_tools_for_agent("lead") + team.get_agent_tools("lead")
    lead_tools_map = {tool.name: tool for tool in lead_tools}
    lead_llm = deepseek.bind_tools(lead_tools)
    rounds_since_todo = 0

    while True:
        query = input("请输入你的问题：")
        if query.lower() in ("q", "exit", "退出"):
            break
        team.submit_user_task(query)

        while True:
            team.deliver_mail("lead")

            prepare_main_messages(
                messages=messages,
                llm=deepseek,
                system_prompt=SYSTEM_PROMPT,
                threshold=THRESHOLD,
                transcript_dir=TRANSCRIPT_DIR,
                keep_recent=KEEP_RECENT,
                bg_manager=BG_MANAGER,
            )

            response = lead_llm.invoke(input=messages)

            print(f"AI 回复: {response.content}\n工具调用: {response.tool_calls}")
            messages.append(response)

            if not response.tool_calls:
                break

            state = execute_tool_calls(response, messages, lead_tools_map)
            used_todo = state["used_todo"]
            need_compact = state["need_compact"]

            team_responses = team.team_cycle(deepseek)
            if team_responses:
                lines = []
                for agent_name, agent_response in team_responses.items():
                    content = (
                        agent_response.content
                        if getattr(agent_response, "content", None)
                        else "(无内容)"
                    )
                    lines.append(f"[{agent_name}] {content}")
                messages.append(
                    HumanMessage(
                        content="<team_cycle>\n"
                        + "\n\n".join(lines)
                        + "\n</team_cycle>"
                    )
                )

            # Layer 3: LLM 主动调用 compact 工具时触发压缩
            if need_compact:
                print("[manual compact] LLM 请求压缩对话...")
                messages[:] = auto_compact(
                    messages,
                    llm=deepseek,
                    system_prompt=SYSTEM_PROMPT,
                    transcript_dir=TRANSCRIPT_DIR,
                )

            # nag reminder: 3轮没更新todo就提醒
            if used_todo:
                rounds_since_todo = 0
            else:
                rounds_since_todo += 1

            if rounds_since_todo >= 3:
                print("[提醒] 请更新你的 todo 列表")
                messages.append(
                    HumanMessage(content="<reminder>请更新你的 todo 列表</reminder>")
                )
                rounds_since_todo = 0

        # 保存对话历史
        readable_history = [m.to_json() for m in messages]
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(readable_history, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    loop()
