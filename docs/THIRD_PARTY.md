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
