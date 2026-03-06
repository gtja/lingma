import os
import unittest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from apps.core.api_views import _map_llm_error


class LLMErrorMappingTests(unittest.TestCase):
    def test_map_bad_gateway_to_502(self):
        status, msg = _map_llm_error(Exception("Error code: 502 Bad Gateway"))
        self.assertEqual(status, 502)
        self.assertIn("502", msg)

    def test_map_generic_error_to_500(self):
        status, msg = _map_llm_error(Exception("some parse error"))
        self.assertEqual(status, 500)
        self.assertIn("生成失败", msg)


if __name__ == "__main__":
    unittest.main()
