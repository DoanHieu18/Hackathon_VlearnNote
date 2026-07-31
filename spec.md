# AI SPEC — VlearnNote: Catch-up Note Agent · Nhóm VlearnNote · Zone —
Hướng: [x] A — VLearn  [ ] B — Trợ lý Học viên  [ ] C — Làn mở
Loại: [ ] Tối ưu tính năng có sẵn  [x] Tính năng mới

## §1. User & Job
- **Job executor**: học viên đang trong buổi live (lý thuyết hoặc thực hành/lab), không phải "học viên nói chung".
- **Core JTBD**: bắt kịp lại nội dung vừa trôi qua trong buổi học khi bị mất tập trung hoặc đi chậm hơn tốc độ giảng, mà không phải hỏi bạn học hay chờ hết buổi. (Bỏ AI đi, việc "bắt kịp bài" vẫn tồn tại — học viên vẫn cần làm việc này bằng cách khác.)
- **Problem statement (không chữ AI)**: Học viên trong buổi live thường xuyên bị thiếu/sót thông tin (khái niệm giảng viên nói, bước thao tác thực hành, lưu ý quan trọng) vì giảng viên đi nhanh hoặc bản thân không ghi chú kịp; cách xử lý phổ biến nhất hiện nay là hỏi bạn học — một kênh không chính thức, không đáng tin cậy, và làm gián đoạn cả người hỏi lẫn người được hỏi.
- **Evidence — làm cả hai đường A và B**:

  **(A) Khảo sát người thật — log đầy đủ tại [`evidence/survey_log.md`](evidence/survey_log.md)** (bộ câu hỏi + toàn bộ 14 câu trả lời nguyên văn, người trả lời ẩn danh HV01–HV14):
  - Mức thiếu/sót thông tin buổi LÝ THUYẾT: trung bình **3,93/5**, **9/14 người chấm ≥4**; buổi THỰC HÀNH: trung bình **3,43/5**, 7/14 chấm ≥4.
  - Nguyên nhân số 1: **"Không ghi chú/theo kịp" — 10/14 (71%)**; "Giảng viên đi quá nhanh" 7/14 (50%).
  - Cách xử lý hiện tại phổ biến nhất: **"Hỏi bạn học" — 11/14 (79%)**, trong khi "Hỏi giảng viên/trợ giảng" chỉ 6/14 (43%) → học viên đang bù đắp bằng kênh không chính thức.
  - Hiệu quả của cách xử lý hiện tại chỉ **3,29/5**, **8/14 người chấm ≤3** → cách làm hiện tại không giải quyết được vấn đề.
  - ⚠️ **Chưa đạt chuẩn A đầy đủ (rubric yêu cầu ≥20 người)** — còn thiếu 6 phản hồi. Bộ câu hỏi giữ nguyên để gộp được số liệu khi thu thêm.

  **(B) Đếm trên dữ liệu — script tái lập được [`evidence/mine_evidence.py`](evidence/mine_evidence.py), báo cáo [`evidence/mining_report.md`](evidence/mining_report.md)** (nguồn: 2.522 bản ghi = 1.261 cặp hội thoại thật, 585 hội thoại):

  | # | Đo cái gì | Con số | Cách đếm |
  |---|---|---|---|
  | M1 | Hội thoại xảy ra **ngay trong giờ học** | **2.522/2.522 (100%)** | đếm `conversation_mode == 'in_class'` |
  | M2 | Lượt tutor **không ghi nguồn trích dẫn** | **582/1.261 (46,2%)** | lọc `role=='tutor'`, đếm `citations` rỗng hoặc `[]` |
  | M3 | Lượt tutor **phải thừa nhận không tìm thấy căn cứ** | **189/1.261 (15,0%)** | lọc `role=='tutor'`, khớp regex `không tìm thấy\|không đề cập\|không có trong\|ngoài phạm vi\|không thuộc\|không tìm được\|chưa tìm thấy` |
  | M4 | Học viên **xin tóm tắt / xin lại nội dung** | **135/1.261 (10,7%)** | bỏ tiền tố metadata `(Trang N, đoạn được chọn: …)`, khớp regex `tóm tắt\|tóm lại\|tổng hợp\|ý chính\|nội dung chính\|key takeaway` |
  | M5 | Tin nhắn học viên **không mang nội dung câu hỏi** | **152/1.261 (12,1%)** | phần học viên tự gõ < 12 ký tự (vd. "hi", "hả", "d") |
  | M6 | Hội thoại học viên **phải hỏi ≥2 lượt** mới xong | **276/585 (47,2%)** | nhóm theo `conversation_id`, đếm hội thoại có ≥2 lượt student |
  | M7 | Lượt tutor **chủ động kiểm tra học viên đã hiểu** | **3/2.522 (0,1%)** | đếm `asked_check_question == 'True'` |

  - **≥5 ví dụ nguyên văn** (trích ngắn kèm mã hội thoại để trace, xem đầy đủ trong `evidence/mining_report.md`): `C0004` "không tìm thấy thuật ngữ *điêu toa*…" · `C0006` học viên hỏi "xem bài tập thực hành lab day 2 chiều nay ở **đaau**" · `C0023` "Giải thích **biều** đồ **đc** bôi đỏ" · `C0038` "lấy văn bản trong trang 26 cho tôi" · tin cụt "hi" / "hả" / "d" lặp lại · "Tui không hiểu" · "bạn cho tôi biết đáp án bài lab 1 được không".
  - **Giới hạn đã ghi rõ**: M2–M5 dùng regex nên có thể bỏ sót/đếm dư — regex được in nguyên văn để người khác chỉnh và đếm lại; data pack là hội thoại với tutor **trên trang tài liệu**, không phải transcript giọng nói, nên chứng minh *nhu cầu hỏi lại trong giờ* và *các lớp chỗ khó*, chưa chứng minh trực tiếp hành vi trên transcript âm thanh.

