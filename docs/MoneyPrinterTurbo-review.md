# Đánh giá MoneyPrinterTurbo cho yêu cầu local

Nguồn: https://github.com/harry0703/MoneyPrinterTurbo
Commit đã đọc: `6940611cc2791d1ca13b3af7ee893ccd9544b874`.

Đã đọc README, LICENSE, config.example.toml, requirements.txt và các service llm, voice, material. Chưa cài hoặc chạy toàn bộ upstream. Review dựa trên file tại commit trên, không suy ra mọi workflow hoạt động.

## Có thể tận dụng

MIT cho phép sửa, phân phối và dùng thương mại; nếu sao chép mã phải giữ copyright và license. Giấy phép mã không bao gồm quyền dùng trọng số model, nhạc, clip, ảnh hay thương hiệu.

Upstream đã có dựng video, phụ đề, nhạc, tư liệu local, adapter Ollama, các lựa chọn TTS tự host và endpoint sinh ảnh tương thích. Đây là nguồn tham khảo phù hợp cho pipeline video ngắn. Tuy nhiên cấu hình `video_source = "pexels"` và luồng Edge TTS không thỏa điều kiện xử lý hoàn toàn local. Miễn phí/không cần API key không có nghĩa offline.

## Thiết kế áp dụng trong công cụ hiện tại

| Công đoạn | Thành phần local | Trạng thái |
|---|---|---|
| Viết kịch bản | Ollama, gợi ý qwen2.5:3b | Adapter đã thêm; cần tải model và kiểm tra trên PC |
| Sinh cảnh | ComfyUI API workflow | Adapter đã thêm; cần model/workflow do người dùng cài |
| Giữ hình sản phẩm | Ảnh thật + chuyển động | Đã kiểm thử dựng video |
| Lời đọc | Piper / eSpeak / System.Speech / file TTS offline | eSpeak đã thử thực tế; Piper cần tải trọng số và kiểm tra trên PC |
| Dựng, phụ đề, nhạc | FFmpeg trên máy | Đã kiểm thử tích hợp trên Linux |

Công cụ hiện tại vẫn là ứng dụng độc lập, **không phải fork đầy đủ MoneyPrinterTurbo**. Chưa sao chép mã upstream; không nên quảng bá là phiên bản nâng cấp đã hoàn thành. Trước mắt áp dụng kiến trúc nhiều bước, thêm Ollama và giới hạn endpoint AI về loopback. Muốn chuyển toàn bộ sang fork upstream cần giữ license, bổ sung cấu hình local-only và kiểm thử từng đường dẫn dịch vụ để tránh fallback ra cloud.

## RTX 5070 12GB / RAM 32GB

Chạy tuần tự: viết kịch bản → nhả LLM khỏi VRAM → sinh từng cảnh ngắn → FFmpeg dựng trên CPU. Không hứa thời gian sinh hoặc chất lượng trước khi thử model thật. Model video lớn và TTS cùng GPU có thể vượt 12GB. Tổng 20–40 giây được ghép từ nhiều cảnh. Text-to-video không bảo đảm giữ đúng sản phẩm; image-to-video nhận ảnh đã được bổ sung trong luồng tham chiếu mới; chưa có kiểm chứng chất lượng GPU.

## Phần còn thiếu để đạt mục tiêu đầy đủ

Đã bổ sung bộ cài Windows, workflow dựng sẵn Wan/SDXL, TTS tiếng Việt và phụ đề chia theo độ dài từng câu. Những phần chưa xác minh là cài đặt Windows thật, download trọng số và suy luận GPU/Piper; luồng I2V đã được bổ sung nhưng chưa kiểm chứng chất lượng/VRAM. Hiện không có GPU Windows trong môi trường cloud để xác minh các phần này.
