import os
import subprocess
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AnyMessage, ToolMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from graph.tool_policy import get_static_tools_for_agent

load_dotenv()
TARGET_DIR = os.getenv("TARGET_DIR")


def get_project_root(start_path: Path) -> Path:
    """获取项目根目录（包含 .git 文件夹或特定标志文件的位置）。"""
    current = start_path.resolve()
    if current.is_file():
        current = current.parent

    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
        if (candidate / "pyproject.toml").exists():
            return candidate
        if (candidate / "setup.py").exists():
            return candidate
        if (candidate / "requirements.txt").exists():
            return candidate

    return current


HARNESS_ROOT = get_project_root(Path(__file__))
TARGET_ROOT = Path(TARGET_DIR).resolve() if TARGET_DIR else HARNESS_ROOT
WORKTREE_ROOT = TARGET_ROOT.parent / f"{TARGET_ROOT.name}-worktrees"


class Agent(BaseModel):
    role: str
    messages: list[AnyMessage]


class Mail(BaseModel):
    sender: str
    recipient: str
    content: str
    message_type: str = "normal"
    metadata: dict[str, Any] = Field(default_factory=dict)


class TeamManager:
    def __init__(
        self,
        lead_system_prompt: str | None = None,
        researcher_system_prompt: str | None = None,
        coder_system_prompt: str | None = None,
    ) -> None:
        default_lead_prompt = (
            "你是团队负责人 lead。你的职责是理解用户需求、拆解任务、"
            "决定是否需要委派给队友，并基于队友回报给出最终结论。\n\n"
            "你的工作规则：\n"
            "1. 你直接面对用户，最终答复应由你给出。\n"
            "2. 当任务需要额外调研、阅读文件、查找信息时，优先把明确的子任务发给 researcher。\n"
            "3. 当任务需要实际改文件、执行后台命令或落地实现时，优先把明确的子任务发给 coder。\n"
            "4. 给 researcher 或 coder 发消息时，要写清楚目标、范围、期望输出。\n"
            "5. 当你收到队友回报后，先整合结果，再决定是继续委派还是直接回答。\n"
            "6. 不要假装 researcher 或 coder 已经完成未做的工作；只有在收到回报后才能引用其结果。\n"
            "7. 如果 researcher 提交了 plan_request，你要审查计划并使用 respond_plan_request 给出批准或拒绝。\n"
            "8. 如需让某位队友停止工作，使用 request_shutdown 发起优雅停止请求，而不是默认其会立刻退出。\n"
            "9. 如果某位已停止的队友需要重新投入工作，使用 reactivate_agent 恢复其 active 状态。\n"
            "10. 对高风险、大改动、影响面大的方案，要先审批再允许执行。\n"
            "11. 如果不需要委派，你也可以直接继续处理当前任务。"
        )
        default_researcher_prompt = (
            "你是研究员 researcher。你的职责是接收 lead 委派的子任务，"
            "阅读文件、查找信息、总结发现，并把结果回报给 lead。\n\n"
            "你的工作规则：\n"
            "1. 你不直接面向用户，你的主要沟通对象是 lead。\n"
            "2. 收到任务后，先聚焦完成 lead 指定的调研或总结，不要擅自扩展太远。\n"
            "3. 完成后使用 send_message 把结果发回给 lead。\n"
            "4. 回报内容应尽量简洁清晰，包含：做了什么、发现了什么、还存在什么不确定点。\n"
            "5. 如果计划涉及高风险、大改动、重构或你认为需要审批的内容，先使用 submit_plan_request 向 lead 提交计划，再等待审批结果。\n"
            "6. 收到 shutdown_request 时，应在收尾后使用 respond_shutdown 明确批准或拒绝。\n"
            "7. 在计划未获批准前，不要直接执行高风险方案。\n"
            "8. 如果任务描述不清，可以先基于现有信息做最合理的调研，再把假设说明清楚。\n"
            "9. 你可以使用 check_mail 查看当前未读邮件摘要，但真正工作前会由系统把邮件送入上下文。"
        )
        default_coder_prompt = (
            "你是执行者 coder。你的职责是接收 lead 委派的实现型子任务，"
            "阅读相关文件、修改代码、必要时运行后台命令，并把结果回报给 lead。\n\n"
            "你的工作规则：\n"
            "1. 你不直接面向用户，你的主要沟通对象是 lead。\n"
            "2. 收到任务后，先理解范围，再使用可用工具完成实现，不要擅自扩展需求。\n"
            "3. 如需查看全局任务进度，可使用 task_list 和 task_get，但不要自行创建或更新任务。\n"
            "4. 需要耗时命令时优先使用 background_run，并在必要时使用 background_check。\n"
            "5. 收到 shutdown_request 时，应在收尾后使用 respond_shutdown 明确批准或拒绝。\n"
            "6. 完成后使用 send_message 把结果、改动内容和未解决问题回报给 lead。\n"
            "7. 如果任务描述不清，先基于现有信息做最合理的实现，再把假设说明清楚。\n"
            "8. 你可以使用 check_mail 查看当前未读邮件摘要，但真正工作前会由系统把邮件送入上下文。"
        )
        self.agent_workspaces = {
            "lead": str(TARGET_ROOT),
            "researcher": str(WORKTREE_ROOT / "researcher"),
            "coder": str(WORKTREE_ROOT / "coder"),
        }
        self.agents: dict[str, Agent] = {
            "lead": Agent(
                role="lead",
                messages=[
                    SystemMessage(content=lead_system_prompt or default_lead_prompt)
                ],
            ),
            "researcher": Agent(
                role="researcher",
                messages=[
                    SystemMessage(
                        content=researcher_system_prompt or default_researcher_prompt
                    )
                ],
            ),
            "coder": Agent(
                role="coder",
                messages=[
                    SystemMessage(content=coder_system_prompt or default_coder_prompt)
                ],
            ),
        }
        self.mailboxes: dict[str, list[Mail]] = {
            "lead": [],
            "researcher": [],
            "coder": [],
        }
        self.agent_status: dict[str, str] = {
            "lead": "active",
            "researcher": "active",
            "coder": "active",
        }
        self.plan_requests: dict[str, dict[str, Any]] = {}
        self.shutdown_requests: dict[str, dict[str, Any]] = {}

    def send_message(self, sender: str, recipient: str, content: str) -> str:
        if recipient not in self.mailboxes:
            return f"Agent {recipient} 不存在"
        mail = Mail(sender=sender, recipient=recipient, content=content)
        self.mailboxes[recipient].append(mail)
        return f"已发送给 {recipient}"

    def _drain_mailbox(self, agent_name: str) -> list[Mail]:
        if agent_name not in self.mailboxes:
            return []
        mails = self.mailboxes[agent_name][:]
        self.mailboxes[agent_name].clear()
        return mails

    def _format_mails(self, mails: list[Mail]) -> str:
        if not mails:
            return "当前没有未读邮件"

        formatted_mails = []
        for mail in mails:
            parts = [f"[from:{mail.sender}]", f"[type:{mail.message_type}]"]

            request_id = mail.metadata.get("request_id")
            if request_id:
                parts.append(f"[request_id:{request_id}]")

            approve = mail.metadata.get("approve")
            if approve is not None:
                parts.append(f"[approve:{approve}]")

            parts.append(mail.content)
            formatted_mails.append("\n".join(parts))

        return "\n\n".join(formatted_mails)

    def deliver_mail(self, agent_name: str) -> None:
        mails = self._drain_mailbox(agent_name)
        if not mails:
            return
        mail_text = self._format_mails(mails)
        self.agents[agent_name].messages.append(
            HumanMessage(content=f"<mailbox>\n{mail_text}\n</mailbox>")
        )

    def _peek_mailbox(self, agent_name: str) -> str:
        mails = self.mailboxes.get(agent_name, [])
        return self._format_mails(mails)

    def get_agent_tools(self, agent_name: str) -> list[Any]:
        @tool
        def send_message(recipient: str, content: str) -> str:
            """给团队中的另一位 agent 发送消息。"""
            return self.send_message(agent_name, recipient, content)

        @tool
        def check_mail() -> str:
            """查看当前 agent 的未读邮件摘要。"""
            return self._peek_mailbox(agent_name)

        agent_tools: list[Any] = [send_message, check_mail]

        if agent_name != "lead":

            @tool
            def respond_shutdown(
                request_id: str, approve: bool, feedback: str = ""
            ) -> str:
                """响应 lead 发起的优雅停止请求。"""
                return self.respond_shutdown(agent_name, request_id, approve, feedback)

            agent_tools.append(respond_shutdown)

        if agent_name == "researcher":

            @tool
            def submit_plan_request(plan: str) -> str:
                """向 lead 提交计划审批请求。"""
                return self.submit_plan_request(agent_name, "lead", plan)

            agent_tools.append(submit_plan_request)

        if agent_name == "lead":

            @tool
            def request_shutdown(teammate: str, reason: str = "") -> str:
                """向某位队友发起优雅停止请求。"""
                return self.request_shutdown(teammate, reason)

            @tool
            def reactivate_agent(teammate: str, reason: str = "") -> str:
                """恢复一位已停止队友的工作状态。"""
                return self.reactivate_agent(teammate, reason)

            @tool
            def respond_plan_request(
                request_id: str, approve: bool, feedback: str = ""
            ) -> str:
                """审批某个计划请求，可批准或拒绝。"""
                return self.respond_plan_request(request_id, approve, feedback)

            agent_tools.append(request_shutdown)
            agent_tools.append(reactivate_agent)
            agent_tools.append(respond_plan_request)

        return agent_tools

    def submit_plan_request(self, sender: str, recipient: str, plan: str) -> str:
        request_id = str(uuid.uuid4())[:8]
        self.plan_requests[request_id] = {
            "from": sender,
            "to": recipient,
            "plan": plan,
            "status": "pending",
        }
        mail = Mail(
            sender=sender,
            recipient=recipient,
            content=plan,
            message_type="plan_request",
            metadata={"request_id": request_id},
        )
        self.mailboxes[recipient].append(mail)
        return f"计划审批请求 {request_id} 已发送给 {recipient}"

    def respond_plan_request(
        self, request_id: str, approve: bool, feedback: str = ""
    ) -> str:
        req = self.plan_requests.get(request_id)
        if not req:
            return f"计划请求 {request_id} 不存在"

        req["status"] = "approved" if approve else "rejected"
        response_mail = Mail(
            sender=req["to"],
            recipient=req["from"],
            content=feedback,
            message_type="plan_response",
            metadata={
                "request_id": request_id,
                "approve": approve,
            },
        )
        self.mailboxes[req["from"]].append(response_mail)

        action_text = "批准" if approve else "拒绝"
        return f"计划请求 {request_id} 已{action_text}"

    def request_shutdown(self, teammate: str, reason: str = "") -> str:
        if teammate not in self.mailboxes or teammate == "lead":
            return f"无法向 {teammate} 发起停止请求"

        request_id = str(uuid.uuid4())[:8]
        self.shutdown_requests[request_id] = {
            "from": "lead",
            "to": teammate,
            "reason": reason,
            "status": "pending",
        }
        mail = Mail(
            sender="lead",
            recipient=teammate,
            content=reason or "请优雅退出当前工作。",
            message_type="shutdown_request",
            metadata={"request_id": request_id},
        )
        self.mailboxes[teammate].append(mail)
        return f"停止请求 {request_id} 已发送给 {teammate}"

    def respond_shutdown(
        self, sender: str, request_id: str, approve: bool, feedback: str = ""
    ) -> str:
        req = self.shutdown_requests.get(request_id)
        if not req:
            return f"停止请求 {request_id} 不存在"
        if req["to"] != sender:
            return f"停止请求 {request_id} 不属于 {sender}"

        req["status"] = "approved" if approve else "rejected"
        if approve:
            self.agent_status[sender] = "stopped"

        response_mail = Mail(
            sender=sender,
            recipient="lead",
            content=feedback,
            message_type="shutdown_response",
            metadata={"request_id": request_id, "approve": approve},
        )
        self.mailboxes["lead"].append(response_mail)

        action_text = "批准" if approve else "拒绝"
        return f"停止请求 {request_id} 已{action_text}"

    def reactivate_agent(self, teammate: str, reason: str = "") -> str:
        if teammate not in self.agent_status or teammate == "lead":
            return f"无法恢复 {teammate}"

        self.agent_status[teammate] = "active"
        if reason:
            self.mailboxes[teammate].append(
                Mail(
                    sender="lead",
                    recipient=teammate,
                    content=reason,
                    message_type="reactivate_notice",
                )
            )
        return f"队友 {teammate} 已恢复为 active"

    def list_worktrees(self) -> str:
        result = subprocess.run(
            "git worktree list --porcelain",
            capture_output=True,
            text=True,
            cwd=TARGET_ROOT,
        )
        if result.returncode == 0:
            return result.stdout
        else:
            return result.stderr

    def ensure_agent_workspace(self, agent_name: str) -> None:
        if agent_name == "lead":
            self.agent_workspaces[agent_name] = str(TARGET_ROOT)
            return

        workspace_path = Path(self.agent_workspaces[agent_name])
        if workspace_path.exists():
            self.agent_workspaces[agent_name] = str(workspace_path)
            return

        WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)
        branch_name = f"team-{agent_name}"
        result = subprocess.run(
            f'git worktree add "{workspace_path}" -b {branch_name}',
            capture_output=True,
            text=True,
            cwd=TARGET_ROOT,
        )
        if result.returncode == 0:
            self.agent_workspaces[agent_name] = str(workspace_path)
        else:
            print(f"[workspace] 创建失败: {result.stderr.strip()}")

    def run_agent_once(self, agent_name: str, llm: Any) -> AnyMessage:
        self.ensure_agent_workspace(agent_name)
        workspace = self.agent_workspaces.get(agent_name)
        if workspace:
            self.agents[agent_name].messages.append(
                HumanMessage(
                    content=(
                        f"<workspace>\n"
                        f"你的工作目录是 {workspace}。\n"
                        f"只在该目录下读写文件，不要修改主仓库内容。\n"
                        f"</workspace>"
                    )
                )
            )

        self.deliver_mail(agent_name)
        agent = self.agents[agent_name]
        static_tools = get_static_tools_for_agent(agent_name)
        agent_tools = static_tools + self.get_agent_tools(agent_name)
        tools_map = {tool_obj.name: tool_obj for tool_obj in agent_tools}
        agent_llm = llm.bind_tools(agent_tools)

        while True:
            response = agent_llm.invoke(agent.messages)
            agent.messages.append(response)

            if not getattr(response, "tool_calls", None):
                return response

            for tool_call in response.tool_calls:
                selected_tool = tools_map[tool_call["name"]]
                result = selected_tool.invoke(tool_call["args"])
                agent.messages.append(
                    ToolMessage(tool_call_id=tool_call["id"], content=str(result))
                )

    def team_cycle(self, llm: Any) -> dict[str, AnyMessage]:
        responses: dict[str, AnyMessage] = {}

        for agent_name in self.agents:
            if agent_name == "lead":
                continue
            if self.agent_status.get(agent_name) != "active":
                continue
            if self.mailboxes.get(agent_name):
                responses[agent_name] = self.run_agent_once(agent_name, llm)

        return responses

    def submit_user_task(self, content: str) -> None:
        self.agents["lead"].messages.append(HumanMessage(content=content))