## §2. Impact & quyết định chọn

| Ứng viên | Bao nhiêu người gặp | Tần suất | Tốn gì mỗi lần | Khả thi build trong sự kiện | Chọn? |
|---|---|---|---|---|---|
| **1. Note + catch-up Q&A agent (realtime, theo buổi)** | 10/14 (71%) báo "không ghi chú kịp"; 11/14 (79%) đang phải hỏi bạn học; M4 = 135 lượt xin lại nội dung | mỗi buổi live, nhiều lần/buổi | vài phút loay hoay + gián đoạn cả người hỏi lẫn người được hỏi; nặng hơn thì học sai/mất điểm | Có — 1 LangGraph agent + 1 lời gọi AI thật ở quyết định trung tâm, dùng đúng transcript được cấp | **CHỌN** |
| 2. Ghi hình lại toàn buổi (video) | 7/14 (50%) mong muốn | mỗi buổi | phải tua lại nguyên video, không tìm nhanh được đúng đoạn — không giải quyết được "bắt kịp trong lúc học" | Không — cần hạ tầng quay/lưu/stream video | Loại |
| 3. Hướng dẫn thực hành từng bước soạn sẵn | 12/14 (86%) mong muốn — **cao nhất** | mỗi bài lab | giảng viên tốn công soạn tay | Có, nhưng **không có quyết định AI nào** — là nội dung tĩnh giảng viên chuẩn bị trước | Loại |
| 4. Bắt tutor luôn ghi nguồn trích dẫn | M2 = 582/1.261 (46,2%) lượt không ghi nguồn | mỗi lượt hỏi | học viên không có đường kiểm lại, dễ tin sai | Có | Loại — là **tối ưu tutor có sẵn**, không phải job "bắt kịp bài đang trôi"; nhóm giữ tinh thần này thành **ràng buộc thiết kế** trong sản phẩm chính |
| 5. Nhắc học viên khi tutor không kiểm tra hiểu bài | M7 = 3/2.522 (0,1%) lượt có kiểm tra hiểu | mỗi lượt | học viên tưởng đã hiểu | Có | Loại — pain chưa được xác nhận từ phía học viên (không ai trong 14 người nêu), chỉ là quan sát từ log |

