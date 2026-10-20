# Kết quả xác minh

Kiểm tra trong môi trường Linux CPU, Python 3.12.14. Đây không phải xác nhận chạy thành công trên Windows 11 hoặc RTX 5070.

## Đã đạt

- **14 kiểm thử unittest**, không skip: tạo lời đọc eSpeak tiếng Việt có audio thật; phân bổ frame đúng cho 20/30/40s; từ chối kết nối AI ngoài loopback; chặn redirect từ local ra Internet; phát hiện alias Ollama remote/cloud trước khi gửi prompt; từ chối workflow cloud/custom chưa chấp nhận; kiểm tra checksum và không ghi đè file hỏng; hủy trước khi dựng và hủy tiến trình đang chạy; xử lý lỗi node; mock giao thức ComfyUI + dựng/decode video có ảnh sản phẩm overlay, tiếng, nhạc, SRT và storyboard; test MP4 end-to-end; xác thực thời lượng đầu vào.
- **Selftest CPU thực tế**: video MP4 H.264/AAC 720×1280, thời lượng ffprobe `20.000000` giây, lời đọc eSpeak tiếng Việt, nhạc tổng hợp, phụ đề đóng vào hình. Decode toàn bộ file thành công. Mẫu nằm ở examples/demo-photo-local.mp4.
- **Chromium thực tế qua giao diện**: điền form, tải ảnh, dựng video 720p/20s có lời đọc và nhạc, phát metadata đúng 20s/720p, tải byte-range 206, hủy tác vụ mới, lịch sử, layout mobile không tràn ngang. Không có lỗi JavaScript hoặc request browser ra ngoài loopback trong lần thử.
- **ComfyUI thật 0.42.0**, ghim commit `8f04fd6ecf4a548937971e840af2a985529fab76`, PyTorch 2.10.0+CPU: khởi động thành công, schema node của các graph Wan/SDXL khớp với server; chỉ thiếu tên file trọng số. Chạy graph EmptyImage → SaveWEBM, submit → history → tải WEBM → decode thành công. Graph này **không sinh AI**.
- Xác minh SHA256 archive ComfyUI chính thức trước khi giải nén. Tra tên repo/file Wan theo ví dụ upstream: https://github.com/comfyanonymous/ComfyUI_examples/blob/master/wan/README.md . Repo đúng là `Comfy-Org/Wan_2.1_ComfyUI_repackaged`.
- Đã tìm thấy và tải được wheel **Windows x64/Python 3.12** của Piper 1.4.2, espeakng-loader 0.2.4, imageio-ffmpeg 0.6.0, comfy-kitchen 0.2.39, comfy-aimdo 0.5.6. Binary FFmpeg Windows có chuỗi cấu hình enable-libass và enable-libx264; **chưa thực thi binary Windows**.
- Kiểm tra dependency (`pip check`) ứng dụng và ComfyUI CPU đều đạt. JavaScript được Node kiểm tra cú pháp, Python compile thành công.

## Chưa đạt / chưa chạy

- **Piper neural**: `doctor --profile basic` báo FFmpeg/eSpeak PASS, Piper FAIL do thiếu model. Chưa suy luận Piper hoặc đánh giá chất lượng/giấy phép voice.
- **Tải model từ Hugging Face**: proxy trả HTTP 403 khi gọi model metadata. Đã lưu tên miền Hugging Face vào cấu hình draft; chưa xác nhận được áp dụng ở runtime. Bộ tải đã kiểm tra logic checksum bằng fixture; chưa kiểm chứng tải trọng số thực tế.
- **Ollama suy luận thực tế**: chưa cài model trong cloud; giao thức, keep_alive=0, kiểm tra local/remote được test với server fixture. Chưa đánh giá chất lượng kịch bản của Qwen2.5:3b.
- **Wan/SDXL GPU**: chưa có GPU/trọng số trong cloud. Schema và vận chuyển media đã xác minh, chưa xác minh tốc độ, VRAM, chất lượng hay suy luận model. Test fixture không được tính là AI inference.
- **Windows 11**: chưa chạy bộ cài PowerShell/batch, eSpeak DLL, Windows voice, CUDA hay Piper trên máy Windows. Không có kiểm thử unattended cài đặt đầy đủ từ máy Windows sạch.

## Kiểm chứng cuối trên PC

1. Chạy setup-windows.bat. Cần Internet tải model, dung lượng trống và driver hỗ trợ CUDA 12.8. Bộ cài kiểm tra phép nhân tensor GPU và `doctor`; lỗi phải xử lý trước khi gọi máy sẵn sàng.
2. Chạy start-windows.bat; chờ Ollama và ComfyUI sẵn sàng.
3. Chạy test-ai-windows.bat. Lệnh này thật sự chạy Ollama/Piper/Wan và dựng video 20s, decode toàn bộ MP4. Báo cáo thành công mới nằm ở work/ai-selftest-report.json. Muốn thử SDXL, cài profile images/all rồi dùng --mode sdxl.
4. Xem và nghe lại mẫu, thử ngắt Internet sau khi cài đủ rồi tạo lại để xác minh offline trên máy thực tế.

ZIP nguồn không kèm trọng số, môi trường Python, giọng neural hoặc phần mềm cài sẵn. Không quảng bá kết quả kiểm thử CPU thành chứng nhận toàn bộ pipeline AI/Windows đã hoàn tất.

Cập nhật dựng: test phụ đề dài kiểm tra không mất từ, tối đa hai dòng/cue và thời điểm kết thúc; 14 test đạt sau khi bỏ lặp clip, thêm seed chẩn đoán và thu nhỏ phụ đề. Chưa chạy lại Wan trên GPU, chưa chứng minh sửa được biến dạng hoặc identity drift. Không đưa video người dùng vào Git/release.
