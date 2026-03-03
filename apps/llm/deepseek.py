from langchain_community.chat_models import ChatOpenAI
import os


class DeepSeekChatModel(ChatOpenAI):
    """DeepSeek chat model."""

    def __init__(
        self,
        api_key: str = None,
        api_base: str = None,
        model: str = "deepseek-chat",
        **kwargs,
    ):
        api_base = api_base or os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError(
                "DeepSeek API key is required. Set it via DEEPSEEK_API_KEY environment variable "
                "or pass it directly."
            )

        os.environ["OPENAI_API_KEY"] = api_key

        super().__init__(
            model_name=model,
            openai_api_base=api_base,
            **kwargs,
        )