- **Ứng viên đã loại + vì sao**: (2) không khả thi kỹ thuật trong 1,5 ngày **và** không giải quyết được đúng thời điểm; (3) mong muốn cao nhất nhưng không có quyết định AI nào — nếu chọn thì bài này thành soạn tài liệu; (4) thuộc loại tối ưu tính năng có sẵn, lệch job — nhưng bài học từ nó được giữ lại thành ràng buộc "mọi output phải kèm nguồn"; (5) thiếu bằng chứng từ phía người dùng.
- **Ứng viên chọn + vì sao (bằng số)**: là ứng viên duy nhất **đồng thời** có (i) bằng chứng hai chiều — B chứng minh vấn đề tồn tại (M1 100% hỏi trong giờ, M6 47,2% phải hỏi ≥2 lượt), A chứng minh người dùng muốn giải (71% nêu đúng nguyên nhân, 79% đang tự bù bằng kênh không chính thức, hiệu quả chỉ 3,29/5), (ii) một quyết định AI thật ở lõi, (iii) build và demo được trong khung thời gian sự kiện.

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
- **Golden set**: `eval/golden_set.json` — **35 case**, phủ đủ 4 lớp chỗ khó (① 8 case · ② 7 · ③ 7 · ④ 4) + 7 case thường + 2 case hiếm. **29/35 case bắt nguồn từ quan sát thực tế**: 14 case giữ nguyên văn tin nhắn học viên trong `data/vlearn-pack/chatlog` (2.522 dòng thật — giữ cả lỗi chính tả "biều đồ"/"đaau", thiếu dấu "nop btap o dau", slang "hôm nay học gì z", tin cụt "hi"/"hả"/"d"), 3 case từ tình huống thật trong chatlog, 8 case trích đoạn giảng thật trong `transcript/`, 1 case từ số mining (166/1.261 lượt tutor thật phải trả "không tìm thấy" = 13,2%), 3 case từ lúc nhóm tự dùng thử.
- **Quality bar** (chốt tại thời điểm commit spec, **giữ nguyên, không hạ**): *"Đạt khi ≥80% case classify_segment đúng is_note_worthy + đúng label, VÀ 100% case lớp ① (nguồn sự thật) không được bịa thêm nội dung ngoài input."*
- **Kết quả các lượt chạy** (runner: `eval/run_eval.py`, model `gemini-2.5-flash`, gọi AI thật):

  | Lượt | Đo được | Tổng thể | classify_segment (bar ≥80%) | Lớp ① (bar 100%) | Kết luận |
  |---|---|---|---|---|---|
  | **001** — lượt đo đầu, đầy đủ | 35/35 | **29/35 = 82,9%** | 11/13 = **84,6%** ✅ | **7/8** ❌ | **Chưa đạt bar** — điều kiện cứng thất bại |
  | 002 — sau fix ①, chạy dở | 23/35 | không dùng | — | **8/8** ✅ | Fix ① có tác dụng, nhưng lộ regression lớp ② |
  | 003 — hết quota ngày | 6/35 | không dùng | — | — | Không hợp lệ, giữ lại để minh bạch |

  Chi tiết đủ mọi case kể cả fail: `eval/run_001.md` (số liệu chính thức), `eval/run_002.md`, `eval/run_003.md`.

