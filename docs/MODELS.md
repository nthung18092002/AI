# Chọn model video local

Bản mới thêm **Wan 2.2 I2V A14B GGUF Q4_K_S** bên cạnh Wan 2.2 TI2V 5B. A14B là ứng viên để thử chất lượng chuyển động và chi tiết cao hơn; **chưa có so sánh video thật với prompt Topgia hoặc benchmark RTX 5070 12GB**. Không gọi đây là bản đã khắc phục biến dạng.

## Cài và chọn A14B trên Windows

1. Cập nhật source, giữ nguyên model/dữ liệu cũ, đóng ứng dụng và ComfyUI do ứng dụng mở.
2. Chuẩn bị ít nhất **70GB trống** khi chạy bộ cài. Đây là dung lượng ổ đĩa dự phòng cho toàn profile, không phải VRAM.
3. Chạy `setup-windows.bat -Profile reference-hq` trong CMD/PowerShell tại thư mục tool.
4. Mở `start-windows.bat`, chọn chế độ tham chiếu và **Model tạo chuyển động từ ảnh → Wan 2.2 I2V A14B · GGUF Q4**. Bộ cài không tự chuyển các dự án cũ sang model khác.
5. Chọn **Nháp** để kiểm tra chạy được trước; khi đạt, tạo dự án mới với **Cân bằng** để đánh giá hình. Duyệt ảnh khung cảnh và clip thử từng cảnh trước khi dựng dài. Nháp giảm kích thước/step nên không dùng kết quả nháp để kết luận chất lượng tối đa của model.

Nếu ComfyUI do bạn chạy riêng, cần khởi động lại với loader đã cài: giữ `--disable-all-custom-nodes` và thêm `--whitelist-custom-nodes ComfyUI-GGUF`. Ứng dụng tự thêm cờ này cho bản ComfyUI do nó quản lý. Không cần bật các custom node khác.

## Khác biệt

| | TI2V 5B | I2V A14B Q4 |
|---|---|---|
| Mục tiêu | Nhẹ hơn | Thử nhánh lớn hơn cho chất lượng |
| Trọng số video | Một model 5B | Hai expert 14B, một expert hoạt động mỗi bước |
| Định dạng | FP16 | GGUF Q4_K_S; lượng tử hóa có thể giảm chi tiết so với trọng số gốc |
| Graph ảnh | Wan22ImageToVideoLatent, VAE Wan2.2 48 kênh | WanImageToVideo, VAE Wan2.1 16 kênh |
| Lấy mẫu bản cân bằng | 24 bước | 20 bước, high-noise → low-noise; không dùng LoRA tăng tốc |
| Kích thước sinh bản cân bằng | 576×1024 | 480×832 để hạn chế bộ nhớ |
| Tốc độ frame gốc | 24fps | 16fps theo template; xuất 24fps bằng chuyển frame rate, không sinh thêm chuyển động bằng AI |
| Profile | reference | reference-hq |

Cả hai xuất MP4 720×1280. Upscale không tạo lại chi tiết logo đã mất. Nháp dùng 288×512/16 bước. Đổi model video không tự cải thiện ảnh khung cảnh do Klein dựng: nếu ảnh đầu sai mặt, bao bì hoặc bàn tay, cần làm lại ảnh trước khi sinh video.

## Giới hạn máy 12GB VRAM / 32GB RAM

Hai file Q4 khoảng **8.75GB/file, tổng 17.5GB** (GB thập phân), chưa tính UMT5 khoảng 6.7GB, VAE, activations, Python và Windows. Kích thước file không bằng peak VRAM/RAM. Tool dùng low-VRAM/offload, text encoder CPU, tiled decode và cache-none; không bảo đảm vừa máy. RAM 32GB vẫn có thể thiếu. Không có số phút/render hoặc mức VRAM đã đo để công bố.

Thử một clip ngắn và theo dõi GPU/RAM trong Task Manager. Nếu thiếu bộ nhớ, thử bản Nháp hoặc quay lại 5B; không tự xóa model cũ. Không hạ thêm lượng tử hóa chỉ để chạy mà không kiểm tra chất lượng. Model mạnh hơn vẫn có thể đổi mặt, làm sai giấy/tay/logo; clip nối dài vẫn có thể drift. Đồng bộ môi vẫn là bước riêng.

## Nguồn và khả năng tái hiện

- Model gốc/kiến trúc: [Wan-Video/Wan2.2](https://github.com/Wan-Video/Wan2.2).
- Q4 của cộng đồng, không phải bản GGUF do Wan phát hành trực tiếp: [QuantStack/Wan2.2-I2V-A14B-GGUF](https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF). Metadata đã đối chiếu có cả `HighNoise/Wan2.2-I2V-A14B-HighNoise-Q4_K_S.gguf` và `LowNoise/Wan2.2-I2V-A14B-LowNoise-Q4_K_S.gguf`. Bộ cài phân giải revision bất biến, kiểm SHA256 từng file và lưu bản ghi tải.
- [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF), ghim commit `6ea2651e7df66d7585f6ffee804b20e92fb38b8a`; archive kiểm SHA256 `aad273a0b774684285b4496f6edff7e2293bd29d71ef89926d6861bfdf4947ac`; dependency `gguf==0.19.0`.
- Cấu trúc hai sampler, shift 5, CFG 3.5, chia 10/10 bước, VAE và 16fps đối chiếu nhánh không LoRA của template ComfyUI `video_wan2_2_14B_i2v`.

Không dùng API AI cloud hoặc API key. HTTP loopback chỉ giao tiếp với dịch vụ trên PC; mạng chỉ cần lúc tải phần mềm/model.
