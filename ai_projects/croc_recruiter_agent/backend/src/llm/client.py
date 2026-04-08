from __future__ import annotations

import os
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI

from src.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAILLMClient:
    """
    OpenAI LLM client wrapper.

    Responsibilities:
    - load environment variables
    - validate API key
    - handle chat completion calls
    - normalize output
    """

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        self.client = OpenAI(api_key=api_key)
        self.model = model

        logger.info("llm.client.initialized", extra={"model": model})

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 700,
    ) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content

            if not content:
                logger.warning("llm.empty_response")
                return ""

            return content.strip()

        except Exception as e:
            logger.exception(
                "llm.request_failed",
                extra={"error": str(e)}
            )
            raise