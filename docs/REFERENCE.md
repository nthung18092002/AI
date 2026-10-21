# Luồng ảnh tham chiếu

Bản này sửa việc ảnh sản phẩm bị chèn như một miếng dán. Ảnh thật được upload vào **ComfyUI input**, đi qua **VAEEncode → ReferenceLatent** trong FLUX.2 Klein 4B. Ảnh khung cảnh đầu tiên được dùng thêm làm tham chiếu nhân vật/bối cảnh cho các ảnh sau. Các khung cảnh sau khi người dùng duyệt mới được đưa vào **LoadImage → Wan22ImageToVideoLatent → Wan 2.2 TI2V 5B**. Không dùng lại graph T2V 1.3B, không ảnh đè, không fallback slideshow.

Đây là thay đổi kiến trúc. **Chưa có kết quả sinh model thật được kiểm chứng trên RTX 5070 12GB.** Kiểm thử đường đi ảnh và schema không chứng minh ảnh đẹp, giữ logo hoặc tay đúng giải phẫu. I2V vẫn có thể làm méo chữ/bao bì và đổi mặt. Một ảnh mặt trước cũng không cung cấp hình học miệng gói, mặt bên hoặc cách rút giấy. Không hứa giữ tuyệt đối sản phẩm chỉ nhờ seed hoặc negative prompt.

Có thêm lựa chọn **Wan 2.2 I2V A14B GGUF Q4** để thử chất lượng cao hơn: cài profile `reference-hq`, chọn model trong giao diện trước khi tạo dự án mới. Model này dùng **WanImageToVideo/Wan2.1 VAE**, khác graph/VAE 5B bên dưới. Xem [model, cách cập nhật và giới hạn bộ nhớ](MODELS.md). Các dự án cũ không bị tự đổi model.

## Cập nhật từ bản cũ

1. Đóng ứng dụng và các dịch vụ của nó. Sao lưu code nếu bạn tự sửa.
2. Chép mã nguồn bản mới vào thư mục ứng dụng hiện tại. Giữ `.venv/`, `runtime/`, `models/`, `work/`, `outputs/`; không xóa model/video của bạn.
3. Chạy `setup-windows.bat -Profile reference`. Bộ cài kiểm tra dung lượng và chuẩn bị các model mới, không chỉ đổi tên model cũ. Cần tối thiểu 55GB trống khi bắt đầu cài, khuyến nghị 70GB cho cache/video. Model tải từ nguồn chính thức và kiểm checksum. Nếu nguồn yêu cầu đăng nhập để tải, tải file qua trang chính thức vào đúng vị trí rồi chạy lại; không cần API key để suy luận.
4. Chạy `start-windows.bat`. Chọn **Ảnh tham chiếu → duyệt khung → I2V**.
5. Chọn đúng một ảnh sản phẩm rõ nét, dán prompt có timeline và lời thoại. Ảnh được xử lý local; không gửi tới dịch vụ AI cloud.

## Model mới

Tên và graph dựa trên các template chính thức `image_flux2_klein_image_edit_4b_distilled` và `video_wan2_2_5B_ti2v` đi kèm ComfyUI 0.42.0.

| File | Thư mục trong runtime/ComfyUI/models | Nguồn |
|---|---|---|
| flux-2-klein-4b-fp8.safetensors | diffusion_models | black-forest-labs/FLUX.2-klein-4b-fp8 |
| qwen_3_4b.safetensors | text_encoders | Comfy-Org/z_image_turbo |
| flux2-vae.safetensors | vae | Comfy-Org/flux2-dev |
| wan2.2_ti2v_5B_fp16.safetensors | diffusion_models | Comfy-Org/Wan_2.2_ComfyUI_Repackaged |
| wan2.2_vae.safetensors | vae | Comfy-Org/Wan_2.2_ComfyUI_Repackaged |
| umt5_xxl_fp8_e4m3fn_scaled.safetensors | text_encoders | Comfy-Org/Wan_2.1_ComfyUI_repackaged |

Bộ cài có thể dùng lại UMT5 đã có nếu checksum khớp. `all` là profile cũ Wan 2.1 + SDXL; muốn luồng này phải chọn `reference`. Dùng low-VRAM, cache-none và tiled VAE để giảm áp lực bộ nhớ. Không coi các cờ đó là bằng chứng chạy vừa VRAM. Bản nháp I2V 288×512/16 bước; bản cân bằng 576×1024/24 bước, xuất upscale 720×1280. Tạo từng đoạn tối đa 2–3s rồi dùng khung cuối làm điều kiện đoạn tiếp theo; có thể tích lũy drift khi nối dài, nên cần xem toàn bộ kết quả.

## Đúng lời thoại và thời lượng

