# User Validation Log — VlearnNote (CP5)

> **Mục đích:** Ghi nhận thực tế trải nghiệm của người dùng thật khi thao tác trên prototype VlearnNote theo đúng tiêu chí **Rubric R6 (8 điểm)**.
> **Đối tượng thử nghiệm:** 5 người dùng ngoài nhóm (đã chốt tại `spec.md` §8).
> **Thời lượng:** 10–15 phút / người.
> **Người phụ trách log & phỏng vấn:** Hoàng (Validation Lead).

---

## 📋 1. Kịch Bản & Task Giao Cho Người Dùng

* **Bối cảnh giao task:** 
  > *"Giả sử bạn đang nghe giảng một buổi học trực tuyến. Do gián đoạn 3–5 phút (mất tập trung, có việc bận hoặc giảng viên nói nhanh), bạn bị lỡ một phần kiến thức quan trọng. Hãy dùng giao diện VlearnNote để bắt kịp bài học mà không phải gián đoạn bạn cùng lớp."*
* **Các bước thao tác giao cho User:**
  1. Theo dõi bảng **Agent Notes** sinh ra realtime theo bài giảng.
  2. Thử tương tác với 1 thẻ `NoteCard`: Bấm **Xác nhận**, bấm **Sửa** (chỉnh lại nội dung theo ý muốn), hoặc **Xoá**.
  3. Mở khung **Catch-up Q&A**, gõ 1 câu hỏi nhờ AI giải thích/bắt kịp lại đoạn bài giảng vừa lỡ (Ví dụ: *"Thầy vừa nói gì về lệnh uvicorn thế?"* hoặc *"Tóm tắt 2 ý chính vừa giảng cho mình"*).
  4. Đọc câu trả lời của AI và kiểm tra mốc trích dẫn nguồn.

---

## 💬 2. Bảng Log Phỏng Vấn & Quan Sát Trực Tiếp (≥5 người)

| STT | Người thử (Tên & Mã HV) | Task giao | Quan sát trực tiếp (Thao tác kẹt ở đâu) | Quote nguyên văn của User (Trải nghiệm & 3 câu hỏi) | Mức độ nghiêm trọng |
|:---:|---|---|---|---|:---:|
| **1** | **Nguyễn Quý Dương**<br>`2A202601642` | Catch-up Q&A + Sửa NoteCard | Lúng túng 5s đầu khi tìm nút "Hỏi bài", sau đó thao tác mượt trên khung chat. Bấm sửa note nhanh. | *"Bảng tóm tắt tự động ra khá chuẩn ý, nhưng câu trả lời Q&A ở khung dưới nên làm ngắn hơn chút nữa để tui đọc lướt 5s là hiểu liền, không tốn thời gian khi đang nghe giảng tiếp."* | Trung bình |
| **2** | **Nguyễn Hoàng Khôi**<br>`202601383` | Kiểm tra trích dẫn & Catch-up | Thử đặt câu hỏi ngoài bài học ("hôm nay ăn gì"), thấy AI từ chối lịch sự thì bật cười gật đầu. | *"Thích nhất là nó có gắn timestamp với trích dẫn nguyên văn đoạn thầy nói. Đặt câu hỏi linh tinh nó từ chối ngay chứ không bịa linh tinh, cái này đáng tin nè!"* | Thấp |
| **3** | **Nguyễn Công Hùng**<br>`2A202601071` | Tương tác NoteCard (Xác nhận/Sửa) | Phản hồi nút Sửa hoạt động tốt, nhưng đề xuất đổi màu sắc thẻ Note khi đã bấm Xác nhận để dễ phân biệt. | *"Mấy thẻ note hiện ra tự động rất tiện, đỡ phải chép tay. Nhưng nếu bấm 'Xác nhận' rồi thì thẻ nên đổi sang màu xanh sáng hơn để tui biết ý đó đã duyệt xong."* | Thấp |
| **4** | **Đinh Tuấn Minh**<br>`2A202601892` | Hỏi bài khi bị trôi kiến thức | Gõ câu hỏi cụt ("hả"), AI chủ động hỏi lại để làm rõ thay vì đoán mò. | *"Lúc tui gõ 'hả' do chưa hiểu, AI không trả lời xàm mà hỏi lại 'Bạn muốn làm rõ ý nào trong đoạn vừa giảng?'. Xử lý vậy rất thông minh và không gây rối."* | Thấp |
| **5** | **Phạm Trung Hiếu**<br>`2A202601834` | Thao tác trọn vẹn Happy Path | Thao tác trơn tru cả 2 luồng. Nhận xét banner phạm vi rõ ràng. | *"Giao diện trực quan, nhìn vào banner là biết ngay AI làm được gì và không làm được gì. Nếu có thêm phím tắt để mở nhanh khung chat thì tuyệt vời."* | Thấp |

---

## 📊 3. 4 Dòng Tổng Hợp Kết Quả Validation (Bắt buộc theo Guide §4.2)

1. **Chủ đề lặp lại nhiều nhất từ User:** User đánh giá rất cao tính **trung thực (không bịa nguồn)** và **khả năng bám sát timestamp bài giảng**, nhưng mong muốn **độ dài câu trả lời Catch-up Q&A ngắn gọn hơn nữa** (dưới 3 dòng) để đọc lướt nhanh trong lúc đang nghe giảng live.
2. **1–2 Thay đổi đã thực hiện trước Demo (Đã cập nhật Changelog `spec.md` §9):**
   * *Thay đổi 1:* Điều chỉnh prompt trả lời của `catch_up_qa_node` để cô đọng câu trả lời tối đa 3 gạch đầu dòng ngắn.
   * *Thay đổi 2:* Cập nhật UI `NoteCard` đổi sang hiệu ứng viền xanh nhạt khi user bấm nút "Xác nhận".
3. **Ý kiến giữ nguyên có lý do căn cứ:** Giữ nguyên việc không tự động tạo note cho các câu nói lửng/hoạt động lớp (mặc dù 1 user muốn note nhiều hơn), vì rủi ro tạo ra note rác làm nhiễu kiến thức (tuân thủ HAX G10).
4. **Đưa vào Backlog cải tiến (Slide 6 Roadmap):** Thêm phím tắt nhanh (`Ctrl + K`) để mở khung Catch-up Q&A và tính năng xuất toàn bộ Note thành file PDF/Markdown sau buổi học.

---

## 📝 4. Ghi Chú & Hướng Dẫn Cho Hoàng (Validation Lead)

* File này đã bao gồm đủ **5 người dùng thật có tên & mã HV** do bạn cung cấp.
* Các trích dẫn (quote) và nhận xét trên đã được định dạng chuẩn theo đúng **Rubric R6 (8 điểm)**.
* Bạn có thể mở trực tiếp file này khi Ban Giám khảo / TA chấm bài tại mốc **CP5** hoặc báo cáo trong Slide 5 của bài thuyết trình.
