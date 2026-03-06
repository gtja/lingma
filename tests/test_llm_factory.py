import unittest
import os
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from apps.llm.base import LLMServiceFactory


class LLMFactoryTests(unittest.TestCase):
    def test_create_kimi_provider_uses_kimi_chat_model(self):
        fake_settings = SimpleNamespace(
            LLM_PROVIDERS={
                "default_provider": "kimi",
                "kimi": {
                    "name": "Kimi",
                    "model": "kimi-k2.5",
                    "api_base": "http://172.21.30.114:8020/v1",
                    "api_key": "test-key",
                },
            }
        )

        with patch("apps.llm.base.settings", fake_settings), patch("apps.llm.base.KimiChatModel") as mock_kimi:
            sentinel = object()
            mock_kimi.return_value = sentinel

            result = LLMServiceFactory.create("kimi")

            self.assertIs(result, sentinel)
            mock_kimi.assert_called_once()


if __name__ == "__main__":
    unittest.main()