- Prompt có các dòng `– 0–5 giây: ... “Lời thoại.”` được phân tích trực tiếp. LLM không viết lại các câu trong ngoặc kép.
- Timeline phải liên tục từ 0. Các mốc 0–5, 5–13, 13–20, 20–28 cho kết quả **28 giây** dù ô thời lượng đang là 30.
- “Không tự thêm chữ trên video” tắt phụ đề đóng vào hình. SRT vẫn được xuất riêng. Checkbox không tự ghi đè lệnh cấm chữ trong prompt.
- Nghe từng đoạn lời đọc trước khi duyệt. Piper hiện dùng voice được cài, chưa xác nhận giới tính/độ tự nhiên trên PC của bạn. Chọn lời đọc nữ tự có nếu voice hiện tại không đúng; không quảng bá mọi voice là nữ tự nhiên.
- Lời đọc tự sinh được giữ nguyên câu, chỉ tăng tốc tối đa 1.35 lần nếu cần. Quá mức sẽ báo lỗi để chỉnh timeline/giọng; không tự cắt chữ. File lời đọc tự tải lên chưa được ASR kiểm tra trùng văn bản.

## Quy trình duyệt

1. **Chuẩn bị khung cảnh**: tạo/lưu ảnh và lời đọc. Kiểm tra toàn bộ ảnh ở độ lớn đầy đủ; không duyệt bao bì/chữ/nhân vật sai.
2. **Duyệt các khung**: chọn checkbox từng cảnh. Server gắn phê duyệt với checksum file; đổi ảnh phải duyệt lại.
3. **Thử chuyển động mỗi cảnh**: tạo tối đa 3s/cảnh từ ảnh đã duyệt. Clip thử hiện **chỉ kiểm tra hình**, chưa lip-sync. Soát tay, gương mặt, chữ và cách di chuyển. Không tốt thì không duyệt và không dựng dài. Có thể tạo lại dự án với ảnh/prompt/seed khác.
4. **Duyệt chuyển động**: chọn các clip đạt. Khi dựng dài, giữ nguyên các đoạn thử đã duyệt rồi tiếp tục từ khung cuối; không sinh lại đoạn mở đầu đã chọn. Giữ nguyên đoạn mở đầu không bảo đảm phần nối tiếp không bị drift.
5. **Dựng toàn bộ**: tạo phần còn lại, xử lý lời đọc/lip-sync nếu có, ghép nhạc. Bản xuất kiểm tra số frame trước khi công bố. Không lặp clip hoặc giữ khung cuối để giả lập đủ chuyển động trong luồng tham chiếu.

Dự án nằm ở `work/projects/<id>/`. Lịch sử mở lại được qua giao diện. Chưa hỗ trợ sửa pose trên canvas hoặc resume một tác vụ GPU bị đóng giữa chừng. Muốn đổi ảnh khung hiện tại phải tạo lại/duyệt lại, không sửa file dưới dự án đang chạy. Chỉ mở một instance ứng dụng cùng lúc vì lịch sử/dịch vụ dùng chung thư mục.

## Lip-sync local: phần cài riêng, chưa xác nhận Windows/5070

Wan I2V không tự khớp môi với WAV. Prompt có yêu cầu khớp môi giữ nguyên yêu cầu đó; thiếu backend sẽ **chặn xuất toàn bộ**, không âm thầm đổi thành voiceover. Người dùng có thể chủ động đổi **Hình thức lời đọc cho bản xuất → Lồng tiếng, không khớp môi**; lựa chọn được ghi trong JSON, không làm lại ảnh/clip đã duyệt.

Có adapter gọi **MuseTalk v1.5** local qua Python subprocess, dùng đúng WAV của từng cảnh. Không gửi video/âm thanh ra API dịch vụ. Adapter kiểm tra file model, kết quả, decode và số frame; không tạo giả output khi MuseTalk lỗi. Cấu hình tồn tại không chứng minh dependency/GPU đã chạy được hoặc môi đã đúng.

MuseTalk **chưa được tự cài bởi profile reference**. Cài một môi trường MuseTalk đã chạy được theo dự án chính thức: https://github.com/TMElyralab/MuseTalk . Upstream hướng dẫn các bản PyTorch/CUDA và MMLab cũ; không áp dụng mù quáng các bản đó cho RTX 50. Cần xác minh môi trường có hỗ trợ Blackwell, face detector và weights đầy đủ. Chưa có công thức cài MuseTalk Windows/RTX 5070 được kiểm chứng trong dự án này.

Nếu đã có một bản MuseTalk hoạt động, tạo `lipsync.json` ở gốc ứng dụng:

```json
{
  "directory": "D:/MuseTalk",
  "python": "D:/MuseTalk/.venv/Scripts/python.exe"
}
```

Cần các file inference và model theo layout upstream: `models/musetalkV15/{musetalk.json,unet.pth}`, Whisper tiny, sd-vae, dwpose và face-parse-bisent. Xem danh sách thiếu trong **Kiểm tra lại → thông tin hệ thống**. Nếu khuôn mặt không thấy hoặc không detect được, job có thể thất bại. Kết quả lip-sync còn cần nghe/xem lại, chưa có đánh giá khách quan đồng bộ môi cho tiếng Việt hoặc cơ chế bảo toàn tuyệt đối identity/bao bì.

Vì thiếu GPU và model thật trong cloud, **chưa thể xác nhận tool đáp ứng đầy đủ prompt người thật cầm/rút/lau giấy, logo nguyên vẹn và khớp môi chính xác**. Mục đích bản sửa là thay đường đi ảnh sai và chặn các kết quả giả thành công, không gắn nhãn một video chưa đạt thành hoàn chỉnh.