- **Phân tích khoảng cách với bar** (nội dung slide 4 khi demo):
  1. **Failure đau nhất — false negative "chưa thấy thầy nhắc"** (case `C1_08`, `C4_04`): `route_intent` trích keyword đã diễn giải lại ("chạy server") trong khi `search_transcript` chỉ khớp chuỗi nguyên văn ("Chạy bằng lệnh: uvicorn main:app") → tool trả `not_found` → agent trung thực trả lời "chưa thấy" **dù giảng viên ĐÃ nói**. Nguy hiểm nhất trong cả sản phẩm: học viên tưởng mình không bỏ sót gì, trong khi thực ra có. Đã sửa: `search_transcript` thêm tầng khớp theo token nội dung (bỏ dấu, bỏ stopword) và tầng `unconfirmed` trả kèm đoạn gần nhất nhưng ghi rõ "chưa xác nhận khớp" — giữ nguyên guardrail chống bịa. Lượt 002 xác nhận lớp ① lên 8/8.
  2. **Regression do sửa prompt** (lượt 002, case `C2_02` "hả", `C2_03` "d"): siết prompt route làm tin cụt bị xếp thành `catch_up` rồi trả về một đoạn transcript bất kỳ — đúng kiểu "sửa chỗ này vỡ chỗ kia". Đã xử lý bằng cách thêm intent `unclear` + node `ask_clarify` (hỏi lại thay vì đoán — HAX G10), thay vì nhồi tiếp vào prompt.
  3. **Lệch định nghĩa nhãn** (case `S04`, `S06`): ranh giới `example` vs `action_item` chưa được định nghĩa rõ trong spec nên nhóm và model chấm khác nhau. Đã viết rõ định nghĩa trong prompt (số liệu/minh hoạ = example; việc học viên phải tự làm = action_item) và ghi vào Changelog — **không đổi % của bar**.
  4. **Việc còn phải làm**: chạy lại trọn bộ 35 case sau 2 fix trên khi quota reset để có lượt đo đầy đủ thứ hai.

## §8. Phân công & kế hoạch
- **Phân công có tên** (xem thêm `PHAN-CONG.md`):
  - Phương — Backend + LangGraph Agent (`backend/agent/`, `backend/main.py`)
  - Hiếu — Frontend + UX/Validation (`frontend/src/App.jsx`, `validation/`)
  - Hưng — Spec + Evidence + Eval (`spec.md`, `eval/golden_set.json`, khảo sát)
- **Willing users**: ✅ **Đã chốt 5 người dùng thật ngoài nhóm đồng ý thử nghiệm (hoàn thành CP1/CP4)**:
  1. Nguyễn Quý Dương (`2A202601642`)
  2. Nguyễn Hoàng Khôi (`202601383`)
  3. Nguyễn Công Hùng (`2A202601071`)
  4. Đinh Tuấn Minh (`2A202601892`)
  5. Phạm Trung Hiếu (`2A202601834`)
- **Kế hoạch validation CP5**: 5 người ngoài nhóm (đã chốt ở trên), phiên 10 phút/người, giao task thật ("dùng thử catch-up Q&A và tương tác với Agent Note khi bị mất tập trung 5 phút trong buổi live"), 3 câu hỏi chuẩn theo guide §4.2, ghi log đầy đủ tại [`validation/feedback_log.md`](validation/feedback_log.md).
- **Multi-prototype**: chưa làm — nếu kịp, thử 2 phương án ở trục "mức automation của note" (auto-note luôn vs. luôn hỏi xác nhận trước khi ghi) để có bằng chứng chọn Conditional.

### §8b. Nhóm còn thiếu gì (tự soát tại CP4)

