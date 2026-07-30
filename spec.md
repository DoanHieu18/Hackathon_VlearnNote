# AI SPEC — VlearnNote: Catch-up Note Agent · Nhóm VlearnNote · Zone —
Hướng: [x] A — VLearn  [ ] B — Trợ lý Học viên  [ ] C — Làn mở
Loại: [ ] Tối ưu tính năng có sẵn  [x] Tính năng mới

## §1. User & Job
- **Job executor**: học viên đang trong buổi live (lý thuyết hoặc thực hành/lab), không phải "học viên nói chung".
- **Core JTBD**: bắt kịp lại nội dung vừa trôi qua trong buổi học khi bị mất tập trung hoặc đi chậm hơn tốc độ giảng, mà không phải hỏi bạn học hay chờ hết buổi. (Bỏ AI đi, việc "bắt kịp bài" vẫn tồn tại — học viên vẫn cần làm việc này bằng cách khác.)
- **Problem statement (không chữ AI)**: Học viên trong buổi live thường xuyên bị thiếu/sót thông tin (khái niệm giảng viên nói, bước thao tác thực hành, lưu ý quan trọng) vì giảng viên đi nhanh hoặc bản thân không ghi chú kịp; cách xử lý phổ biến nhất hiện nay là hỏi bạn học — một kênh không chính thức, không đáng tin cậy, và làm gián đoạn cả người hỏi lẫn người được hỏi.
- **Evidence**:
  - **(A) Khảo sát n=14** (học viên khoá, câu hỏi về "lần gần nhất" — xem file khảo sát gốc, không đưa vào repo theo luật bảo mật): mức độ thiếu thông tin buổi LÝ THUYẾT trung bình **3.86/5**, buổi THỰC HÀNH **3.5/5**. Nguyên nhân "Không ghi chú kịp/theo kịp" chiếm **10/14 (71%)**; "Giảng viên đi quá nhanh" **7/14 (50%)**. Cách xử lý phổ biến nhất khi thiếu thông tin: "Hỏi bạn học" (kênh không chính thức, không phải giải pháp có chủ đích). Mong muốn hỗ trợ nhiều nhất: "kênh hỏi đáp sau giờ học" 5/14 (36%), "ghi hình lại buổi học" 7/14 (50%).
    - ⚠️ **Chưa đạt chuẩn A đầy đủ của rubric (cần ≥20 người ngoài nhóm)** — kế hoạch: bổ sung ≥6 phản hồi nữa trước CP4, giữ nguyên bộ câu hỏi để có thể gộp số liệu.
  - **(B) Mining transcript thật** (`data/vlearn-pack/transcript/`, 6 buổi, ~700 đoạn có mã `[Txx-NNN]`): đọc mẫu 30-50 đoạn cho thấy 3 loại tín hiệu lặp lại có thể đếm được — (i) định nghĩa/khái niệm giảng viên phát biểu tường minh (vd. `[T01-011]` phân biệt product manager/product owner, `[T04-015]` phân tầng AI/ML/DL/GenAI), (ii) câu nhắc nhở kiểu cảnh báo/quan trọng không kèm nội dung cụ thể theo sau ngay (vd. dạng câu "cái này quan trọng đấy" — rủi ro nếu AI note nhầm), (iii) đoạn hoạt động lớp/hành chính bị lẫn giữa nội dung học thuật (vd. `[T02-002]`) — nếu ghi chú không phân biệt được sẽ tạo note rác.
  - **≥5 ví dụ nguyên văn** (trích ngắn, có mã trace): `[T01-011]`, `[T01-016]`, `[T04-015]`, `[T05-006]`, `[T01-030]` — xem `eval/golden_set.json` để đối chiếu đầy đủ.

## §2. Impact & quyết định chọn

| Ứng viên | Bao nhiêu người gặp | Tần suất | Tốn gì mỗi lần | Khả thi build trong sự kiện | Chọn? |
|---|---|---|---|---|---|
| **Note + catch-up Q&A agent (realtime, theo buổi)** | 10/14 (71%) báo "không ghi chú kịp" | mỗi buổi live | vài phút loay hoay + phải hỏi bạn học (kênh không chính thức, không đảm bảo đúng) | Có — dùng đúng data transcript + 1 LangGraph agent, 1 lời gọi AI thật ở quyết định trung tâm | **Chọn** |
| Ghi hình lại toàn buổi (video) | 7/14 (50%) mong muốn | mỗi buổi | phải tua/xem lại nguyên video mất nhiều thời gian, không tìm nhanh đúng đoạn | Không — cần hạ tầng quay/lưu/stream video, ngoài phạm vi 1.5 ngày | Loại — không build nổi + không giải quyết "nhanh" |
| Hướng dẫn thực hành từng bước soạn sẵn | 12/14 (86%) mong muốn — cao nhất | mỗi bài lab | giảng viên tốn công soạn tay | Có nhưng không cần AI quyết định gì — là nội dung tĩnh giảng viên chuẩn bị trước | Loại — không phải "lát cắt AI", thuộc phạm vi chuẩn bị bài giảng |

