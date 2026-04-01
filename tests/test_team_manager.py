import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from team import TeamManager
from graph.tool_policy import get_static_tools_for_agent


class TeamManagerCoderTests(unittest.TestCase):
    def test_team_manager_registers_coder_agent_and_mailbox(self):
        team = TeamManager()

        self.assertIn("coder", team.agents)
        self.assertIn("coder", team.mailboxes)
        self.assertEqual(team.agents["coder"].role, "coder")

    def test_coder_gets_basic_dynamic_team_tools(self):
        team = TeamManager()

        tool_names = [tool.name for tool in team.get_agent_tools("coder")]

        self.assertIn("send_message", tool_names)
        self.assertIn("check_mail", tool_names)
        self.assertNotIn("respond_plan_request", tool_names)

    def test_lead_can_request_shutdown_for_teammate(self):
        team = TeamManager()

        result = team.request_shutdown("coder", "任务已结束")

        self.assertIn("已发送", result)
        self.assertEqual(len(team.shutdown_requests), 1)
        request = next(iter(team.shutdown_requests.values()))
        self.assertEqual(request["to"], "coder")
        self.assertEqual(request["status"], "pending")
        self.assertEqual(team.mailboxes["coder"][0].message_type, "shutdown_request")

    def test_teammate_can_approve_shutdown_and_be_stopped(self):
        team = TeamManager()
        team.request_shutdown("coder", "任务已结束")
        request_id = next(iter(team.shutdown_requests.keys()))

        result = team.respond_shutdown("coder", request_id, True, "已收尾完成")

        self.assertIn("已批准", result)
        self.assertEqual(team.shutdown_requests[request_id]["status"], "approved")
        self.assertEqual(team.agent_status["coder"], "stopped")
        self.assertEqual(team.mailboxes["lead"][-1].message_type, "shutdown_response")

    def test_get_agent_tools_exposes_shutdown_tools_to_right_roles(self):
        team = TeamManager()

        lead_tool_names = [tool.name for tool in team.get_agent_tools("lead")]
        coder_tool_names = [tool.name for tool in team.get_agent_tools("coder")]

        self.assertIn("request_shutdown", lead_tool_names)
        self.assertIn("respond_shutdown", coder_tool_names)
        self.assertNotIn("request_shutdown", coder_tool_names)

    def test_lead_can_reactivate_stopped_teammate(self):
        team = TeamManager()
        team.request_shutdown("coder", "任务已结束")
        request_id = next(iter(team.shutdown_requests.keys()))
        team.respond_shutdown("coder", request_id, True, "已收尾完成")

        result = team.reactivate_agent("coder", "开始新任务")

        self.assertIn("已恢复", result)
        self.assertEqual(team.agent_status["coder"], "active")

    def test_coder_can_submit_merge_request(self):
        team = TeamManager()

        result = team.submit_merge_request(
            "coder", "team-coder", "abc1234", "完成 workspace 绑定"
        )

        self.assertIn("已发送", result)
        self.assertEqual(len(team.merge_requests), 1)
        request_id = next(iter(team.merge_requests.keys()))
        request = team.merge_requests[request_id]
        self.assertEqual(request["from"], "coder")
        self.assertEqual(request["to"], "lead")
        self.assertEqual(request["branch"], "team-coder")
        self.assertEqual(request["commit"], "abc1234")
        self.assertEqual(request["status"], "pending")
        self.assertEqual(team.mailboxes["lead"][-1].message_type, "merge_request")

    def test_submit_merge_request_auto_uses_workspace_branch_and_commit(self):
        team = TeamManager()

        with (
            patch.object(team, "ensure_agent_workspace") as mock_ensure,
            patch("team.subprocess.run") as mock_run,
        ):
            team.agent_workspaces["coder"] = r"H:\tmp\coder-worktree"
            mock_run.side_effect = [
                type(
                    "Result",
                    (),
                    {"returncode": 0, "stdout": "team-coder\n", "stderr": ""},
                )(),
                type(
                    "Result", (), {"returncode": 0, "stdout": "abc1234\n", "stderr": ""}
                )(),
            ]

            result = team.submit_merge_request("coder", "", "", "自动带分支和提交")

        self.assertIn("已发送", result)
        mock_ensure.assert_called_once_with("coder")
        request_id = next(iter(team.merge_requests.keys()))
        request = team.merge_requests[request_id]
        self.assertEqual(request["branch"], "team-coder")
        self.assertEqual(request["commit"], "abc1234")

    def test_lead_can_respond_merge_request(self):
        team = TeamManager()
        team.submit_merge_request(
            "coder", "team-coder", "abc1234", "完成 workspace 绑定"
        )
        request_id = next(iter(team.merge_requests.keys()))

        result = team.respond_merge_request(request_id, True, "同意合并")

        self.assertIn("已批准", result)
        self.assertEqual(team.merge_requests[request_id]["status"], "approved")
        self.assertEqual(team.mailboxes["coder"][-1].message_type, "merge_response")

    def test_get_agent_tools_exposes_merge_tools_to_right_roles(self):
        team = TeamManager()

        lead_tool_names = [tool.name for tool in team.get_agent_tools("lead")]
        coder_tool_names = [tool.name for tool in team.get_agent_tools("coder")]

        self.assertIn("respond_merge_request", lead_tool_names)
        self.assertIn("submit_merge_request", coder_tool_names)
        self.assertNotIn("respond_merge_request", coder_tool_names)

    def test_workspace_bound_read_file_blocks_escape(self):
        team = TeamManager()
        with TemporaryDirectory() as workspace_dir:
            team.agent_workspaces["coder"] = workspace_dir
            static_tools = get_static_tools_for_agent("coder")
            bound_tools = team.get_workspace_bound_tools("coder", static_tools)

            read_tool = next(tool for tool in bound_tools if tool.name == "read_file")
            result = read_tool.invoke({"file_path": "../outside.txt"})

            self.assertIn("workspace", result)

    def test_workspace_bound_write_file_writes_inside_workspace(self):
        team = TeamManager()
        with TemporaryDirectory() as workspace_dir:
            team.agent_workspaces["coder"] = workspace_dir
            static_tools = get_static_tools_for_agent("coder")
            bound_tools = team.get_workspace_bound_tools("coder", static_tools)

            write_tool = next(tool for tool in bound_tools if tool.name == "write_file")
            result = write_tool.invoke({"file_path": "notes.txt", "content": "hello"})

            self.assertIn("文件已写入", result)
            self.assertEqual(
                (Path(workspace_dir) / "notes.txt").read_text(encoding="utf-8"), "hello"
            )

    def test_workspace_bound_background_run_uses_workspace_cwd(self):
        team = TeamManager()
        with TemporaryDirectory() as workspace_dir:
            team.agent_workspaces["coder"] = workspace_dir
            static_tools = get_static_tools_for_agent("coder")
            bound_tools = team.get_workspace_bound_tools("coder", static_tools)

            background_tool = next(
                tool for tool in bound_tools if tool.name == "background_run"
            )

            with patch("team.BG_MANAGER.run", return_value="abc123") as mock_run:
                result = background_tool.invoke({"command": "pytest"})

            self.assertIn("abc123", result)
            mock_run.assert_called_once()
            call_args, call_kwargs = mock_run.call_args
            self.assertEqual(call_args[0], "pytest")
            self.assertEqual(
                Path(call_kwargs["cwd"]).resolve(), Path(workspace_dir).resolve()
            )


if __name__ == "__main__":
    unittest.main()
