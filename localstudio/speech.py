"""All speech runs in-process on CPU. Never contacts an external TTS server."""
import ctypes
import math
from pathlib import Path
import struct
import threading
import wave

SPEECH_LOCK = threading.Lock()
VOICE_CACHE = {}


def wave_seconds(path):
    with wave.open(str(path), 'rb') as wav:
        return wav.getnframes() / wav.getframerate()


def piper_speech(text, output, model):
    model = Path(model)
    if not model.is_file() or not Path(str(model) + '.json').is_file():
        raise RuntimeError('Chưa có model Piper tiếng Việt. Chạy setup-windows.bat hoặc chọn giọng eSpeak offline.')
    import onnxruntime
    onnxruntime.disable_telemetry_events()
    from piper import PiperVoice
    with SPEECH_LOCK:
        key = str(model.resolve())
        if key not in VOICE_CACHE:
            VOICE_CACHE[key] = PiperVoice.load(str(model), use_cuda=False)
        with wave.open(str(output), 'wb') as wav:
            VOICE_CACHE[key].synthesize_wav(text, wav)
    if wave_seconds(output) < 0.05:
        raise RuntimeError('Piper trả về âm thanh rỗng.')


def espeak_speech(text, output):
    """Bundled eSpeak NG, Vietnamese voice. Robotic but usable without weights."""
    import espeakng_loader
    with SPEECH_LOCK:
        lib = espeakng_loader.load_library()
        lib.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        lib.espeak_Initialize.restype = ctypes.c_int
        lib.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]
        lib.espeak_SetParameter.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        lib.espeak_Synth.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_int, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        callback_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)
        lib.espeak_SetSynthCallback.argtypes = [callback_type]
        rate = lib.espeak_Initialize(2, 0, str(espeakng_loader.get_data_path()).encode(), 0)
        if rate <= 0:
            raise RuntimeError('Không khởi tạo được eSpeak NG.')
        chunks = []
        @callback_type
        def collect(samples, count, events):
            if samples and count > 0:
                chunks.append(ctypes.string_at(samples, count * 2))
            return 0
        lib.espeak_SetSynthCallback(collect)
        try:
            if lib.espeak_SetVoiceByName(b'vi') != 0:
                raise RuntimeError('Không tìm thấy voice tiếng Việt trong eSpeak NG.')
            lib.espeak_SetParameter(1, 165, 0)  # words per minute
            encoded = text.encode('utf-8') + b'\0'
            buf = ctypes.create_string_buffer(encoded)
            if lib.espeak_Synth(buf, len(encoded), 0, 1, 0, 1, None, None) != 0:
                raise RuntimeError('eSpeak NG không tạo được lời đọc.')
            lib.espeak_Synchronize()
        finally:
            lib.espeak_Terminate()
        with wave.open(str(output), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(b''.join(chunks))
    if wave_seconds(output) < 0.05:
        raise RuntimeError('eSpeak NG trả về âm thanh rỗng.')


def ambient_music(output, seconds):
    """A deterministic, original soft chord bed; not AI-generated music."""
    rate = 16000
    chords = [(130.81, 164.81, 196), (110, 130.81, 164.81), (87.31, 110, 130.81), (98, 123.47, 146.83)]
    with wave.open(str(output), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        for second in range(seconds):
            samples = bytearray()
            frequencies = chords[(second // 4) % len(chords)]
            for n in range(rate):
                t = second + n / rate
                envelope = min(1, t / 1.5, (seconds - t) / 1.5) * (0.7 + 0.3 * math.sin(math.pi * (t % 4) / 4))
                value = sum(math.sin(2 * math.pi * f * t) + .15 * math.sin(4 * math.pi * f * t) for f in frequencies) / 3
                samples.extend(struct.pack('<h', int(value * envelope * 4800)))
            wav.writeframes(samples)