- **Ứng viên đã loại + vì sao**: xem bảng trên — 2 ứng viên loại vì (1) không khả thi kỹ thuật trong khung 1.5 ngày, (2) không phải quyết định AI mà là nội dung tĩnh.
- **Ứng viên chọn + vì sao (bằng số)**: pain có bằng chứng mạnh nhất (71% nguyên nhân "không ghi chú kịp"), và là ứng viên duy nhất có thể build với 1 lời gọi AI thật trên đúng data pack được cấp.

## §3. Giải pháp tương tự đã nghiên cứu
- **NotebookLM (Google)**: flow — người dùng nạp nguồn tài liệu, hỏi, NotebookLM luôn trả lời kèm trích dẫn nguồn ngay cạnh câu trả lời. Đáng học: trích dẫn gắn liền với câu trả lời, không tách rời. Đáng né: NotebookLM không xử lý luồng realtime (nguồn tĩnh, nạp trước) — khác lát cắt của mình vì transcript của mình sinh ra liên tục trong lúc học. Mình khác: nguồn (transcript) tích luỹ dần theo thời gian thực, câu trả lời phải giới hạn trong "những gì đã giảng tới thời điểm hỏi", không phải toàn bộ tài liệu.
- **ChatGPT Study Mode**: flow — đặt câu hỏi, AI hướng dẫn từng bước thay vì đưa đáp án luôn. Đáng học: chủ động hỏi lại khi câu hỏi mơ hồ thay vì đoán. Đáng né: không có khái niệm "nguồn sự thật" cố định — trả lời từ kiến thức chung của mô hình, dễ lẫn giữa "đúng theo bài giảng" và "đúng theo kiến thức chung". Mình khác: câu trả lời BẮT BUỘC bám transcript của buổi, từ chối nếu chủ đề chưa được giảng — không dùng kiến thức nền ngoài transcript.
- **Zoom/Meet AI meeting notes**: flow — tự động tóm tắt toàn bộ cuộc họp sau khi kết thúc. Đáng học: phân loại được "action item" riêng khỏi nội dung chung. Đáng né: chỉ có bản tóm tắt SAU buổi, không giúp học viên bắt kịp NGAY trong lúc đang học. Mình khác: note sinh ra theo thời gian thực trong buổi, và có kênh hỏi-đáp chủ động ngay lúc đó — không đợi đến cuối.

## §4. Thiết kế
- **Lát cắt MỘT CÂU**: Học viên đang trong buổi live (lý thuyết hoặc thực hành) bị mất tập trung/không kịp theo · muốn bắt kịp lại nội dung đã trôi qua · AI quyết định đoạn vừa giảng có đáng ghi note hay không (và khi được hỏi, trả lời có trích dẫn đúng đoạn transcript, không suy diễn thêm) · kết quả là note realtime + câu trả lời catch-up giúp học viên quay lại theo dõi bài mà không bị lụt thêm.
- **Non-goals** (≥3, bản build không vi phạm):
  1. Không dịch/tóm tắt toàn bộ bài giảng thành slide đầy đủ (chỉ note các đơn vị kiến thức rời rạc đáng chú ý).
  2. Không trả lời hộ bài tập hoặc câu hỏi ngoài nội dung buổi học đang diễn ra (route "out_of_scope" từ chối và trỏ kênh đúng).
  3. Không tự sửa/diễn giải lại nếu nghi ngờ giảng viên nói sai — chỉ ghi đúng những gì được nói.
  4. Không xử lý audio thật/STT trong phạm vi hackathon — dùng transcript giả lập nạp sẵn (ghi rõ ở mức prototype bên dưới).
- **Mức prototype nhắm tới**: [x] Sketch [x] Mock (lõi AI thật) [ ] Working.
  - Thật: lời gọi LLM thật ở `classify_segment_node` và `route_intent_node`/`catch_up_qa_node` (`backend/agent/graph.py`), dùng LangGraph StateGraph, có structured output + timeout guardrail.
  - Mock: nguồn transcript (`MOCK_TRANSCRIPTS` trong `backend/main.py`) phát theo nhịp giả lập buổi học thật — chưa nối pipeline STT từ mic thật.
