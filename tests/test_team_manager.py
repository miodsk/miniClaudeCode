import unittest

from team import TeamManager


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


if __name__ == "__main__":
    unittest.main()
