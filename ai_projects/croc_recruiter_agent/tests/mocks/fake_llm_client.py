from typing import Dict, List


class FakeLLMClient:
    """
    Mock deterministic LLM.
    Counts how many times it was called (to validate cache).
    """

    def __init__(self):
        self.call_count = 0

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 700,
    ) -> str:
        self.call_count += 1

        # deterministic response
        return "This is a mocked answer based on retrieved context."