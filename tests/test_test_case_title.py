import unittest

from apps.core.title_utils import build_test_case_title


class TestCaseTitleTests(unittest.TestCase):
    def test_uses_description_as_title(self):
        title = build_test_case_title(
            description="兼容性测试：使用不同操作系统访问应用并执行文件对话",
            fallback_title="测试用例-1",
        )
        self.assertEqual(title, "兼容性测试：使用不同操作系统访问应用并执行文件对话")

    def test_falls_back_when_description_blank(self):
        title = build_test_case_title(description="   ", fallback_title="测试用例-2")
        self.assertEqual(title, "测试用例-2")

    def test_truncates_to_model_limit(self):
        title = build_test_case_title(description="a" * 250, fallback_title="测试用例-3")
        self.assertEqual(len(title), 200)
        self.assertEqual(title, "a" * 200)


if __name__ == "__main__":
    unittest.main()
