from typing import Dict, Any

from ..llm.base import BaseLLMService
from ..knowledge.service import KnowledgeService
from ..core.models import TestCase
from .prompts import TestCaseReviewerPrompt
from utils.logger_manager import get_logger


class TestCaseReviewerAgent:
    """测试用例评审Agent"""

    def __init__(self, llm_service: BaseLLMService, knowledge_service: KnowledgeService):
        self.llm_service = llm_service
        self.knowledge_service = knowledge_service
        self.prompt = TestCaseReviewerPrompt()
        self.logger = get_logger(self.__class__.__name__)

    def review(self, test_case: TestCase) -> Dict[str, Any]:
        """评审测试用例"""
        try:
            self.logger.info("待评审的测试用例数据: \n%s", test_case)
            test_case_dict = {
                "description": test_case.description,
                "test_steps": test_case.test_steps,
                "expected_results": test_case.expected_results,
            }

            messages = self.prompt.format_messages(test_case_dict)
            self.logger.info("构建后的评审提示词: \n%s", messages)

            result = self.llm_service.invoke(messages)
            raw_text = result.content if hasattr(result, "content") else str(result)
            cleaned = self._extract_json(raw_text)
            if cleaned != raw_text:
                self.logger.info("评审结果已截取为JSON片段")
            return cleaned

        except Exception as e:
            self.logger.error("评审过程出错: %s", str(e), exc_info=True)
            raise Exception(f"评审失败: {str(e)}")

    def _extract_json(self, text: str) -> str:
        """从模型输出中截取JSON对象或数组字符串"""
        if not isinstance(text, str):
            return str(text)

        content = text.strip()
        if content.startswith("```"):
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1].replace("json", "").strip()

        start_obj = content.find("{")
        end_obj = content.rfind("}")
        if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
            return content[start_obj:end_obj + 1].strip()

        start_arr = content.find("[")
        end_arr = content.rfind("]")
        if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
            return content[start_arr:end_arr + 1].strip()

        return content
