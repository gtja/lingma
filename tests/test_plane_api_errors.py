import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.test import RequestFactory, TestCase

from apps.core.api_views import plane_one_click_generate, plane_work_items
from apps.core.models import PlaneWorkItem, TestCase as TestCaseModel


class PlaneApiErrorTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_plane_refresh_maps_upstream_502_to_bad_gateway(self):
        request = self.factory.post(
            "/api/plane-work-items/",
            data=json.dumps({"max_items": 0}),
            content_type="application/json",
        )

        with (
            patch("apps.core.api_views._ensure_plane_work_item_table"),
            patch(
                "apps.core.api_views.sync_work_items_to_db",
                side_effect=RuntimeError(
                    "GET http://plane.jing-an.com:3238/api/v1/workspaces/gtja/projects/ failed: 502"
                ),
            ),
        ):
            response = plane_work_items(request)

        payload = json.loads(response.content)
        self.assertEqual(response.status_code, 502)
        self.assertIn("Plane", payload["message"])
        self.assertIn("502", payload["message"])


class PlaneOneClickGenerateTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.item = PlaneWorkItem.objects.create(
            project_id="p1",
            project_name="Plane 项目",
            work_item_id="w1",
            work_item_name="设备列表",
            work_item_content="需要生成设备列表相关测试用例",
        )

    def test_plane_generate_falls_back_to_qwen_and_returns_cases(self):
        unique_description = "设备列表展示正常-回退到qwen"
        request = self.factory.post(
            "/api/plane-one-click-generate/",
            data=json.dumps({"id": self.item.id, "llm_provider": "kimi", "case_count": 0}),
            content_type="application/json",
        )

        fake_settings = SimpleNamespace(
            LLM_PROVIDERS={
                "default_provider": "qwen",
                "qwen": {"name": "Qwen", "model": "qwen-max", "api_key": "qwen-key"},
                "kimi": {"name": "Kimi", "model": "kimi-k2.5", "api_key": "kimi-key"},
            }
        )

        class FakeGenerator:
            def __init__(self, llm_service, **kwargs):
                self.llm_service = llm_service

            def generate(self, requirements, input_type="requirement"):
                if self.llm_service.provider == "kimi":
                    raise Exception("Error code: 502 Bad Gateway")
                self.llm_service.last_provider_used = "qwen"
                return [
                    {
                        "description": unique_description,
                        "test_steps": ["进入设备列表"],
                        "expected_results": ["看到设备列表数据"],
                    }
                ]

        def fake_create(provider, **config):
            return SimpleNamespace(provider=provider, last_provider_used=provider)

        with (
            patch("apps.core.api_views.settings", fake_settings),
            patch("apps.core.api_views._ensure_plane_work_item_table"),
            patch("apps.core.views.knowledge_service", object()),
            patch("apps.core.api_views.LLMServiceFactory.create", side_effect=fake_create),
            patch("apps.core.api_views.TestCaseGeneratorAgent", side_effect=FakeGenerator),
            patch("apps.core.api_views.logger", create=True) as mock_logger,
        ):
            response = plane_one_click_generate(request)

        payload = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["effective_provider"], "qwen")
        self.assertEqual(len(payload["test_cases"]), 1)
        mock_logger.warning.assert_called_once()
        mock_logger.info.assert_called()

        saved_case = TestCaseModel.objects.filter(description=unique_description).latest("id")
        self.assertEqual(saved_case.llm_provider, "qwen")
        self.assertEqual(saved_case.description, unique_description)


if __name__ == "__main__":
    unittest.main()
