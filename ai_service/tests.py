"""ai_service 单元测试。"""

from django.test import SimpleTestCase

from ai_service.services import (
    AiAgentService,
    _MEMORY_FALSE_SUCCESS_RE,
)


class MemoryWriteEnforcementTests(SimpleTestCase):
    def setUp(self):
        self.svc = AiAgentService()

    def test_user_requests_memory_write_detected(self):
        self.assertTrue(
            self.svc._user_requests_github_memory_write(
                [{"role": "user", "content": "把右侧策略写入记忆中"}]
            )
        )
        self.assertTrue(
            self.svc._user_requests_github_memory_write(
                [{"role": "user", "content": "重新写入 memories/投资策略.md"}]
            )
        )

    def test_user_requests_memory_write_not_triggered_for_unrelated(self):
        self.assertFalse(
            self.svc._user_requests_github_memory_write(
                [{"role": "user", "content": "今天大盘怎么看"}]
            )
        )

    def test_tool_records_include_mybook_write(self):
        self.assertTrue(
            self.svc._tool_records_include_mybook_write(
                [{"tool_name": "append_github_mybook_memory", "is_error": False}]
            )
        )
        self.assertTrue(
            self.svc._tool_records_include_mybook_write(
                [{"tool_name": "put_github_mybook_memory", "is_error": False}]
            )
        )
        self.assertFalse(
            self.svc._tool_records_include_mybook_write(
                [{"tool_name": "read_github_mybook_file", "is_error": False}]
            )
        )
        self.assertFalse(
            self.svc._tool_records_include_mybook_write(
                [{"tool_name": "append_github_mybook_memory", "is_error": True}]
            )
        )

    def test_false_success_regex_matches_common_claims(self):
        self.assertIsNotNone(_MEMORY_FALSE_SUCCESS_RE.search("✅ **已覆盖写入！**"))
        self.assertIsNotNone(_MEMORY_FALSE_SUCCESS_RE.search("已经写入到记忆文件"))
        self.assertIsNone(_MEMORY_FALSE_SUCCESS_RE.search("请先说明你的持仓"))