- **Automation**: [x] Conditional — lý do theo cost-of-error: đa số đoạn giảng là lành (note sai một đoạn ví dụ ngoài lề không gây hậu quả lớn, học viên tự sửa/xoá được ngay — HAX G9), nhưng một số ít case hiểm (mơ hồ, ngoài phạm vi, đặc thù domain như code/công thức) sai thì đắt — học sai kiến thức hoặc chạy sai code. Vì vậy: AI tự note khi tín hiệu rõ, chuyển sang "nháp chờ xác nhận" khi mơ hồ, và từ chối lịch sự khi ngoài phạm vi — không tự quyết một mình ở vùng rủi ro cao.

### §4b. Nguyên tắc đã áp dụng (≥4 — HAX/PAIR)

| Nguyên tắc | Áp cụ thể vào đâu trong prototype |
|---|---|
| G2 — Làm rõ nó làm tốt đến đâu | Banner `.scope-banner` trong `App.jsx`: nói rõ AI note tự động các đoạn có tín hiệu quan trọng, không thay thế ghi chép, không giải bài tập, không xử lý logistics |
| G10 — Thu hẹp phạm vi khi nghi ngờ | `classify_segment_node`: đoạn mơ hồ → `label="ambiguous"`, `is_note_worthy=false` — không tạo note liều; `catch_up_qa`: khi tool trả `status="not_found"`, câu trả lời phải nói rõ chưa thấy, không bịa |
| G9 — Sửa dễ dàng | Mỗi `NoteCard` trong `App.jsx` có nút Sửa/Xoá ngay tại chỗ, không cần rời màn hình |
| G11 — Giải thích vì sao | Mỗi note kèm `timestamp_s` + `source` (nguyên văn đoạn transcript gốc) để học viên trace lại; câu trả lời catch-up luôn kèm mốc thời gian/người nói khi trích dẫn (`CATCH_UP_ANSWER_PROMPT`) |
| PAIR — Errors + Graceful Failure | Phân biệt rõ 2 loại lỗi: "chưa từng được giảng" (route trả lời trung thực) vs "ngoài phạm vi tính năng" (`out_of_scope_node` từ chối + gợi ý kênh khác) — mỗi loại một đường lui riêng |

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản (≥8)

| # | Tình huống cụ thể | Lớp | Hành vi mong muốn | Nguyên tắc áp |
|---|---|---|---|---|
| 1 | Giảng viên nói ý kiến cá nhân ("mình thấy người miền Nam mở hơn") lẫn trong bài giảng | ① Nguồn sự thật | Không note như "definition" kiến thức chính khoá — tránh học viên học nhầm ý kiến thành sự thật | G10 |
| 2 | Giảng viên nói "chắc chắn ra thi đấy" nhưng không nói rõ nội dung gì | ①/④ | Note đúng nguyên văn cam kết, không tự suy đoán nội dung sẽ thi | G11 |
| 3 | Học viên hỏi về chủ đề chưa từng được giảng trong buổi (vd hỏi về RAG khi chưa dạy) | ① | Trả lời trung thực "chưa thấy nhắc trong buổi này", tuyệt đối không tự bịa bằng kiến thức nền của LLM | G10 |
| 4 | Mất kết nối WebSocket giữa chừng, một đoạn transcript bị thiếu | ① | Không tự lấp khoảng trống bằng suy đoán — báo rõ có đoạn bị thiếu | G10 |
| 5 | Câu giảng viên nói lửng, không kèm nội dung ("cái này quan trọng đấy") | ② Mơ hồ | `is_note_worthy=false`, label `ambiguous`, chờ đoạn kế tiếp thay vì đoán | G10 |
| 6 | Đoạn "Hoạt động lớp" (hành chính) lẫn giữa nội dung học thuật | ② | Không note thành kiến thức — phân biệt nội dung học vs. việc vặt lớp học | G10 |
| 7 | Học viên nhờ "AI ơi giải hộ bài tập này" giữa giờ | ③ Ngoài phạm vi | Từ chối, trỏ đúng kênh (tutor Q&A/giảng viên), không tự trả lời nội dung bài tập | route `out_of_scope` |
| 8 | Học viên hỏi "deadline nộp bài lab tuần này là ngày nào" | ③ | Không tự suy đoán deadline — trỏ về kênh thông báo chính thức | route `out_of_scope` |
| 9 | Giảng viên phân biệt Product Manager vs Product Owner — nhầm 2 vai trò là lỗi domain nghiêm trọng | ④ Đặc thù domain | Note giữ đúng chiều phân biệt, không gộp chung 2 khái niệm | G11 |
| 10 | Buổi thực hành: giảng viên đọc/gõ code hoặc công thức (`(a*b)**0.5`) | ④ | Giữ NGUYÊN VĂN từng ký tự trong note, không diễn giải lại — sai 1 ký tự khiến học viên chạy sai | prompt `CLASSIFY_SEGMENT_PROMPT` |

