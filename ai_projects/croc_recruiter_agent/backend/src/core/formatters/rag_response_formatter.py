import re
from typing import List


def clean_llm_answer(answer: str) -> str:
    if not answer:
        return ""

    # remove "Answer:"
    answer = re.sub(r"(?i)^answer:\s*", "", answer.strip())

    # remove "(Source: ...)"
    answer = re.sub(r"\(source:.*?\)", "", answer, flags=re.IGNORECASE)

    # remove "Sources:"
    answer = re.sub(r"(?i)sources?:.*", "", answer)

    return answer.strip()


def format_rag_response(answer: str, sources: List[str]) -> str:
    """
    Final formatter (single source of truth)
    """

    cleaned_answer = clean_llm_answer(answer)

    unique_sources = list(dict.fromkeys(sources or []))

    formatted = f"{cleaned_answer}\n\n"

    if unique_sources:
        for source in unique_sources:
            formatted += f"[Source: {source}]\n"
    else:
        formatted += "[Source: unknown]\n"

    return formatted.strip()
