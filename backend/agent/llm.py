"""Provider LLM thật — không hardcode câu trả lời, không mock.

Dùng Google Gemini qua `langchain-google-genai`. Cần biến môi trường
GEMINI_API_KEY hoặc GOOGLE_API_KEY (đọc từ .env, xem .env.example — key dạng
"AIza..." lấy từ Google AI Studio). Nếu thiếu key, lỗi ngay khi khởi tạo —
không âm thầm rơi về câu trả lời giả lập, vì rubric R5 yêu cầu "≥1 lời gọi AI
chạy thật, không hardcode".
"""

from __future__ import annotations

import concurrent.futures
import os

from langchain_google_genai import ChatGoogleGenerativeAI

DEFAULT_MODEL = os.getenv("VLEARNNOTE_MODEL", "gemini-2.0-flash")
TIMEOUT_SECONDS = float(os.getenv("VLEARNNOTE_TIMEOUT_SECONDS", "20"))

_llm: ChatGoogleGenerativeAI | None = None


def _read_gemini_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def get_llm() -> ChatGoogleGenerativeAI:
    global _llm
    if _llm is None:
        api_key = _read_gemini_key()
        if not api_key:
            raise RuntimeError(
                "Thiếu GEMINI_API_KEY (hoặc GOOGLE_API_KEY) trong biến môi trường — "
                "xem backend/.env.example. Tính năng bắt buộc gọi AI thật, không được "
                "hardcode/mock ở lớp này."
            )
        _llm = ChatGoogleGenerativeAI(model=DEFAULT_MODEL, google_api_key=api_key, temperature=0)
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
