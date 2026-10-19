# Local Affiliate Studio

Công cụ PC cho **Windows 11 / Ryzen 7600X / RTX 5070 12GB / RAM 32GB**: nhập ý tưởng và thông tin sản phẩm → viết kịch bản → sinh cảnh → lời đọc tiếng Việt → video dọc **20/30/40 giây** có phụ đề và nhạc.

**Không cần API key hoặc dịch vụ AI đám mây.** Ollama, ComfyUI, TTS và FFmpeg xử lý trên cùng PC. ONNX Runtime được tắt telemetry qua API trước khi nạp giọng Piper. Internet dùng để cài phần mềm và tải model ban đầu. Dịch vụ nội bộ giao tiếp HTTP loopback, không gửi prompt tới nhà cung cấp cloud. Sau khi tải đủ, có thể ngắt Internet để tạo video.

## Cài trên Windows

1. Giải nén toàn bộ bộ công cụ vào thư mục có quyền ghi, ví dụ `D:\LocalAffiliateStudio`. Để trống ít nhất **35GB**, khuyến nghị 50–60GB cho model và video trung gian. Cập nhật driver NVIDIA hỗ trợ CUDA 12.8/RTX 50.
2. Bấm **`setup-windows.bat`**. Cần Internet và winget (App Installer của Windows). Bộ cài chuẩn bị Python 3.12 nếu thiếu, môi trường ứng dụng, PyTorch CUDA 12.8, ComfyUI, Ollama + Qwen2.5:3b, model Wan 2.1 1.3B và giọng Piper tiếng Việt. Tải model có thể lâu, nhiều GB. Có thể có hộp thoại từ trình cài Windows.
3. Bấm **`start-windows.bat`**. Trình duyệt mở giao diện; ComfyUI/Ollama được khởi động nếu đã cài và chưa chạy. Bấm **Kiểm tra lại** sau khi các dịch vụ khởi động.
4. Nhập prompt, thông tin sản phẩm, chọn thời lượng và **Tạo video trên máy**. Video nằm trong `outputs/`. Với hàng hóa cụ thể nên tải thêm ảnh sản phẩm và giữ tùy chọn chèn ảnh thật.

Nếu thiếu winget, cài Python 3.12 và Ollama từ trang chính thức rồi chạy lại. Bộ cài không bỏ qua lỗi checksum, TLS hoặc CUDA. Lỗi sẽ dừng với thông báo; sửa nguyên nhân rồi chạy lại, file đã tải đúng được giữ nguyên. Không chạy bộ cài khi đang dựng video.

### Chọn bộ model

Chạy trong Command Prompt ở thư mục ứng dụng:

```bat
setup-windows.bat -Profile video
setup-windows.bat -Profile images
setup-windows.bat -Profile all
setup-windows.bat -Profile basic
```

- `video` (mặc định): Wan sinh clip chuyển động + Ollama + Piper.
- `images`: SDXL sinh ảnh + chuyển động zoom, Ollama + Piper. Chọn đúng chế độ SDXL trong giao diện.
- `all`: cả Wan và SDXL, cần tối thiểu 45GB trống khi bắt đầu cài; khuyến nghị nhiều hơn.
- `basic`: TTS và dựng ảnh thật; không cài Ollama/ComfyUI. Trong giao diện chọn ảnh sản phẩm và tắt viết bằng Ollama.

Chỉ profile được chọn mới được tải; không âm thầm chuyển từ video AI sang slideshow khi thiếu model. Giữ cửa sổ ứng dụng mở trong khi dựng; đóng sẽ dừng các dịch vụ do ứng dụng tự khởi động. Dịch vụ đã chạy từ trước không bị ứng dụng tắt.

## Các chế độ

