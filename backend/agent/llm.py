"""Provider LLM thật — không hardcode câu trả lời, không mock.

Dùng OpenAI qua `langchain-openai`. 
"""

from __future__ import annotations

import concurrent.futures
import os

from langchain_openai import ChatOpenAI

DEFAULT_MODEL = os.getenv("VLEARNNOTE_MODEL", "gpt-4o-mini")
TIMEOUT_SECONDS = float(os.getenv("VLEARNNOTE_TIMEOUT_SECONDS", "20"))

_llm: ChatOpenAI | None = None

def get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("Thiếu OPENAI_API_KEY trong biến môi trường.")
        _llm = ChatOpenAI(model=DEFAULT_MODEL, api_key=key, temperature=0)
    return _llm


def invoke_with_timeout(messages: list[dict], *, response_format=None) -> object:
    """Gọi LLM với guardrail timeout."""
    llm = get_llm()
    bound = llm.with_structured_output(response_format) if response_format else llm

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(bound.invoke, messages)
        try:
            return future.result(timeout=TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError as exc:
            raise TimeoutError(
                f"LLM không phản hồi sau {TIMEOUT_SECONDS}s (timeout guardrail)"
            ) from exc
