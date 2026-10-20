# Local Affiliate Studio

Công cụ video local cho Windows, đang phát triển luồng **ảnh sản phẩm → ảnh khung cảnh tham chiếu → duyệt → image-to-video**. Không dùng API dịch vụ AI đám mây. Các thành phần local giao tiếp qua HTTP loopback; Internet dùng để cài phần mềm/tải model.

Bản cũ đã sinh từng cảnh bằng Wan 2.1 T2V và chèn ảnh sản phẩm đè lên video, gây đổi người, sai bao bì và hình như miếng dán. Luồng đó không phù hợp cho quảng cáo cần nhận diện sản phẩm. Bản sửa bỏ ảnh đè và thêm graph tham chiếu thực sự. **Chưa xác minh chất lượng sinh model trên RTX 5070 12GB; không gọi đây là công cụ đã bảo đảm mọi yêu cầu quảng cáo.**

## Bắt đầu / cập nhật Windows 11

1. Giải nén mã nguồn. Nếu cập nhật bản cũ, chép mã mới vào thư mục hiện tại và giữ `.venv/`, `runtime/`, `models/`, `work/`, `outputs/`.
2. Cập nhật driver NVIDIA hỗ trợ CUDA 12.8. Chuẩn bị ít nhất **55GB trống**, khuyến nghị 70GB cho model/cache/video mới.
3. Chạy **`setup-windows.bat -Profile reference`**. Cần Internet và winget (hoặc tự cài Python 3.12/Ollama từ nguồn chính thức nếu thiếu winget).
4. Chạy **`start-windows.bat`**. Chọn **Ảnh tham chiếu → duyệt khung → I2V**, chọn một ảnh sản phẩm chuẩn và nhập prompt.
5. Duyệt các khung, thử chuyển động từng cảnh rồi mới dựng dài. Xem [hướng dẫn chi tiết và giới hạn](docs/REFERENCE.md).

Profile reference cài ComfyUI, PyTorch CUDA 12.8, FLUX.2 Klein 4B fp8, text encoder Qwen3 4B, FLUX2 VAE, Wan 2.2 TI2V 5B, Wan2.2 VAE, UMT5 và Piper. Dùng model nhỏ hơn không có nghĩa chắc chắn vừa 12GB VRAM. Bộ cài có phép tính tensor GPU để kiểm tra CUDA, nhưng chưa benchmark các model này trên máy mục tiêu.

**Lip-sync là phần cài riêng, chưa có bộ cài Windows/RTX 5070 được kiểm chứng.** Adapter MuseTalk local có sẵn; thiếu module/model sẽ chặn yêu cầu khớp môi. Không coi giọng đọc ghép vào video là lip-sync. [Cấu hình/giới hạn MuseTalk](docs/REFERENCE.md).

## Hành vi đã sửa

- Ảnh được upload thật vào ComfyUI, đi qua VAE/reference conditioning; không chỉ nối tên file vào prompt.
- Khung đầu làm tham chiếu thêm cho nhân vật/bối cảnh ở các khung sau.
- Khung đã duyệt đi vào graph **Wan22ImageToVideoLatent**, dùng đúng Wan2.2 VAE; không thay bằng T2V hoặc ảnh tĩnh.
- Timeline/lời thoại đặt trong prompt được giữ nguyên. Các mốc 0–5, 5–13, 13–20, 20–28 được dựng thành 28 giây.
- “Không tự thêm chữ” tắt phụ đề đóng vào hình; không ép toàn bộ lời thoại lên màn hình.
- Mỗi cảnh có clip thử tối đa 3s để duyệt. Clip đã duyệt được dùng lại khi dựng dài; các đoạn sau tiếp tục bằng khung cuối.
- Không loop, freeze hoặc kéo dài giả trong luồng tham chiếu. Thiếu frame báo lỗi. PCM audio ghép riêng trước khi encode AAC để tránh trễ tích lũy theo cảnh.
- Thiếu lip-sync local hoặc module lỗi thì dừng. Chỉ đổi sang voiceover khi người dùng chọn rõ ràng; lưu hình thức thực tế trong JSON.

Đưa ảnh vào model **không bảo đảm pixel/logo/chữ được giữ nguyên**, bàn tay đúng hay miệng chính xác. Duyệt khung/clip là kiểm tra bằng mắt, không phải bộ kiểm định tự động. Bản xem trước hiện chỉ kiểm tra hình; lip-sync thực tế chưa có mẫu được xác minh. Người dẫn/căn bếp được model dựng từ mô tả, chưa có bảo đảm giữ danh tính tuyệt đối.

## Chế độ và profile khác