| Chế độ | Kết quả | Phần cứng/model |
|---|---|---|
| Wan 2.1 | Clip AI có chuyển động, ghép 20–40s | GPU, model Wan 1.3B + UMT5 + VAE |
| SDXL | Ảnh AI, chuyển động zoom, ghép 20–40s | GPU, SDXL base |
| Ảnh sản phẩm | Dựng ảnh thật, giữ đúng sản phẩm | CPU, ít nhất một ảnh |
| Workflow riêng | Output từ ComfyUI API graph | Model/node core local của workflow |

Bản nháp Wan tạo cảnh 288×512/49 frame, bản cân bằng 480×832/81 frame, model chạy 16fps rồi dựng ra 24fps/720×1280. Đây là upscale, không phải model sinh 720p gốc. Cảnh ngắn được cắt/lặp để đủ timeline. Tổng 20–40 giây là video đã ghép; không sinh một đoạn dài liên tục. Chưa có benchmark tốc độ/VRAM trên RTX 5070 thật.

**Ảnh thật được chèn nguyên dạng lên nền AI**, không tự đưa vào model image-to-video. Text-to-video có thể tạo sai hình dạng, logo hoặc chi tiết sản phẩm. Chức năng bảo toàn sản phẩm bằng I2V chưa có; dùng ảnh thật khi nhận diện sản phẩm là yêu cầu bắt buộc.

### Lời đọc, phụ đề, nhạc

- **Piper neural tiếng Việt**: chạy CPU với model đã tải. Bộ cài lưu model card; xem quyền sử dụng voice trước khi làm nội dung thương mại.
- **eSpeak NG**: tiếng Việt offline có sẵn trong dependency, giọng máy. Không cần tải model neural và đã chạy thử thực tế trên Linux.
- **Windows voice**: tùy chọn nâng cao, chỉ các voice tương thích System.Speech; không đảm bảo voice Windows Settings có sẵn ở API này.
- **File WAV/MP3**: ưu tiên hơn giọng tự sinh. File nhạc tải lên ưu tiên hơn nhạc tự tạo.
- Phụ đề được đóng vào video, kèm file SRT. Giọng tự sinh được tạo từng câu và phân bổ thời gian theo độ dài; nếu quá dài, tăng tốc để vừa video. Đây là căn theo câu/cảnh, không phải karaoke từng từ. Lời đọc tự tải lên có phụ đề chia theo cảnh, chưa nhận dạng/forced alignment.
- Nhạc tự tạo là hòa âm ambient tổng hợp bằng thuật toán, không dùng dịch vụ sinh nhạc hoặc nhạc thư viện có bản quyền.

## Chạy, kiểm tra và khắc phục

