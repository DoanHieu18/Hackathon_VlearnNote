# Bằng chứng đường B — đếm trên chatlog thật

> Sinh bằng `evidence/mine_evidence.py` (chạy lại được để kiểm chứng).
> Nguồn: `data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv` — 2522 bản ghi = 1261 cặp (học viên + tutor), 585 hội thoại, đã ẩn danh toàn bộ ID.
> Chỉ trích ≤160 ký tự kèm mã hội thoại — không dán nguyên văn dài (luật bảo mật data pack).

## Bảng số liệu + cách đếm

| # | Đo cái gì | Con số | Cách đếm (kiểm lại được) | Nói lên điều gì cho lát cắt |
|---|---|---|---|---|
| M1 | Toàn bộ hội thoại học viên × AI tutor xảy ra NGAY TRONG GIỜ HỌC | **2522/2522 (100.0%)** | Đếm bản ghi có `conversation_mode == 'in_class'` trên tổng 2.522 bản ghi. Không có bản ghi nào ở mode khác. | Nhu cầu hỏi lại/bắt kịp phát sinh ngay trong buổi, không phải sau buổi — xác nhận đúng thời điểm của lát cắt (realtime), và loại bỏ phương án 'tóm tắt sau buổi'. |
| M2 | Lượt trả lời của tutor KHÔNG ghi nguồn trích dẫn | **582/1261 (46.2%)** | Lọc `role == 'tutor'`, đếm bản ghi có `citations` rỗng hoặc `[]`. | Gần một nửa câu trả lời không cho học viên đường nào kiểm lại — đây chính là chỗ sản phẩm của nhóm bắt buộc phải khác: mọi note/câu trả lời đều kèm mốc thời gian + nguyên văn đoạn nguồn. |
| M3 | Lượt tutor phải thừa nhận không tìm thấy căn cứ trong tài liệu | **189/1261 (15.0%)** | Lọc `role == 'tutor'`, khớp regex `không tìm thấy/không đề cập/không có trong/ngoài phạm vi/không thuộc/không tìm được/chưa tìm thấy` trên trường `content`. | Tình huống 'không có căn cứ' xảy ra thường xuyên, không phải ngoại lệ — nên lớp chỗ khó ① phải được xử lý bằng thiết kế, không phải bằng may mắn. |
| M4 | Tin nhắn học viên xin tóm tắt / xin lại nội dung | **135/1261 (10.7%)** | Lọc `role == 'student'`, bỏ tiền tố metadata `(Trang N, đoạn được chọn: …)` do VLearn tự chèn, khớp regex `tóm tắt/tóm lại/tổng hợp/ý chính/nội dung chính/key takeaway`. | Nhu cầu 'cho tôi lại nội dung vừa rồi' là loại yêu cầu phổ biến nhất đo được trong data — trùng đúng nhánh session_recap/catch_up của sản phẩm. |
| M5 | Tin nhắn học viên KHÔNG mang nội dung câu hỏi (tin cụt) | **152/1261 (12.1%)** | Sau khi bỏ tiền tố metadata, phần học viên tự gõ ngắn hơn 12 ký tự (vd. 'hi', 'hả', 'd', 'ok', '123'). | Chứng minh lớp chỗ khó ② (mơ hồ) là tình huống thật, không phải nhóm tưởng tượng — sản phẩm phải hỏi lại chứ không được đoán. |
| M6 | Hội thoại mà học viên phải hỏi ≥2 lượt trong cùng một mạch | **276/585 (47.2%)** | Nhóm bản ghi `role == 'student'` theo `conversation_id`, đếm hội thoại có ≥2 lượt học viên. | Một lần hỏi thường không đủ để bắt kịp — ủng hộ thiết kế giữ state theo cả buổi (rolling transcript) thay vì hỏi-đáp một lượt rời rạc. |
| M7 | Lượt tutor có chủ động kiểm tra lại xem học viên đã hiểu chưa | **3/2522 (0.1%)** | Đếm bản ghi có `asked_check_question == 'True'`. | Gần như bằng 0 — tutor hiện tại không đóng vòng phản hồi. Nhóm KHÔNG chọn giải bài này (ngoài lát cắt), nhưng ghi lại vì đây là ứng viên đã cân nhắc. |
| M8 | Trong số lượt được học viên chấm, tỉ lệ chấm 'không hữu ích' | **37/70 (52.9%)** | Lọc bản ghi có `rating` khác rỗng, đếm `rating == 'down'`. | Mẫu nhỏ (chỉ 70/2.522 lượt được chấm) nên KHÔNG dùng làm bằng chứng chính — ghi lại kèm cảnh báo cỡ mẫu để minh bạch. |

## Ví dụ nguyên văn (trích ngắn, có mã hội thoại để trace)

- **[Không có căn cứ (①)]** `C0001` — “Xin lỗi bạn, tôi không tìm thấy nội dung cụ thể cho slide 37 trong tài liệu hiện có. Bạn có thể cung cấp thêm thông tin hoặc tiêu đề của slide đó để tôi có thể …”
- **[Không có căn cứ (①)]** `C0002` — “Chào bạn, hiện tại tôi không tìm thấy tài liệu tổng hợp đầy đủ cho toàn bộ nội dung của Ngày 04 trong slide được cung cấp. Nếu bạn có thắc mắc về một khái niệm …”
- **[Xin tóm tắt / bắt kịp (M4)]** `C0001` — “tóm tắt nội dung chính trong slide này”
- **[Xin tóm tắt / bắt kịp (M4)]** `C0003` — “tóm tắt”
- **[Tin cụt, mơ hồ (②)]** `C0003` — “tóm tắt”
- **[Tin cụt, mơ hồ (②)]** `C0004` — “điêu toa”
- **[Tin cụt, mơ hồ (②)]** `C0009` — “heloo”
- **[Báo không hiểu (②)]** `C0063` — “TẠO QUIZ ĐỂ TÔI HIỂU RÕ VÀ ÔN LẠI TOÀN BỘ SLIDE NÀY”
- **[Báo không hiểu (②)]** `C0073` — “Giải thích chi tiết sự khác biệt giữa 4 cái keyword trên, trả lời cho một sinh viên SE chưa hiểu gì về AI”

## Giới hạn của phép đếm này (nói rõ để người chấm tự đánh giá)

- M2/M3/M4/M5 dùng khớp từ khoá/regex nên có thể bỏ sót cách diễn đạt khác, và có thể đếm dư khi từ khoá xuất hiện trong ngữ cảnh khác. Regex được ghi nguyên văn ở bảng trên để người khác chỉnh và đếm lại.
- M8 có cỡ mẫu quá nhỏ (chỉ 70/2.522 lượt được chấm) — không dùng làm bằng chứng chính.
- Data pack là hội thoại với **AI tutor trên trang tài liệu**, không phải transcript buổi live. Vì vậy nó chứng minh *nhu cầu hỏi lại trong giờ* và *các lớp chỗ khó*, chứ chưa chứng minh trực tiếp hành vi trên bản transcript giọng nói — phần đó nhóm bù bằng khảo sát (đường A) và 6 transcript bài giảng thật.
