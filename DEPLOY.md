# Deploy miễn phí trên một Render service

Repo dùng Docker để build React và chạy FastAPI trong cùng một service. Frontend,
REST API và WebSocket dùng chung một domain nên không cần Vercel hay `VITE_API_URL`.

1. Tạo Render Web Service từ repository `DoanHieu18/Hackathon_VlearnNote`.
2. Chọn branch `main` và runtime `Docker`.
3. Để trống Root Directory; Dockerfile nằm ở root repository.
4. Thêm `OPENAI_API_KEY` trong Environment.
5. Chọn instance Free và deploy.

Nếu service cũ đang dùng runtime Python/Root Directory `backend`, nên tạo service
mới từ `render.yaml` hoặc đổi runtime sang Docker và xóa Root Directory.

Render free có thể ngủ khi không có truy cập; request đầu tiên sau một thời gian
sẽ cần vài giây để thức dậy. SQLite và audio nằm trên filesystem tạm thời nên có
thể mất khi Render redeploy; dữ liệu cần lưu lâu dài nên chuyển sang PostgreSQL.