- Nút **Kiểm tra lại** báo FFmpeg, Ollama, ComfyUI và giọng đọc. Đây là kiểm tra thành phần, không phải bằng chứng model đã sinh video thành công.
- **`test-ai-windows.bat`** tạo video AI 20s thật, có Ollama/Piper/Wan. Giữ ứng dụng mở, không dựng video khác cùng lúc. Mặc định dùng bản nháp. Dùng `test-ai-windows.bat --mode sdxl` với profile images.
- Báo cáo chẩn đoán: `.venv\Scripts\python.exe scripts\doctor.py --profile video`; thêm `--verify-models` để đọc và đối chiếu checksum toàn bộ trọng số, có thể lâu.
- Log dịch vụ: `work\logs\`. Lịch sử: `work\jobs.json`. Model: `models\` và `runtime\ComfyUI\models\`.
- Hủy tác vụ dừng FFmpeg và gửi hủy theo prompt ID tới ComfyUI. Nếu đang ở Ollama/TTS, cần chờ lệnh hiện tại trả về. Tác vụ bị đóng giữa chừng được đánh dấu gián đoạn khi mở lại; chưa có resume từng cảnh.
- CUDA lỗi: cập nhật driver NVIDIA, đọc log. Bộ cài có thử phép nhân tensor thật trên GPU để phát hiện PyTorch/driver không tương thích. Không cần tự cài CUDA Toolkit riêng cho wheel PyTorch.
- Thiếu VRAM: chọn bản nháp, tắt ứng dụng chiếm VRAM, không chạy song song model khác. ComfyUI bật low-VRAM, text encoder Wan chạy CPU và VAE decode theo tile. Ollama được yêu cầu unload model sau khi viết xong. Có thể cần pagefile Windows; tốc độ thực tế phải đo trên máy.
- Thiếu giọng Piper: chạy lại bộ cài hoặc chọn eSpeak. Không có fallback TTS cloud.
- Thiếu filter subtitles: dùng FFmpeg có libass/libx264. Ưu tiên FFmpeg hệ thống, nếu không có dùng bản đóng gói của imageio-ffmpeg. Bản Windows chưa được chạy tại môi trường Linux này.
- Port bận: có thể dùng `.venv\Scripts\python.exe app.py --port 7862`. Các dịch vụ model vẫn dùng 8188 và 11434.
- Chỉ xóa `work/` khi ứng dụng dừng. Sao lưu video cần giữ trước khi xóa `outputs/`. Dữ liệu/môi trường lớn không được đưa vào Git.

## Quyền riêng tư và phạm vi local

Server giao diện chỉ bind `127.0.0.1`, kiểm tra Host/Origin và không mở CORS. Adapter AI chỉ chấp nhận HTTP localhost/127.0.0.1/::1, không dùng proxy và chặn redirect ra ngoài. Không có telemetry trong mã ứng dụng. ComfyUI do ứng dụng khởi động có `--offline`, `--disable-all-custom-nodes`, offline Hugging Face/Transformers. Ollama do ứng dụng khởi động có `OLLAMA_NO_CLOUD=1`. Ứng dụng kiểm tra /api/show để từ chối model Ollama remote/cloud, và chỉ cho phép danh sách node ComfyUI core xử lý local. Khi dùng server đã chạy từ trước, bạn chịu trách nhiệm cấu hình phần mềm đó chỉ chạy local; đây không phải firewall ngăn mọi chương trình trên PC ra Internet.

Ảnh, prompt và âm thanh nằm trên PC. Cài đặt dùng nguồn chính thức qua HTTPS, xác minh SHA256 của ComfyUI và SHA256 LFS/Git blob của file model theo revision bất biến, lưu hồ sơ ở `models/download-records.json`. Trọng số chưa tải trong cloud do Hugging Face bị chặn; bộ tải được kiểm thử với fixture checksum, chưa xác minh download/suy luận model thật.

## Phát triển / môi trường cloud

```bash
cd /workspace/AI
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py --no-browser --no-services --port 7861
```

Dùng checkout hiện có trong môi trường đã cô lập, không cần Git worktree. Không trình bày URL loopback như web preview cloud.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/selftest.py
# Kiểm thử giao diện, cần Chromium hệ thống:
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/browser-smoke.py --port 7861
# Đóng gói nguồn cho Windows:
.venv/bin/python scripts/package.py
```

Test unittest cần FFmpeg/ffprobe hệ thống. Selftest dùng eSpeak và dựng MP4 20s thật; browser smoke thao tác form, phát video, download byte range, hủy và kiểm tra mobile. Test ComfyUI fixture không phải suy luận AI. Trạng thái cụ thể nằm ở [VALIDATION.md](docs/VALIDATION.md).

[Đánh giá MoneyPrinterTurbo](docs/MoneyPrinterTurbo-review.md) · [Thành phần/giấy phép](docs/THIRD_PARTY.md)

Ứng dụng độc lập, chưa phải fork đầy đủ MoneyPrinterTurbo. Chưa có đăng bài tự động, lấy thông tin sản phẩm tự động, voice cloning, phụ đề từng từ hoặc bảo đảm thu nhập affiliate. Hãy xem lại thông tin, hình ảnh, lời đọc và quyền dùng tư liệu trước khi đăng; thêm nhãn tiếp thị liên kết theo nền tảng.
