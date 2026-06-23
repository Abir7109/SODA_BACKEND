import hashlib
import logging
import os
import threading
import time
import wave
from pathlib import Path

from dotenv import load_dotenv
import numpy as np
try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    sd = None
    HAS_SOUNDDEVICE = False

load_dotenv(Path(__file__).resolve().parent / ".env")

log = logging.getLogger("welcome_home")

_welcome_running = False
_welcome_lock = threading.Lock()

# ── Config ────────────────────────────────────────────────────────────────
TTS_ENABLED = os.getenv("WELCOME_TTS_ENABLED", "true").lower() == "true"
TTS_PHRASE = os.getenv(
    "WELCOME_PHRASE",
    "Welcome back, sir. Happy to see you again. Your systems are all online."
)
TTS_AFTER_DELAY = float(os.getenv("WELCOME_TTS_DELAY", "1.0"))
TTS_CACHE_ENABLED = os.getenv("WELCOME_TTS_CACHE", "true").lower() == "true"


# ── Entry Point ───────────────────────────────────────────────────────────

def run_welcome_sequence():
    global _welcome_running
    with _welcome_lock:
        if _welcome_running:
            log.info("Welcome sequence already running, skipping.")
            return
        _welcome_running = True
    try:
        log.info("Welcome sequence starting...")
        if TTS_ENABLED:
            delay = max(0.0, TTS_AFTER_DELAY)
            if delay:
                time.sleep(delay)
            _say_welcome()
        log.info("Welcome sequence complete.")
    except Exception as e:
        log.warning(f"Welcome sequence error: {e}")
    finally:
        with _welcome_lock:
            _welcome_running = False


# ── ElevenLabs TTS with WAV cache ─────────────────────────────────────────

def _elevenlabs_pcm_sample_rate(output_format):
    override = (os.environ.get("ELEVENLABS_PCM_SAMPLE_RATE") or "").strip()
    if override.isdigit():
        return int(override)
    if output_format.startswith("pcm_"):
        try:
            return int(output_format.split("_", maxsplit=1)[1])
        except (ValueError, IndexError):
            pass
    return 24000


def _elevenlabs_env_config():
    voice = (os.environ.get("ELEVENLABS_VOICE_ID") or "").strip()
    model = (os.environ.get("ELEVENLABS_MODEL_ID") or "eleven_multilingual_v2").strip()
    fmt = (os.environ.get("ELEVENLABS_OUTPUT_FORMAT") or "pcm_24000").strip()
    rate = _elevenlabs_pcm_sample_rate(fmt)
    return voice, model, fmt, rate


def _tts_cache_dir():
    base = Path(__file__).resolve().parent
    return base / ".cache" / "welcome_tts"


def _tts_cache_path(text, voice_id, model_id, output_format):
    key = f"{text}|{voice_id}|{model_id}|{output_format}".encode()
    digest = hashlib.sha256(key).hexdigest()[:24]
    return _tts_cache_dir() / f"{digest}.wav"


def _play_pcm_wav_file(path):
    try:
        with wave.open(str(path), "rb") as wf:
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            rate = wf.getframerate()
            if ch != 1 or sw != 2:
                return False
            raw = wf.readframes(wf.getnframes())
    except (OSError, wave.Error):
        return False
    if not raw:
        return False
    pcm_i16 = np.frombuffer(raw, dtype=np.int16)
    pcm_f = pcm_i16.astype(np.float32) / 32768.0
    try:
        sd.play(pcm_f, rate)
        sd.wait()
    except Exception as e:
        log.warning(f"Could not play cached TTS: {e}")
        return False
    return True


def _save_pcm_wav_file(path, pcm_bytes, sample_rate):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with wave.open(str(tmp), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        tmp.replace(path)
    except OSError:
        if tmp.is_file():
            tmp.unlink(missing_ok=True)
        raise


def _play_beep():
    try:
        dur = 0.15
        rate = 48000
        t = np.linspace(0, dur, int(rate * dur), endpoint=False)
        tone = np.sin(2 * np.pi * 660 * t) * 0.3
        fade = np.minimum(t / 0.02, 1.0) * np.minimum((dur - t) / 0.02, 1.0)
        sd.play(tone * fade, rate)
        sd.wait()
    except Exception:
        pass

def _say_welcome():
    text = TTS_PHRASE.strip()
    if not text:
        _play_beep()
        return
    vid, model_id, output_format, pcm_rate = _elevenlabs_env_config()
    if not vid:
        _play_beep()
        return

    cache_path = _tts_cache_path(text, vid, model_id, output_format)
    if TTS_CACHE_ENABLED and cache_path.is_file():
        log.info(f"Playing TTS from cache: {cache_path}")
        if _play_pcm_wav_file(cache_path):
            return
        log.warning("Cache miss; fetching from ElevenLabs.")

    api_key = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
    if not api_key:
        _play_beep()
        return
    try:
        from elevenlabs.client import ElevenLabs
    except ImportError:
        log.warning("elevenlabs not installed. pip install elevenlabs")
        return
    try:
        client = ElevenLabs(api_key=api_key)
        chunks = client.text_to_speech.convert(
            voice_id=vid, text=text, model_id=model_id, output_format=output_format,
        )
        raw = b"".join(chunks)
    except Exception as e:
        log.warning(f"ElevenLabs TTS failed: {e}")
        return
    if not raw:
        return
    if TTS_CACHE_ENABLED:
        try:
            _save_pcm_wav_file(cache_path, raw, pcm_rate)
            log.info(f"Cached TTS: {cache_path}")
        except OSError as e:
            log.warning(f"Could not cache TTS: {e}")
    pcm_i16 = np.frombuffer(raw, dtype=np.int16)
    pcm_f = pcm_i16.astype(np.float32) / 32768.0
    try:
        sd.play(pcm_f, pcm_rate)
        sd.wait()
    except Exception as e:
        log.warning(f"Could not play TTS: {e}")
