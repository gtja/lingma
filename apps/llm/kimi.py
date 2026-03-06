from langchain_community.chat_models import ChatOpenAI
import os


class KimiChatModel(ChatOpenAI):
    """Kimi chat model (OpenAI-compatible API)."""

    def __init__(
        self,
        api_key: str = None,
        api_base: str = None,
        model: str = "kimi-k2.5",
        **kwargs,
    ):
        api_base = api_base or os.getenv("KIMI_API_BASE", "http://172.21.30.114:8020/v1")
        api_key = api_key or os.getenv("KIMI_API_KEY")
        if not api_key:
            raise ValueError(
                "Kimi API key is required. Set it via KIMI_API_KEY environment variable "
                "or pass it directly."
            )

        os.environ["OPENAI_API_KEY"] = api_key

        super().__init__(
            model_name=model,
            openai_api_base=api_base,
            **kwargs,
        )
