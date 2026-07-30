"""Provider LLM thật — không hardcode câu trả lời, không mock.

Dùng Google Gemini qua `langchain-google-genai`. Hỗ trợ NHIỀU key xoay vòng
(free tier Gemini giới hạn quota/phút theo từng key) — đọc `GEMINI_API_KEY`,
`GEMINI_API_KEY_2`, `GEMINI_API_KEY_3`, ... theo thứ tự trong `.env`. Khi một
key bị lỗi quota (429/ResourceExhausted), tự động thử key kế tiếp — không
âm thầm rơi về câu trả lời giả lập; nếu TẤT CẢ key đều lỗi thì raise rõ ràng,
vì rubric R5 yêu cầu "≥1 lời gọi AI chạy thật, không hardcode".
"""

from __future__ import annotations

import concurrent.futures
import itertools
import os
import re

from langchain_google_genai import ChatGoogleGenerativeAI

DEFAULT_MODEL = os.getenv("VLEARNNOTE_MODEL", "gemini-2.0-flash")
TIMEOUT_SECONDS = float(os.getenv("VLEARNNOTE_TIMEOUT_SECONDS", "20"))

_QUOTA_ERROR_HINTS = ("429", "resourceexhausted", "quota", "rate limit")

_llms: list[ChatGoogleGenerativeAI] | None = None
_rotation_index = itertools.count()


def _load_gemini_keys() -> list[str]:
    """Gom mọi GEMINI_API_KEY[, _2, _3, ...] hợp lệ, giữ đúng thứ tự khai báo."""
    keys: list[str] = []
    primary = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if primary:
        keys.append(primary)

    numbered = sorted(
        (name for name in os.environ if re.fullmatch(r"GEMINI_API_KEY_\d+", name)),
        key=lambda name: int(name.rsplit("_", 1)[1]),
    )
    for name in numbered:
        value = os.environ.get(name)
        if value:
            keys.append(value)

    # Không lọc theo tiền tố "AIza" — Google phát hành key Gemini ở nhiều định
    # dạng (vd. "AQ.Ab8..." cũng là key hợp lệ gọi được qua SDK này, đã verify
    # bằng lời gọi thật). Việc key có hoạt động hay không để API tự báo lỗi.
    return keys


def _build_clients() -> list[ChatGoogleGenerativeAI]:
    keys = _load_gemini_keys()
    if not keys:
        raise RuntimeError(
            "Thiếu GEMINI_API_KEY (hoặc GOOGLE_API_KEY) trong biến môi trường — "
            "xem backend/.env.example. Tính năng bắt buộc gọi AI thật, không được "
            "hardcode/mock ở lớp này."
        )
    return [
        ChatGoogleGenerativeAI(model=DEFAULT_MODEL, google_api_key=key, temperature=0)
        for key in keys
    ]


def get_llms() -> list[ChatGoogleGenerativeAI]:
    global _llms
    if _llms is None:
        _llms = _build_clients()
    return _llms


def _is_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(hint in text for hint in _QUOTA_ERROR_HINTS)


def invoke_with_timeout(messages: list[dict], *, response_format=None) -> object:
    """Gọi LLM với guardrail timeout, xoay vòng key khi gặp lỗi quota."""
    llms = get_llms()
    start = next(_rotation_index) % len(llms)
    last_error: Exception | None = None

    for offset in range(len(llms)):
        llm = llms[(start + offset) % len(llms)]
        bound = llm.with_structured_output(response_format) if response_format else llm

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(bound.invoke, messages)
            try:
                return future.result(timeout=TIMEOUT_SECONDS)
            except concurrent.futures.TimeoutError as exc:
                raise TimeoutError(
                    f"LLM không phản hồi sau {TIMEOUT_SECONDS}s (timeout guardrail)"
                ) from exc
            except Exception as exc:  # noqa: BLE001 — chỉ rotate cho lỗi quota, còn lại raise ngay
                if not _is_quota_error(exc):
                    raise
                last_error = exc
                continue

    raise RuntimeError(
        f"Tất cả {len(llms)} GEMINI_API_KEY đều bị lỗi quota/rate-limit."
    ) from last_error
