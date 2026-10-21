# Kết quả xác minh bản tham chiếu

Môi trường kiểm tra: Linux CPU/Python 3.12.14. Chưa có GPU hoặc trọng số FLUX.2 Klein/Wan2.2/MuseTalk để xác minh chất lượng sinh.

## Đã đạt

- **23 unittest, không skip**: giữ nguyên lời thoại/timeline và lệnh cấm chữ; kết nối AI chỉ loopback; chặn model Ollama remote/cloud; checksum tải file; hủy subprocess; audio eSpeak Việt thật; dựng ảnh thật; caption; graph Klein nhận product+anchor latents; graph Wan2.2 nhận start image/VAE đúng; ảnh bị đổi phải duyệt lại; legacy T2V không giả làm lip-sync; MuseTalk thiếu output không tạo file giả. Hai bài mới kiểm đường đi hai expert/VAE/conditioning A14B và chuyển video fixture 16fps sang 24fps cùng đoạn nối, giữ đúng 123 frame/5.125s.
- **Integration tham chiếu dùng output model fixture**: truyền pixel thật qua HTTP multipart, tạo/duyệt bốn khung và bốn clip fixture, chặn export khi thiếu lip-sync. Chỉ sau lựa chọn voiceover rõ ràng mới dựng được MP4 thực tế **28.000s/672 frame/720×1280**, có audio. Không overlay, phụ đề burn, loop hoặc freeze trong bài thử này. Mô phỏng output không phải suy luận AI.
- **Chromium thực tế**: luồng tham chiếu qua giao diện đạt từ upload, duyệt, xem clip thử, chặn thiếu lip-sync, chọn voiceover đến MP4 28s/720p. Browser smoke ảnh thật cũ cũng đạt: upload, render 20s/720p có eSpeak/nhạc/phụ đề, playback metadata, byte range 206, hủy và responsive mobile; không có lỗi JS/request browser ra ngoài loopback trong lần thử.
- **ComfyUI thật 0.42.0 CPU**, source ghim `8f04fd6ecf4a548937971e840af2a985529fab76`: nhận PNG upload, LoadImage nhận tên file, schema/enum node của các graph Klein/Wan2.2 khớp. Validation bị chặn đúng ở model chưa cài, không chèn file/trạng thái giả để vượt qua. Graph core EmptyImage→SaveWEBM submit/history/download/decode đã đạt, không dùng trọng số neural.
- Source ComfyUI tải chính thức được kiểm SHA256. Tên file/model của graph mới đối chiếu template `image_flux2_klein_image_edit_4b_distilled` và `video_wan2_2_5B_ti2v` đi kèm ComfyUI.
- **A14B/GGUF**: archive ComfyUI-GGUF ghim commit/SHA256 đã tải và kiểm hash; dependency gguf 0.19.0 nạp được trên ComfyUI 0.42.0 CPU. Upload PNG thật và đối chiếu schema/input/enum A14B đạt; kiểm tra readiness từ chối đúng vì chưa có trọng số. Hai expert, sampler 10/10, shift/CFG, VAE và 16fps đối chiếu template chính thức `video_wan2_2_14B_i2v`. Metadata Hugging Face của QuantStack hiện truy cập được, xác nhận hai file Q4_K_S (8,748,151,296 byte/file) và SHA256; chưa tải trọng số.
- **Chromium A14B**: chọn model trong UI, upload/duyệt bốn khung fixture, bốn clip fixture, chặn thiếu lip-sync và xuất voiceover sau lựa chọn rõ ràng đạt MP4 28s/720p. Fixture không chạy model A14B hoặc Klein. Metadata dự án ghi đúng A14B; không dùng lại graph 5B.
- FFmpeg mux được sửa để tránh AAC priming tích lũy: concat video và PCM riêng, encode AAC một lần, kiểm frame đầu ra trước công bố. Fixture từng phát hiện lệch 1 frame, sau sửa đạt đúng 672.
- Kiểm tra compile Python, cú pháp JS và pip check đạt. Wheel Windows x64/Python3.12 của Piper, espeakng-loader, imageio-ffmpeg, comfy-kitchen và comfy-aimdo đã tải được; chưa thực thi Windows binary. Cấu hình FFmpeg Windows có libass/libx264.

## Chưa đạt / chưa chạy

- **Chất lượng AI**: chưa sinh ảnh/clip neural với ảnh sản phẩm Topgia; chưa có bằng chứng logo, chữ, gương mặt và thao tác tay đúng hoặc nhất quán. I2V/negative prompt/seed không phải bảo đảm giữ đúng bao bì.
- **VRAM/Windows**: chưa chạy model hoặc bộ cài reference trên Windows 11/RTX 5070 12GB; chưa đo thời gian, VRAM, RAM hoặc tính ổn định.
- **Lip-sync**: adapter MuseTalk đã có, chưa tự cài môi trường/weights; chưa chạy inference MuseTalk hoặc kiểm chất lượng đồng bộ môi tiếng Việt. Layout file hợp lệ chỉ được báo là cấu hình tồn tại. Thiếu/lỗi backend sẽ chặn yêu cầu khớp môi. Upstream CUDA/MMLab cũ chưa được xác minh cho Blackwell.
- **Piper/Ollama neural**: chưa tải/kiểm model thực tế trong cloud. Doctor Piper báo FAIL do thiếu voice model; eSpeak/FFmpeg PASS. Giao thức Ollama được test bằng fixture, chưa đánh giá Qwen hoặc giọng nữ tự nhiên.
- **Download trọng số**: lần trước Hugging Face trả proxy HTTP403 trong cloud; metadata QuantStack đã truy cập được ở lần kiểm tra A14B. Chưa tải/kiểm toàn bộ các file trọng số thật hoặc xác nhận tải tất cả nguồn trên Windows. Logic checksum có fixture test.

## Kiểm tra trên PC

Chạy `setup-windows.bat -Profile reference`, mở ứng dụng, chọn luồng tham chiếu. Kiểm tra khung đầy đủ rồi clip thử của từng cảnh. Không duyệt nếu logo/người/tay sai. Để xuất yêu cầu khớp môi, cần một môi trường MuseTalk chạy được, cấu hình và kiểm tra kết quả thực tế; xem [REFERENCE.md](REFERENCE.md). Voiceover chỉ được dùng khi chủ động thay yêu cầu.

Muốn thử model lớn hơn, cài `setup-windows.bat -Profile reference-hq`, mở lại tool và chọn A14B Q4 trước khi tạo dự án mới; xem [MODELS.md](MODELS.md). Chưa benchmark chất lượng, thời gian hoặc bộ nhớ A14B trên RTX 5070/32GB RAM. Source test thành công không phải xác nhận chất lượng quảng cáo.

`test-ai-windows.bat` vẫn là selftest cũ Wan2.1/SDXL, không chứng nhận luồng mới. `scripts/selftest.py` và mẫu `examples/demo-photo-local.mp4` chỉ là dựng ảnh thật/eSpeak trên CPU. Source ZIP không chứa trọng số, voice neural hoặc môi trường cài sẵn. Video/ảnh riêng người dùng không được đưa vào Git/release; fixture dùng ảnh tự tạo.