| Chế độ | Hành vi |
|---|---|
| Tham chiếu (mới) | FLUX.2 Klein dựng khung từ ảnh thật + Wan2.2 I2V; cần profile reference |
| Ảnh thật | Zoom ảnh sản phẩm, không tạo người/động tác bằng AI; chạy CPU |
| SDXL (cũ) | Sinh ảnh bằng text, không nhận ảnh sản phẩm làm điều kiện |
| Wan2.1 T2V (cũ) | Thử nghiệm không ảnh điều kiện, dễ drift; không dùng như cam kết giữ đúng sản phẩm |
| Workflow riêng | Các node core local trong danh sách cho phép; chưa tự ánh xạ ảnh |

`setup-windows.bat -Profile basic` cài TTS/dựng ảnh thật; `images` cài SDXL; `video` cài Wan2.1 cũ; `all` cài cả hai profile cũ. `all` không thay thế profile `reference`. Bộ cài không tự xóa các model cũ hoặc tắt xác minh TLS/checksum để làm setup vượt qua.

## Âm thanh / file đầu ra

Piper neural, eSpeak NG offline (giọng máy), Windows System.Speech nếu có voice tương thích, hoặc file WAV/MP3 tự tải lên. Cần nghe thử voice; chưa xác nhận Piper hiện tại đáp ứng giọng nữ tự nhiên. Nhạc ambient tạo bằng thuật toán local, không phải model AI sinh nhạc; file nhạc tải lên ưu tiên nếu bạn chọn.

Đầu ra MP4 H.264/AAC 720×1280, 24fps, SRT và JSON. I2V bản nháp 288×512, bản cân bằng 576×1024 rồi upscale; không phải model sinh 720p gốc. Video dài được sinh theo các đoạn ngắn, có thể tích lũy drift. Xem toàn bộ video trước khi dùng.

File: `outputs/`; dự án tham chiếu: `work/projects/`; lịch sử: `work/jobs.json`; log: `work/logs/`; model: `models/` và `runtime/ComfyUI/models/`. Dừng ứng dụng trước khi dọn dữ liệu. Chỉ chạy một instance ứng dụng dùng chung thư mục. Các dịch vụ do ứng dụng khởi động sẽ dừng khi đóng; dịch vụ chạy sẵn không bị tắt.

## Local và bảo vệ dữ liệu

Giao diện bind 127.0.0.1, kiểm tra Host/Origin, không mở CORS. Adapter AI chặn URL ngoài loopback, bỏ proxy và chặn redirect ra ngoài. Ollama `/api/show` được kiểm tra để từ chối model remote/cloud. Graph chỉ dùng danh sách node core xử lý local. ComfyUI do ứng dụng quản lý bật offline, tắt custom nodes và cache-none; ONNX telemetry bị tắt trước khi nạp Piper. Đây không phải firewall cho mọi phần mềm trên PC; tự cấu hình server ngoài do bạn chạy.

Trọng số tải từ nguồn chính thức qua HTTPS, kiểm SHA256 LFS/Git blob theo revision bất biến. Archive ComfyUI được ghim commit và SHA256. Thông tin tải lưu tại `models/download-records.json`. Không cần secret hoặc API key cho suy luận. License code không thay thế license model/voice/nhạc: xem [thành phần bên ngoài](docs/THIRD_PARTY.md).

## Phát triển / kiểm thử

```bash
cd /workspace/AI
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py --no-browser --no-services --port 7864
```

Dùng checkout hiện có trong môi trường cô lập; không cần Git worktree. Loopback không phải web preview cloud. Cloud hiện không có GPU/trọng số; không dùng thành công CPU để tuyên bố model/Windows đã đạt.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/selftest.py
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/browser-smoke.py --port 7864
.venv/bin/python scripts/reference-browser-smoke.py --port 7864
.venv/bin/python scripts/package.py
```

Unit/integration test cần FFmpeg/ffprobe hệ thống; browser test cần Chromium. Reference integration dùng output model mô phỏng để kiểm đường đi ảnh, duyệt, thời gian, mux và các chặn lỗi; **không kiểm tra chất lượng AI**. `scripts/selftest.py` kiểm ảnh thật/TTS/FFmpeg CPU. `test-ai-windows.bat` hiện là selftest cũ Wan2.1/SDXL, không chứng nhận luồng tham chiếu hoặc lip-sync. Luồng mới kiểm qua giao diện theo [REFERENCE.md](docs/REFERENCE.md).

Ứng dụng độc lập, chưa phải fork đầy đủ MoneyPrinterTurbo. [Đánh giá repo](docs/MoneyPrinterTurbo-review.md) · [Báo cáo kiểm thử](docs/VALIDATION.md).
