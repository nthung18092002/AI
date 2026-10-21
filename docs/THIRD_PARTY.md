# Thành phần bên ngoài

Mã của Local Affiliate Studio được cung cấp theo LICENSE ở gốc. Ứng dụng hiện là mã độc lập; đã tham khảo kiến trúc MoneyPrinterTurbo nhưng không chép mã upstream. Nếu sau này tích hợp mã upstream, phải giữ copyright/license MIT của Harry.

Các thành phần cài riêng có giấy phép riêng, không được đổi thành MIT chỉ vì phần giao diện này dùng MIT:

- ComfyUI: https://github.com/Comfy-Org/ComfyUI — giấy phép trong source cài ở runtime/ComfyUI/LICENSE. Bản nguồn được ghim commit, tải từ GitHub và kiểm tra SHA256.
- Ollama: https://github.com/ollama/ollama . Model Qwen2.5:3b được cài bằng Ollama; xem giấy phép/tag model tại https://ollama.com/library/qwen2.5:3b trước khi phân phối model.
- Wan 2.1: https://github.com/Wan-Video/Wan2.1 ; trọng số đóng gói cho ComfyUI: https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged . Giấy phép model và điều khoản upstream áp dụng riêng.
- SDXL: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0 — xem model card và giấy phép model.
- Piper 1.4.2: https://github.com/OHF-Voice/piper1-gpl — GPL-3.0. Voice được tải riêng từ https://huggingface.co/rhasspy/piper-voices ; bộ cài lưu MODEL_CARD tại models/piper/MODEL_CARD. Chưa đọc được card ở môi trường cloud bị chặn Hugging Face; không xác nhận quyền thương mại của voice dựa trên giấy phép engine. Bạn có thể chọn eSpeak hoặc lời đọc tự có.
- eSpeak NG và dữ liệu giọng: https://github.com/espeak-ng/espeak-ng — GPL-3.0. espeakng-loader đóng gói thư viện/data và có metadata giấy phép trong package.
- FFmpeg, imageio-ffmpeg: giấy phép tùy build và các codec đi kèm. Sản phẩm dùng libx264 và libass; xem license đi kèm binary, đặc biệt nếu phân phối lại binary.
- Pillow, PyTorch, torchvision, ONNX Runtime, Playwright và các dependency khác giữ giấy phép upstream.

ZIP nguồn do công cụ đóng gói không kèm binary, trọng số model hoặc các môi trường Python. Bộ cài tải từng thành phần từ nguồn chính thức. Đây không phải xác nhận quyền sử dụng mọi tư liệu, voice hay sản phẩm cho quảng cáo thương mại.

Luồng tham chiếu mới thêm FLUX.2 Klein 4B fp8 (`black-forest-labs/FLUX.2-klein-4b-fp8`), Qwen3 4B tokenizer/encoder từ Comfy-Org/z_image_turbo, VAE từ Comfy-Org/flux2-dev và Wan2.2 TI2V5B/VAE từ Comfy-Org/Wan_2.2_ComfyUI_Repackaged. Tên file dựa trên template ComfyUI chính thức. Kiểm tra model card/giấy phép tại nguồn trước khi sử dụng/phân phối; chưa tải các trọng số này trong cloud.

Adapter MuseTalk không sao chép mã upstream, gọi bản cài local của người dùng. Source/weights/dependency của MuseTalk có điều khoản riêng. Công thức upstream dùng CUDA/MMLab cũ chưa được dự án này xác minh cho RTX 5070. Có adapter không có nghĩa bản cài GPU đã hoạt động hoặc khớp môi đã đạt.

Profile reference-hq thêm Wan2.2 I2V A14B với bản lượng tử hóa cộng đồng [QuantStack/Wan2.2-I2V-A14B-GGUF](https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF); điều khoản model gốc Wan và thông tin bản repack áp dụng riêng. Loader [city96/ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) Apache-2.0 cài tách trong runtime, giữ LICENSE upstream, ghim commit và SHA256 archive; không đưa source/binary của loader vào ZIP ứng dụng. Dependency gguf và các dependency khác giữ giấy phép riêng. [Chi tiết phiên bản và graph](MODELS.md).
