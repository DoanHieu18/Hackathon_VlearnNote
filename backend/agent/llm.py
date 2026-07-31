"""Provider LLM thật — không hardcode câu trả lời, không mock.

Hỗ trợ CẢ HAI provider, tự nhận theo key có trong `.env` (xem `.env.example`):
  - OpenAI  : `OPENAI_API_KEY`  (+ `OPENAI_API_KEY_2..N` nếu muốn xoay vòng)
  - Gemini  : `GEMINI_API_KEY`  (+ `GEMINI_API_KEY_2..N`) hoặc `GOOGLE_API_KEY`

Vì sao cần cả hai: nhóm có 5 key Gemini free tier (quota ngày rất thấp — 20
request/model) và có thể được cấp key OpenAI của khoá. Ai có key nào thì chạy
key đó, không phải sửa code.

Nếu không có key nào hợp lệ thì raise ngay — không âm thầm rơi về câu trả lời
giả lập, vì rubric R5 yêu cầu "≥1 lời gọi AI chạy thật, không hardcode".
"""

from __future__ import annotations

import concurrent.futures
import itertools
import logging
import os
import re

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = float(os.getenv("VLEARNNOTE_TIMEOUT_SECONDS", "20"))

# Lỗi đáng để đổi sang key khác (hết quota/bị chặn nhịp), phân biệt với lỗi
# prompt/schema — loại sau phải raise ngay để nhóm thấy mà sửa.
_QUOTA_ERROR_HINTS = ("429", "resourceexhausted", "quota", "rate limit", "rate_limit")

_DEFAULT_MODEL = {"openai": "gpt-4o-mini", "gemini": "gemini-2.5-flash"}
_MODEL_PREFIX = {"openai": ("gpt", "o1", "o3", "o4", "chatgpt"), "gemini": ("gemini",)}

_clients: list | None = None
_provider: str | None = None
_rotation_index = itertools.count()


def _collect_keys(base: str) -> list[str]:
    """Gom `BASE` + `BASE_2`, `BASE_3`, … theo đúng thứ tự số, bỏ giá trị rỗng."""
    keys: list[str] = []
    primary = os.environ.get(base)
    if primary and primary.strip():
        keys.append(primary.strip())

    numbered = sorted(
        (name for name in os.environ if re.fullmatch(rf"{re.escape(base)}_\d+", name)),
        key=lambda name: int(name.rsplit("_", 1)[1]),
    )
    for name in numbered:
        value = os.environ.get(name)
        if value and value.strip():
            keys.append(value.strip())
    return keys


def _detect_provider() -> tuple[str, list[str]]:
    """Chọn provider theo key thực có. `VLEARNNOTE_PROVIDER` để ép thủ công."""
    openai_keys = _collect_keys("OPENAI_API_KEY")
    gemini_keys = _collect_keys("GEMINI_API_KEY") or _collect_keys("GOOGLE_API_KEY")

    forced = (os.getenv("VLEARNNOTE_PROVIDER") or "").strip().lower()
    if forced:
        if forced not in _DEFAULT_MODEL:
            raise RuntimeError(
                f"VLEARNNOTE_PROVIDER='{forced}' không hợp lệ — chỉ nhận 'openai' hoặc 'gemini'."
            )
        keys = openai_keys if forced == "openai" else gemini_keys
        if not keys:
            raise RuntimeError(
                f"VLEARNNOTE_PROVIDER='{forced}' nhưng không tìm thấy key tương ứng "
                f"trong biến môi trường — xem backend/.env.example."
            )
        return forced, keys

    if openai_keys:
        return "openai", openai_keys
    if gemini_keys:
        return "gemini", gemini_keys

    raise RuntimeError(
        "Không tìm thấy key LLM nào: cần OPENAI_API_KEY hoặc GEMINI_API_KEY "
        "(xem backend/.env.example). Tính năng bắt buộc gọi AI thật, không được "
        "hardcode/mock ở lớp này."
    )


def _resolve_model(provider: str) -> str:
    """Lấy model cho provider, bỏ qua `VLEARNNOTE_MODEL` nếu khác họ model.

    Tránh đúng cái bẫy: `.env` để `VLEARNNOTE_MODEL=gemini-2.5-flash` nhưng lại
    chạy bằng key OpenAI (hoặc ngược lại) — khi đó tên model sai và lỗi trả về
    rất khó hiểu.
    """
    override = (
        os.getenv(f"VLEARNNOTE_MODEL_{provider.upper()}") or os.getenv("VLEARNNOTE_MODEL") or ""
    ).strip()
    if not override:
        return _DEFAULT_MODEL[provider]
    if override.lower().startswith(_MODEL_PREFIX[provider]):
        return override

    fallback = _DEFAULT_MODEL[provider]
    logger.warning(
        "VLEARNNOTE_MODEL='%s' không thuộc họ model của provider '%s' — dùng '%s'. "
        "Đặt VLEARNNOTE_MODEL_%s nếu muốn chỉ định riêng cho provider này.",
        override,
        provider,
        fallback,
        provider.upper(),
    )
    return fallback


def _build_clients() -> tuple[str, list]:
    provider, keys = _detect_provider()
    model = _resolve_model(provider)

    # max_retries=0: để lớp xoay vòng key ở dưới xử lý lỗi quota, thay vì để SDK
    # tự retry lâu trên cùng một key đã hết quota rồi mới báo lỗi.
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        clients = [
            ChatOpenAI(model=model, api_key=key, temperature=0, max_retries=0) for key in keys
        ]
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI

        clients = [
            ChatGoogleGenerativeAI(
                model=model, google_api_key=key, temperature=0, max_retries=0
            )
            for key in keys
        ]

    logger.info("LLM provider=%s model=%s (%d key)", provider, model, len(clients))
    return provider, clients


def get_clients() -> list:
    global _clients, _provider
    if _clients is None:
        _provider, _clients = _build_clients()
    return _clients


def get_provider() -> str:
    get_clients()
    return _provider or "unknown"


def describe() -> str:
    """Mô tả provider/model đang dùng — để ghi vào bảng kết quả eval."""
    clients = get_clients()
    model = getattr(clients[0], "model_name", None) or getattr(clients[0], "model", "?")
    return f"{get_provider()}:{model} ({len(clients)} key)"


def _is_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(hint in text for hint in _QUOTA_ERROR_HINTS)


def invoke_with_timeout(messages: list[dict], *, response_format=None) -> object:
    """Gọi LLM với guardrail timeout, xoay vòng key khi gặp lỗi quota."""
    clients = get_clients()
    start = next(_rotation_index) % len(clients)
    last_error: Exception | None = None

    for offset in range(len(clients)):
        client = clients[(start + offset) % len(clients)]
        bound = client.with_structured_output(response_format) if response_format else client

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
        f"Tất cả {len(clients)} key của provider '{get_provider()}' đều bị lỗi "
        f"quota/rate-limit."
    ) from last_error
