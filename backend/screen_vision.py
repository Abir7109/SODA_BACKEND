import os
import time
import asyncio
from pathlib import Path
from datetime import datetime
from PIL import Image
import io

VISION_DIR = Path("projects/clipboard").resolve()
VISION_DIR.mkdir(parents=True, exist_ok=True)

_OCR_AVAILABLE = False
try:
    import pytesseract
    pytesseract.get_tesseract_version()
    _OCR_AVAILABLE = True
except Exception:
    pass


async def capture_screenshot() -> bytes | None:
    cap = _capture_screenshot_bytes()
    if cap:
        return cap[0]
    return None


def _capture_screenshot_bytes() -> tuple[bytes, int, int] | None:
    try:
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)
            png_bytes = mss.tools.to_png(img.rgb, img.size)
            return png_bytes, img.size[0], img.size[1]
    except Exception as e:
        print(f"[screen_vision] screenshot failed: {e}")
        return None


def _save_screenshot(png_bytes: bytes) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    p = VISION_DIR / f"vision_{ts}.png"
    p.write_bytes(png_bytes)
    return str(p)


def _ocr_image(img_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(img_bytes))
    return pytesseract.image_to_string(img)


async def analyze_screen(prompt: str = "Describe what is on the screen in detail.", model: str = None, screenshot: bytes | None = None) -> dict:
    if screenshot is not None:
        png_bytes = screenshot
    else:
        cap = _capture_screenshot_bytes()
        if not cap:
            return {"success": False, "error": "Screenshot capture failed"}
        png_bytes, w, h = cap

    saved_path = _save_screenshot(png_bytes)

    if not _OCR_AVAILABLE:
        return {"success": False, "error": "Tesseract OCR not available. Install tesseract and pytesseract.", "screenshot": saved_path}

    t0 = time.time()
    try:
        text = await asyncio.to_thread(_ocr_image, png_bytes)
        elapsed_ms = int((time.time() - t0) * 1000)
        return {
            "success": True,
            "prompt": prompt,
            "model": "ocr",
            "analysis": text if text.strip() else "(no text detected on screen)",
            "screenshot": saved_path,
            "width": 0,
            "height": 0,
            "elapsed_ms": elapsed_ms,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "screenshot": saved_path}


async def read_screen_text(model: str = None) -> dict:
    return await analyze_screen(
        prompt="Read all text visible on this screen.",
        model=model,
    )
