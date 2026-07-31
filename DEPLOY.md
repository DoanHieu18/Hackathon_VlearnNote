# Deploy miễn phí

## Backend trên Render

1. Tạo Web Service từ repository `DoanHieu18/Hackathon_VlearnNote`.
2. Chọn branch `main`; Render sẽ đọc `render.yaml`.
3. Thêm `OPENAI_API_KEY` trong Environment.
4. Sau khi deploy, lưu URL dạng `https://vlearnnote-api.onrender.com`.

## Frontend trên Vercel

1. Import cùng repository vào Vercel.
2. Chọn Root Directory là `frontend` và framework là Vite.
3. Thêm biến môi trường `VITE_API_URL` bằng URL Render ở trên.
4. Deploy. `frontend/vercel.json` đã cấu hình fallback cho React Router/SPA.

Render free có thể ngủ khi không có truy cập; request đầu tiên sau một thời gian sẽ cần vài giây để thức dậy.
