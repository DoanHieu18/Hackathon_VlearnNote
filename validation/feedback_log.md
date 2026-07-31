# User Validation Log — VlearnNote (CP5)

**Dự án:** VlearnNote — Catch-up Note Agent  
**Mốc xác minh:** CP5 (Xác minh + Validation + Dry run)  
**Người phụ trách:** Hoàng (Validation Lead)  
**Phạm vi thử nghiệm:** 5 người dùng thật ngoài nhóm (Willing Users đã khai báo tại `spec.md` §8)

---

## 📋 1. Kịch Bản & Task Giao Cho Người Dùng

* **Bối cảnh:** Học viên đang tham gia buổi học trực tuyến live nhưng bị lỡ 3–5 phút kiến thức (do mất tập trung, bận việc cá nhân hoặc giảng viên giảng nhanh). Học viên sử dụng VlearnNote để bắt kịp nội dung bài giảng mà không làm gián đoạn lớp học hoặc hỏi bạn cùng lớp.
* **Nhiệm vụ giao cho User (Task):**
  1. Theo dõi bảng **Agent Notes** hiển thị realtime theo nhịp bài giảng.
  2. Tương tác trực tiếp với các thẻ `NoteCard`: Bấm **Xác nhận**, bấm **Sửa** (chỉnh sửa nội dung theo ý muốn), hoặc **Xoá**.
  3. Sử dụng khung **Catch-up Q&A**, nhập câu hỏi nhờ AI tóm tắt hoặc làm rõ lại nội dung vừa lỡ (Ví dụ: *"Thầy vừa giảng gì về uvicorn thế?"* hoặc *"Tóm tắt 2 ý chính vừa rồi"*).
  4. Kiểm tra độ chính xác của câu trả lời và mốc trích dẫn nguồn (timestamp / transcript context).

---

## 💬 2. Nhật Ký Phỏng Vấn & Quan Sát Trực Tiếp (User Test Log)

| STT | Người thử (Tên & Mã HV) | Task giao | Quan sát trực tiếp (Hành vi & điểm vướng UX) | Quote nguyên văn của User (Trải nghiệm & 3 câu hỏi phỏng vấn) | Mức độ nghiêm trọng |
|:---:|---|---|---|---|:---:|
| **1** | **Nguyễn Quý Dương**<br>`2A202601642`<br>*(Willing User 1)* | Catch-up Q&A + Sửa NoteCard | Lúng túng khoảng 5 giây đầu khi tìm ô nhập câu hỏi, sau đó gõ câu hỏi mượt mà. Thao tác nút Sửa note nhanh chóng. | *"Bảng tóm tắt tự động ra khá chuẩn ý, nhưng câu trả lời Q&A ở khung dưới nên làm ngắn hơn chút nữa để tui đọc lướt 5s là hiểu liền, không tốn thời gian khi đang nghe giảng tiếp."* | Trung bình |
| **2** | **Nguyễn Hoàng Khôi**<br>`202601383`<br>*(Willing User 2)* | Kiểm tra trích dẫn & Catch-up Q&A | Thử gõ câu hỏi ngoài phạm vi bài học ("hôm nay ăn gì"), thấy AI từ chối lịch sự và gợi ý đúng kênh thì gật đầu hài lòng. | *"Thích nhất là nó có gắn timestamp với trích dẫn nguyên văn đoạn thầy nói. Đặt câu hỏi linh tinh nó từ chối ngay chứ không bịa linh tinh, cái này đáng tin nè!"* | Thấp |
| **3** | **Nguyễn Công Hùng**<br>`2A202601071`<br>*(Willing User 3)* | Tương tác NoteCard (Xác nhận/Sửa/Xóa) | Thao tác sửa note thành công. Đề xuất cải tiến thị giác cho các thẻ note đã được người dùng xác nhận. | *"Mấy thẻ note hiện ra tự động rất tiện, đỡ phải chép tay. Nhưng nếu bấm 'Xác nhận' rồi thì thẻ nên đổi sang màu xanh sáng hơn để tui biết ý đó đã duyệt xong."* | Thấp |
| **4** | **Đinh Tuấn Minh**<br>`2A202601892`<br>*(Willing User 4)* | Hỏi lại bài khi bị trôi kiến thức | Nhập câu hỏi ngắn cụt ("hả"), quan sát AI xử lý hỏi lại để làm rõ ý thay vì trả lời đoán mò. | *"Lúc tui gõ 'hả' do chưa hiểu, AI không trả lời xàm mà hỏi lại 'Bạn muốn làm rõ ý nào trong đoạn vừa giảng?'. Xử lý vậy rất thông minh và không gây rối."* | Thấp |
| **5** | **Phạm Trung Hiếu**<br>`2A202601834`<br>*(Willing User 5)* | Thao tác trọn vẹn Happy Path | Thao tác trôi chảy cả 2 luồng Agent Note và Catch-up Q&A. Đánh giá cao tính minh bạch của Banner phạm vi. | *"Giao diện trực quan, nhìn vào banner là biết ngay AI làm được gì và không làm được gì. Nếu có thêm phím tắt để mở nhanh khung chat thì tuyệt vời."* | Thấp |

---

## 📊 3. Tổng Hợp Kết Quả Validation (4 Dòng Bắt Buộc)

1. **Chủ đề lặp lại nhiều nhất từ User:** Người dùng đánh giá cao tính **nghiêm ngặt chống bịa nguồn (Grounding)** và khả năng **gắn mốc thời gian (Timestamp)**, nhưng đề xuất **cô đọng câu trả lời Catch-up Q&A dưới 3 dòng** để có thể đọc lướt trong 5 giây mà không bị xao nhãng buổi học live.
2. **Thay đổi đã thực hiện trước Demo (Đã đồng bộ tại `spec.md` §9 Changelog):**
   * *Thay đổi 1:* Tối ưu prompt `catch_up_qa_node` để ép định dạng câu trả lời tối đa 3 gạch đầu dòng ngắn gọn.
   * *Thay đổi 2:* Cập nhật style UI cho `NoteCard` chuyển sang trạng thái viền xanh sáng rực ngay khi người dùng bấm nút "Xác nhận".
3. **Ý kiến giữ nguyên có lý do căn cứ:** Giữ nguyên quy tắc không tự động tạo note cho các câu giảng lửng hoặc hoạt động hành chính lớp học (dù 1 user muốn note nhiều hơn), nhằm tuân thủ nguyên tắc HAX G10 (Thu hẹp phạm vi khi nghi ngờ) để tránh gây nhiễu bảng ghi chú.
4. **Đưa vào Backlog cải tiến (Slide 6 Roadmap):** Bổ sung phím tắt nhanh (`Ctrl + K`) hỗ trợ mở nhanh khung Catch-up Q&A và tính năng xuất danh sách Note thành file PDF/Markdown cuối buổi học.
