"""Provider LLM thật — không hardcode câu trả lời, không mock.

Cần biến môi trường OPENAI_API_KEY (đọc từ .env, xem .env.example). Nếu thiếu
key, lỗi ngay khi khởi tạo — không âm thầm rơi về câu trả lời giả lập, vì
rubric R5 yêu cầu "≥1 lời gọi AI chạy thật, không hardcode".
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
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Thiếu OPENAI_API_KEY trong biến môi trường — xem backend/.env.example. "
                "Tính năng bắt buộc gọi AI thật, không được hardcode/mock ở lớp này."
            )
        _llm = ChatOpenAI(model=DEFAULT_MODEL, api_key=api_key, temperature=0)
    return _llm


def invoke_with_timeout(messages: list[dict], *, response_format=None) -> object:
    """Gọi LLM với guardrail timeout — không để một lời gọi treo làm nghẽn cả stream."""
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