| # | Còn thiếu / đang vướng | Mức | Cần hỗ trợ gì |
|---|---|---|---|
| 1 | **Khảo sát mới 14/20 người** → chưa đạt chuẩn A | Cao | Xin TA cách phát khảo sát nhanh trong giờ nghỉ để đủ ≥20 (bộ câu hỏi đã có, chỉ thiếu người) |
| 2 | ~~Chưa có ≥3 willing user có tên~~ | ✅ **Đã xong** | Đã chốt đủ 5 người dùng có tên & mã HV (xem §8) |
| 3 | **Quota Gemini free tier 20 request/ngày/model** — chỉ chạy được 1 lượt đo đầy đủ (35 case ≈ 45 lời gọi), 2 lượt sau chết giữa đường | Cao | Xin API key khoá học có quota cao hơn, hoặc xác nhận việc báo cáo kết quả theo "số case đo được" là chấp nhận được |
| 4 | **Chưa nối STT thật** — nguồn transcript vẫn là `MOCK_TRANSCRIPTS` phát theo nhịp | Trung bình | Hỏi TA: mức Mock này có đủ cho rubric R5 không, hay nên đọc trực tiếp từ 6 transcript trong data pack cho gần thật hơn |
| 5 | **Chưa có vòng validation với người thật** | ✅ **Đang thực hiện** | Đã chốt 5 tester có tên & tạo file log `validation/feedback_log.md` |
| 6 | **Chưa chạy multi-prototype** so 2 trục thiết kế | Thấp | Hỏi TA hạng mục này có bắt buộc hay chỉ khuyến khích |
| 7 | **Chưa có `demo-slides.pdf`** và chưa dry run bấm giờ | Trung bình | — (nhóm tự làm trước CP5) |

## §9. Changelog
| Thời điểm | Đổi gì | Vì sao |
|---|---|---|
| Bản đầu | Lát cắt gốc: chỉ note tự động thụ động | — |
| Cập nhật | Bổ sung nhánh catch-up Q&A + session_recap, mở rộng job sang "mất tập trung/không theo kịp" | Theo yêu cầu nhóm + khớp số liệu khảo sát (71% "không ghi chú kịp", kênh xử lý phổ biến nhất là "hỏi bạn học" — cho thấy cần một kênh hỏi-đáp chính thức) |
| Cập nhật | Dùng LangGraph StateGraph thay vì 1 vòng ReAct đơn | Cần state chia sẻ liên tục giữa luồng ingest transcript và luồng trả lời câu hỏi chen ngang bất kỳ lúc nào |
| Sau lượt đo 001 | `search_transcript` thêm tầng khớp theo token nội dung (bỏ dấu/stopword) + status `unconfirmed` | Case `C1_08` và `C4_04`: khớp chuỗi nguyên văn làm agent trả "chưa thấy thầy nhắc" dù giảng viên ĐÃ nói — failure đau nhất, làm thất bại điều kiện cứng lớp ① (7/8) |
| Sau lượt đo 001 | Viết rõ định nghĩa nhãn `example` vs `action_item` trong `CLASSIFY_SEGMENT_PROMPT`; sửa kỳ vọng case `S06` thành `action_item` | Case `S04`/`S06`: định nghĩa nhãn trong spec chưa phân định rõ nên nhóm và model chấm khác nhau. **Quality bar % không đổi** — chỉ làm rõ định nghĩa đang mơ hồ, đúng hướng dẫn guide §4.1 |
| Sau lượt đo 002 | Thêm intent `unclear` + node `ask_clarify` vào `question_graph` | Regression lộ ra ở lượt 002: siết prompt route làm tin cụt thật ("hả", "d" — lấy từ chatlog) bị xếp thành `catch_up` rồi trả về đoạn transcript bất kỳ. Hỏi lại đúng tinh thần HAX G10 thay vì đoán |
| Sau lượt đo 003 | `run_eval.py` tách "CHƯA ĐO ĐƯỢC (hết quota)" khỏi "FAIL"; `llm.py` đặt `max_retries=0` để lớp xoay vòng key tự xử lý | Lượt 003 chỉ đo được 6/35 vì hết quota ngày, nếu tính chung vào mẫu số sẽ ra 17,1% — con số gây hiểu nhầm hoàn toàn về chất lượng sản phẩm |
| Sau vòng Validation (CP5) | Cô đọng câu trả lời Catch-up Q&A dưới 3 dòng + đổi màu viền NoteCard đã bấm "Xác nhận" | Theo phản hồi nguyên văn từ 5 người dùng thử nghiệm (`validation/feedback_log.md`): user cần đọc lướt nhanh 5s trong giờ học live |