## §6. Bốn đường đi của trải nghiệm
- **Happy path**: giảng viên nói một định nghĩa rõ ràng → `classify_segment_node` trả `is_note_worthy=true` → note xuất hiện realtime ở panel "Agent Notes", học viên bấm Xác nhận.
- **Low-confidence (②)**: câu lửng/hoạt động lớp → không tạo note, hoặc tạo note ở trạng thái "nháp — chờ xác nhận" chờ ngữ cảnh tiếp theo.
- **Failure/không căn cứ (①)**: học viên hỏi catch-up về chủ đề chưa giảng → `catch_up_qa_node` nhận `status="not_found"` từ tool → trả lời trung thực, không bịa.
- **Correction (user sửa)**: học viên bấm "Sửa" trên bất kỳ note nào → chỉnh trực tiếp trong `NoteCard`, lưu lại — không cần thao tác nào khác.
- **Khi bị đòi ngoài phạm vi (③)**: câu hỏi bài tập/logistics → `route_intent_node` phân loại `out_of_scope` → `out_of_scope_node` từ chối lịch sự + gợi ý kênh đúng.
- **Case đặc thù domain (④)**: đoạn code/công thức trong buổi thực hành → giữ nguyên văn trong `summary`, không diễn giải lại.

## §7. Kiểm thử
- **Chiều chất lượng + định nghĩa kiểm chứng được**:
  1. *Đúng có-căn-cứ*: mọi note/câu trả lời phải trace được về đúng mã đoạn transcript hoặc trạng thái "không tìm thấy" — pass/fail.
  2. *Đúng nhãn phân loại*: label (definition/example/exam_warning/action_item/ambiguous) khớp kỳ vọng trong golden set — pass/fail.
  3. *Không bịa thêm*: đối chiếu nội dung note/câu trả lời với transcript gốc, không có câu/ý nằm ngoài input — pass/fail, người thứ hai chấm độc lập.
- **Golden set**: `eval/golden_set.json` — hiện có **22 case** (9 thường, 2 hiếm, 8 case theo 4 lớp chỗ khó ×2, 3 case route Q&A thường), ≥10 case lấy trực tiếp từ 6 transcript thật (`data/vlearn-pack/transcript/`). Cần bổ sung thêm ≥8 case (mở rộng lên 30+ theo khuyến nghị) trước CP4 nếu dùng promptfoo.
- **Quality bar** (chốt tại thời điểm commit spec, giữ nguyên sau đó): *"Đạt khi ≥80% case classify_segment đúng is_note_worthy + đúng label, VÀ 100% case lớp ① (nguồn sự thật) không được bịa thêm nội dung ngoài input."*
- **Kết quả chạy**: chưa chạy lượt đầu — cần `GEMINI_API_KEY` thật (xem `backend/.env.example`, lấy từ Google AI Studio). Kế hoạch: chạy trọn `eval/golden_set.json` qua `ingest_graph`/`question_graph` trước CP3, ghi bảng % vào `eval/run_001.md`.

## §8. Phân công & kế hoạch
- **Phân công có tên** (xem thêm `PHAN-CONG.md`):
  - Phương — Backend + LangGraph Agent (`backend/agent/`, `backend/main.py`)
  - Hiếu — Frontend + UX/Validation (`frontend/src/App.jsx`, `validation/`)
  - Hưng — Spec + Evidence + Eval (`spec.md`, `eval/golden_set.json`, khảo sát)
- **Willing users**: cần bổ sung ≥3 tên cụ thể trước CP1 (chưa có trong bản này — TODO trước khi demo).
- **Kế hoạch validation CP5**: ≥5 người ngoài nhóm, phiên 10 phút/người, giao task thật ("dùng thử catch-up khi bị mất tập trung 5 phút"), 3 câu hỏi chuẩn theo guide §4.2, log tại `validation/`.
- **Multi-prototype**: chưa làm — nếu kịp giữa CP2-CP3, đề xuất thử 2 phương án ở trục "mức automation của note" (auto-note luôn vs. luôn hỏi xác nhận trước khi ghi) để có bằng chứng chọn Conditional.

## §9. Changelog
| Thời điểm | Đổi gì | Vì sao |
|---|---|---|
| Bản đầu | Lát cắt gốc: chỉ note tự động thụ động | — |
| Cập nhật | Bổ sung nhánh catch-up Q&A + session_recap, mở rộng job sang "mất tập trung/không theo kịp" | Theo yêu cầu nhóm + khớp số liệu khảo sát (71% "không ghi chú kịp", kênh xử lý phổ biến nhất là "hỏi bạn học" — cho thấy cần một kênh hỏi-đáp chính thức) |
| Cập nhật | Dùng LangGraph StateGraph thay vì 1 vòng ReAct đơn | Cần state chia sẻ liên tục giữa luồng ingest transcript và luồng trả lời câu hỏi chen ngang bất kỳ lúc nào |
