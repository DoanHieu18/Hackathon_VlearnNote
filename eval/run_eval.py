"""Chạy trọn bộ eval/golden_set.json qua graph THẬT (Gemini) và ghi bảng kết quả.

Chạy:
    cd backend
    .venv/Scripts/python.exe ../eval/run_eval.py

Ghi ra `eval/run_<NNN>.md` + `eval/run_<NNN>.json` — đủ MỌI case kể cả fail.
Không được sửa số liệu sau khi chạy (luật rubric: số liệu bị chỉnh sửa không tính).
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND / ".env")

from agent.graph import ingest_graph, question_graph  # noqa: E402
from agent.state import TranscriptSegment  # noqa: E402

# Cụm từ cho thấy agent thừa nhận KHÔNG có căn cứ (thay vì bịa).
NOT_FOUND_MARKERS = (
    "không tìm thấy", "chưa tìm thấy", "không thấy", "chưa thấy",
    "không có", "chưa có", "không đề cập", "chưa đề cập",
    "không được nhắc", "chưa được nhắc", "không nhắc", "chưa nhắc",
    "không xuất hiện", "chưa xuất hiện", "không ghi nhận", "không nằm trong",
    "ngoài phạm vi", "không thuộc",
)

# Cụm từ cho thấy agent hỏi lại / khoanh vùng thay vì đoán bừa.
ASK_BACK_MARKERS = (
    "?", "bạn muốn", "bạn cần", "cụ thể", "phần nào", "đoạn nào",
    "chỗ nào", "ý bạn", "làm rõ", "nói rõ",
)

RATE_LIMIT_SLEEP = float(os.getenv("EVAL_SLEEP_SECONDS", "2"))


def _contains_any(text: str, needles) -> bool:
    low = text.lower()
    return any(n.lower() in low for n in needles)


def _run_classify(case: dict) -> tuple[bool, str, dict]:
    data = case["input"]
    segment = TranscriptSegment(
        speaker=data["speaker"], text=data["text"], timestamp_s=float(data["timestamp_s"])
    )
    state = ingest_graph.invoke({"incoming_segment": segment, "rolling_transcript": [segment]})
    cls = state.get("classification") or {}
    got_worthy = bool(cls.get("is_note_worthy"))
    got_label = cls.get("label")
    got_summary = cls.get("summary") or ""
    got_speaker = cls.get("speaker") or ""
    exp = case["expected"]
    actual = {
        "is_note_worthy": got_worthy,
        "label": got_label,
        "speaker": got_speaker,
        "summary": got_summary,
    }

    reasons = []
    if "is_note_worthy" in exp and got_worthy != exp["is_note_worthy"]:
        reasons.append(f"is_note_worthy={got_worthy}, mong đợi {exp['is_note_worthy']}")
    if "label" in exp and got_label != exp["label"]:
        reasons.append(f"label='{got_label}', mong đợi '{exp['label']}'")
    # `label_in`: dùng khi taxonomy có nhiều nhãn cùng đúng một cách chính đáng
    # (vd. một số liệu minh hoạ có thể là example/key_point/insight). Vẫn chấm
    # fail nếu rơi ra ngoài tập nhãn hợp lý.
    if "label_in" in exp and got_label not in exp["label_in"]:
        reasons.append(f"label='{got_label}', mong đợi một trong {exp['label_in']}")
    if "speaker_must_contain_any" in exp and not _contains_any(
        got_speaker, exp["speaker_must_contain_any"]
    ):
        reasons.append(
            f"speaker='{got_speaker}', mong đợi chứa một trong {exp['speaker_must_contain_any']}"
        )
    if "summary_must_contain_all" in exp:
        missing = [k for k in exp["summary_must_contain_all"] if k.lower() not in got_summary.lower()]
        if missing:
            reasons.append(f"summary thiếu: {missing}")
    if "summary_must_contain_any" in exp and not _contains_any(
        got_summary, exp["summary_must_contain_any"]
    ):
        reasons.append(f"summary không chứa bất kỳ: {exp['summary_must_contain_any']}")

    return (not reasons), "; ".join(reasons), actual


def _run_question(case: dict) -> tuple[bool, str, dict]:
    data = case["input"]
    segments = [
        TranscriptSegment(
            speaker=s["speaker"], text=s["text"], timestamp_s=float(s["timestamp_s"])
        )
        for s in data.get("context_segments", [])
    ]
    state = question_graph.invoke(
        {
            "student_question": data["student_question"],
            "rolling_transcript": segments,
            "session_notes": [],
        }
    )
    intent = (state.get("route_decision") or {}).get("intent")
    answer = ((state.get("qa_answer") or {}).get("text")) or ""
    exp = case["expected"]
    actual = {"intent": intent, "answer": answer}

    reasons = []
    if "intent" in exp and intent != exp["intent"]:
        reasons.append(f"intent='{intent}', mong đợi '{exp['intent']}'")
    if "must_not_be" in exp and intent == exp["must_not_be"]:
        reasons.append(f"intent='{intent}' — không được là '{exp['must_not_be']}'")
    if exp.get("must_say_not_found") is True and not _contains_any(answer, NOT_FOUND_MARKERS):
        reasons.append("câu trả lời KHÔNG thừa nhận thiếu căn cứ (nguy cơ bịa nguồn)")
    if exp.get("must_say_not_found") is False and _contains_any(answer, NOT_FOUND_MARKERS):
        reasons.append("từ chối dù transcript THẬT SỰ có căn cứ")
    if "answer_must_contain_any" in exp and not _contains_any(
        answer, exp["answer_must_contain_any"]
    ):
        reasons.append(f"câu trả lời không chứa: {exp['answer_must_contain_any']}")
    if exp.get("must_ask_back_or_scope") and not _contains_any(
        answer, ASK_BACK_MARKERS + NOT_FOUND_MARKERS
    ):
        reasons.append("không hỏi lại/khoanh vùng khi câu hỏi mơ hồ")

    return (not reasons), "; ".join(reasons), actual


RUNNERS = {
    "classify_segment": _run_classify,
    "route_intent": _run_question,
    "route_intent_ambiguous": _run_question,
    "catch_up_grounding": _run_question,
}


def main() -> None:
    golden = json.loads((ROOT / "eval" / "golden_set.json").read_text(encoding="utf-8"))
    cases = golden["cases"]
    model = os.getenv("VLEARNNOTE_MODEL", "(mặc định)")

    results = []
    for i, case in enumerate(cases, 1):
        runner = RUNNERS[case["type"]]
        measured = True
        try:
            passed, reason, actual = runner(case)
            error = None
        except Exception as exc:  # noqa: BLE001 — case lỗi vẫn phải vào bảng, không bỏ qua
            passed, reason, actual, error = False, f"LỖI KHI CHẠY: {exc}", {}, str(exc)
            # Hết quota/rate-limit là lỗi HẠ TẦNG, không phải sản phẩm trả sai.
            # Tách riêng để không làm loãng tỉ lệ đạt (ghi số trung thực, không
            # tính case chưa đo được vào mẫu số).
            low = str(exc).lower()
            if "quota" in low or "rate-limit" in low or "429" in low:
                measured = False

        results.append(
            {
                "id": case["id"],
                "type": case["type"],
                "class": case["class"],
                "real_source": case.get("real_source", ""),
                "measured": measured,
                "passed": passed,
                "reason": reason,
                "actual": actual,
                "error": error,
            }
        )
        mark = "PASS" if passed else ("FAIL" if measured else "CHƯA ĐO ĐƯỢC")
        print(f"[{i:>2}/{len(cases)}] {case['id']:<8} {mark}  {reason}", flush=True)
        time.sleep(RATE_LIMIT_SLEEP)

    measured_results = [r for r in results if r["measured"]]
    not_measured = [r for r in results if not r["measured"]]
    total = len(measured_results)
    passed_n = sum(1 for r in measured_results if r["passed"])

    # Điều kiện cứng của quality bar: 0 lần bịa nguồn (mọi case lớp ①).
    class1 = [r for r in measured_results if r["class"].startswith("①")]
    class1_pass = sum(1 for r in class1 if r["passed"])

    by_class: dict[str, list] = {}
    for r in measured_results:
        by_class.setdefault(r["class"], []).append(r)

    run_no = 1
    while (ROOT / "eval" / f"run_{run_no:03d}.md").exists():
        run_no += 1
    stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    pct = (passed_n / total * 100) if total else 0.0
    lines = [
        f"# Kết quả chạy golden set — lượt {run_no:03d}",
        "",
        f"- **Thời điểm**: {stamp}",
        f"- **Model**: `{model}`",
        f"- **Số case đo được**: {total}/{len(results)}"
        + (
            f" — ⚠️ {len(not_measured)} case CHƯA ĐO ĐƯỢC do hết quota API (lỗi hạ tầng, "
            "không phải sản phẩm trả sai). Lượt này KHÔNG dùng làm số liệu chính thức."
            if not_measured
            else ""
        ),
        f"- **Kết quả trên số case đo được**: **{passed_n}/{total}** ({pct:.1f}%)",
        f"- **Điều kiện cứng (lớp ① không bịa nguồn)**: {class1_pass}/{len(class1)}"
        f" ({'ĐẠT' if class1 and class1_pass == len(class1) else 'KHÔNG ĐẠT'})",
        f"- **Quality bar đã cam kết**: {golden['_meta']['quality_bar']}",
        "",
        "## Theo lớp chỗ khó",
        "",
        "| Lớp | Đạt/Tổng |",
        "|---|---|",
    ]
    for cls, rs in sorted(by_class.items()):
        lines.append(f"| {cls} | {sum(1 for r in rs if r['passed'])}/{len(rs)} |")

    lines += [
        "",
        "## Chi tiết từng case (đủ mọi case, kể cả fail)",
        "",
        "| # | ID | Lớp | Loại | Nguồn thật | Kết quả | Vì sao fail |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(results, 1):
        src = (r["real_source"] or "—").replace("|", "/")
        reason = (r["reason"] or "").replace("|", "/") or "—"
        if not r["measured"]:
            verdict = "⏸️ CHƯA ĐO ĐƯỢC (hết quota)"
        elif r["passed"]:
            verdict = "✅ PASS"
        else:
            verdict = "❌ FAIL"
        lines.append(
            f"| {i} | `{r['id']}` | {r['class']} | {r['type']} | {src} | {verdict} | {reason} |"
        )

    fails = [r for r in measured_results if not r["passed"]]
    if fails:
        lines += ["", "## Output thật của các case FAIL (để phân tích nguyên nhân)", ""]
        for r in fails:
            lines += [
                f"### `{r['id']}` — {r['class']}",
                f"- Vì sao fail: {r['reason']}",
                f"- Output thật: `{json.dumps(r['actual'], ensure_ascii=False)[:600]}`",
                "",
            ]

    (ROOT / "eval" / f"run_{run_no:03d}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "eval" / f"run_{run_no:03d}.json").write_text(
        json.dumps(
            {
                "run": run_no,
                "timestamp": stamp,
                "model": model,
                "total_cases": len(results),
                "measured": total,
                "not_measured": len(not_measured),
                "passed": passed_n,
                "class1_passed": class1_pass,
                "class1_total": len(class1),
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\n=== DO DUOC: {total}/{len(results)} case (chua do duoc: {len(not_measured)})")
    print(f"=== KET QUA: {passed_n}/{total} ({pct:.1f}%)")
    print(f"=== Lop (1) nguon su that: {class1_pass}/{len(class1)}")
    print(f"=== Da ghi: eval/run_{run_no:03d}.md")


if __name__ == "__main__":
    main()
