# Phân công — Nhóm VlearnNote

Lát cắt: học viên bị mất tập trung/không kịp theo trong buổi live (lý thuyết hoặc thực hành)
muốn bắt kịp lại nội dung đã trôi qua bằng note tự động realtime + hỏi-đáp có trích dẫn,
không phải hỏi bạn học hay đợi hết buổi.

| Tên | Role | Việc chính | File/thư mục phụ trách |
|---|---|---|---|
| **Phương** | Backend + LangGraph Agent | Dựng StateGraph (ingest → classify → note_writer / route_intent → catch_up_qa), nối AI thật vào WebSocket, guardrail (timeout, không bịa nguồn) | `codebase/backend/` |
| **Hiếu** | Frontend + UX | Panel note có xác nhận/sửa/xoá (G9), banner phạm vi (G2), khung hỏi-đáp catch-up | `codebase/frontend/` |
| **Hưng** | Spec + Evidence + Eval | Hoàn thiện `spec.md` §1-§9, mining transcript + khảo sát, xây golden set ≥20 case, chấm quality bar | `spec.md`, `eval/` |
| **Hoàng** | Validation + User Testing | Quản lý 5 Willing Users, thu thập log phỏng vấn 5 người dùng thật, cập nhật Changelog & Slide 5 | `validation/` |

Ai cũng phải giải thích được phần có tên mình (vibe-coding rule — kiểm tra ngẫu nhiên tại CP5).
