"""Đếm bằng chứng (đường B) trên chatlog thật — chạy lại được để kiểm chứng.

Chạy:
    backend/.venv/Scripts/python.exe evidence/mine_evidence.py

In ra từng con số kèm ĐÚNG quy tắc đếm, và ghi `evidence/mining_report.md`.
Không đọc file nào ngoài data pack được cấp; không ghi nguyên văn dài ra repo
(chỉ trích ≤160 ký tự kèm mã hội thoại để trace) — đúng luật bảo mật data pack.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "vlearn-pack" / "chatlog" / "chat_history_anonymized_for_hackathon.csv"
OUT_PATH = ROOT / "evidence" / "mining_report.md"

# --- Quy tắc đếm, khai báo tường minh để người khác kiểm lại được -------------

# Tutor thừa nhận không có căn cứ trong tài liệu.
NOT_FOUND_RE = re.compile(
    r"không tìm thấy|không đề cập|không có trong|ngoài phạm vi|không thuộc|"
    r"không tìm được|chưa tìm thấy",
    re.I,
)

# Học viên xin tóm tắt / xin lại nội dung (nhu cầu bắt kịp bài).
RECAP_RE = re.compile(r"tóm tắt|tóm lại|tổng hợp|ý chính|nội dung chính|key ?takeaway", re.I)

# Học viên báo không hiểu / cần giải thích lại.
CONFUSED_RE = re.compile(r"không hiểu|chưa hiểu|khó hiểu|giải thích lại|nói lại|hiểu rõ", re.I)

# Tin nhắn không mang nội dung câu hỏi: sau khi bỏ tiền tố "(Trang N, đoạn được
# chọn: ...)" thì phần học viên tự gõ ngắn hơn 12 ký tự.
TERSE_MAX_LEN = 12

PREFIX_RE = re.compile(r"^\(Trang[^)]*\)\s*", re.S)


def student_text(content: str) -> str:
    """Bỏ phần metadata VLearn tự chèn, chỉ lấy chữ học viên thật sự gõ."""
    return PREFIX_RE.sub("", content.strip()).strip()


def snippet(text: str, limit: int = 160) -> str:
    one_line = " ".join(text.split())
    return one_line[:limit] + ("…" if len(one_line) > limit else "")


def main() -> None:
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    students = [r for r in rows if r["role"] == "student"]
    tutors = [r for r in rows if r["role"] == "tutor"]
    n_pairs = len(students)

    in_class = [r for r in rows if r["conversation_mode"] == "in_class"]
    not_found = [r for r in tutors if NOT_FOUND_RE.search(r["content"])]
    no_cite = [r for r in tutors if r["citations"].strip() in ("", "[]")]
    recap = [r for r in students if RECAP_RE.search(student_text(r["content"]))]
    confused = [r for r in students if CONFUSED_RE.search(student_text(r["content"]))]
    terse = [r for r in students if len(student_text(r["content"])) < TERSE_MAX_LEN]
    checked = [r for r in rows if r["asked_check_question"] == "True"]
    rated = [r for r in rows if r["rating"].strip()]
    rated_down = [r for r in rated if r["rating"] == "down"]

    # Hội thoại nhiều lượt = học viên phải hỏi lại nhiều lần trong cùng một mạch.
    per_conv: dict[str, int] = {}
    for r in students:
        per_conv[r["conversation_id"]] = per_conv.get(r["conversation_id"], 0) + 1
    multi_turn = {c: n for c, n in per_conv.items() if n >= 2}

    def pct(part: int, whole: int) -> str:
        return f"{part}/{whole} ({part / whole * 100:.1f}%)"

    metrics = [
        (
            "M1",
            "Toàn bộ hội thoại học viên × AI tutor xảy ra NGAY TRONG GIỜ HỌC",
            pct(len(in_class), len(rows)),
            "Đếm bản ghi có `conversation_mode == 'in_class'` trên tổng 2.522 bản ghi. "
            "Không có bản ghi nào ở mode khác.",
            "Nhu cầu hỏi lại/bắt kịp phát sinh ngay trong buổi, không phải sau buổi — "
            "xác nhận đúng thời điểm của lát cắt (realtime), và loại bỏ phương án "
            "'tóm tắt sau buổi'.",
        ),
        (
            "M2",
            "Lượt trả lời của tutor KHÔNG ghi nguồn trích dẫn",
            pct(len(no_cite), len(tutors)),
            "Lọc `role == 'tutor'`, đếm bản ghi có `citations` rỗng hoặc `[]`.",
            "Gần một nửa câu trả lời không cho học viên đường nào kiểm lại — đây chính "
            "là chỗ sản phẩm của nhóm bắt buộc phải khác: mọi note/câu trả lời đều kèm "
            "mốc thời gian + nguyên văn đoạn nguồn.",
        ),
        (
            "M3",
            "Lượt tutor phải thừa nhận không tìm thấy căn cứ trong tài liệu",
            pct(len(not_found), len(tutors)),
            "Lọc `role == 'tutor'`, khớp regex "
            r"`không tìm thấy|không đề cập|không có trong|ngoài phạm vi|không thuộc|"
            r"không tìm được|chưa tìm thấy` trên trường `content`.",
            "Tình huống 'không có căn cứ' xảy ra thường xuyên, không phải ngoại lệ — "
            "nên lớp chỗ khó ① phải được xử lý bằng thiết kế, không phải bằng may mắn.",
        ),
        (
            "M4",
            "Tin nhắn học viên xin tóm tắt / xin lại nội dung",
            pct(len(recap), n_pairs),
            "Lọc `role == 'student'`, bỏ tiền tố metadata `(Trang N, đoạn được chọn: …)` "
            r"do VLearn tự chèn, khớp regex `tóm tắt|tóm lại|tổng hợp|ý chính|"
            r"nội dung chính|key takeaway`.",
            "Nhu cầu 'cho tôi lại nội dung vừa rồi' là loại yêu cầu phổ biến nhất đo được "
            "trong data — trùng đúng nhánh session_recap/catch_up của sản phẩm.",
        ),
        (
            "M5",
            "Tin nhắn học viên KHÔNG mang nội dung câu hỏi (tin cụt)",
            pct(len(terse), n_pairs),
            f"Sau khi bỏ tiền tố metadata, phần học viên tự gõ ngắn hơn {TERSE_MAX_LEN} "
            "ký tự (vd. 'hi', 'hả', 'd', 'ok', '123').",
            "Chứng minh lớp chỗ khó ② (mơ hồ) là tình huống thật, không phải nhóm tưởng "
            "tượng — sản phẩm phải hỏi lại chứ không được đoán.",
        ),
        (
            "M6",
            "Hội thoại mà học viên phải hỏi ≥2 lượt trong cùng một mạch",
            pct(len(multi_turn), len(per_conv)),
            "Nhóm bản ghi `role == 'student'` theo `conversation_id`, đếm hội thoại có "
            "≥2 lượt học viên.",
            "Một lần hỏi thường không đủ để bắt kịp — ủng hộ thiết kế giữ state theo "
            "cả buổi (rolling transcript) thay vì hỏi-đáp một lượt rời rạc.",
        ),
        (
            "M7",
            "Lượt tutor có chủ động kiểm tra lại xem học viên đã hiểu chưa",
            pct(len(checked), len(rows)),
            "Đếm bản ghi có `asked_check_question == 'True'`.",
            "Gần như bằng 0 — tutor hiện tại không đóng vòng phản hồi. Nhóm KHÔNG chọn "
            "giải bài này (ngoài lát cắt), nhưng ghi lại vì đây là ứng viên đã cân nhắc.",
        ),
        (
            "M8",
            "Trong số lượt được học viên chấm, tỉ lệ chấm 'không hữu ích'",
            pct(len(rated_down), len(rated)),
            "Lọc bản ghi có `rating` khác rỗng, đếm `rating == 'down'`.",
            "Mẫu nhỏ (chỉ 70/2.522 lượt được chấm) nên KHÔNG dùng làm bằng chứng chính "
            "— ghi lại kèm cảnh báo cỡ mẫu để minh bạch.",
        ),
    ]

    # --- Ví dụ nguyên văn (trích ngắn + mã hội thoại để trace) ---------------
    examples: list[tuple[str, str, str]] = []
    for label, pool, take in (
        ("Không có căn cứ (①)", not_found, 2),
        ("Xin tóm tắt / bắt kịp (M4)", recap, 2),
        ("Tin cụt, mơ hồ (②)", terse, 3),
        ("Báo không hiểu (②)", confused, 2),
    ):
        seen: set[str] = set()
        for r in pool:
            raw = r["content"] if r["role"] == "tutor" else student_text(r["content"])
            text = snippet(raw)
            if text.lower() in seen:
                continue
            seen.add(text.lower())
            examples.append((label, r["conversation_id"], text))
            if len([e for e in examples if e[0] == label]) >= take:
                break

    lines = [
        "# Bằng chứng đường B — đếm trên chatlog thật",
        "",
        "> Sinh bằng `evidence/mine_evidence.py` (chạy lại được để kiểm chứng).",
        f"> Nguồn: `data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv` — "
        f"{len(rows)} bản ghi = {n_pairs} cặp (học viên + tutor), "
        f"{len(per_conv)} hội thoại, đã ẩn danh toàn bộ ID.",
        "> Chỉ trích ≤160 ký tự kèm mã hội thoại — không dán nguyên văn dài (luật bảo mật data pack).",
        "",
        "## Bảng số liệu + cách đếm",
        "",
        "| # | Đo cái gì | Con số | Cách đếm (kiểm lại được) | Nói lên điều gì cho lát cắt |",
        "|---|---|---|---|---|",
    ]
    for mid, what, number, how, meaning in metrics:
        lines.append(
            f"| {mid} | {what} | **{number}** | {how.replace('|', '/')} | {meaning.replace('|', '/')} |"
        )

    lines += ["", "## Ví dụ nguyên văn (trích ngắn, có mã hội thoại để trace)", ""]
    for label, cid, text in examples:
        lines.append(f"- **[{label}]** `{cid}` — “{text}”")

    lines += [
        "",
        "## Giới hạn của phép đếm này (nói rõ để người chấm tự đánh giá)",
        "",
        "- M2/M3/M4/M5 dùng khớp từ khoá/regex nên có thể bỏ sót cách diễn đạt khác, "
        "và có thể đếm dư khi từ khoá xuất hiện trong ngữ cảnh khác. Regex được ghi "
        "nguyên văn ở bảng trên để người khác chỉnh và đếm lại.",
        "- M8 có cỡ mẫu quá nhỏ (chỉ 70/2.522 lượt được chấm) — không dùng làm bằng chứng chính.",
        "- Data pack là hội thoại với **AI tutor trên trang tài liệu**, không phải transcript "
        "buổi live. Vì vậy nó chứng minh *nhu cầu hỏi lại trong giờ* và *các lớp chỗ khó*, "
        "chứ chưa chứng minh trực tiếp hành vi trên bản transcript giọng nói — phần đó nhóm "
        "bù bằng khảo sát (đường A) và 6 transcript bài giảng thật.",
    ]

    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    for mid, what, number, _, _ in metrics:
        print(f"{mid}: {number:22} {what}")
    print(f"\nDa ghi: {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
