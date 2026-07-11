import os
import io
import json
import base64
import re
from PIL import Image

MODEL = "gemini-2.0-flash"


def _get_client():
    try:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def _resize_for_api(img_bytes: bytes, max_dim: int = 1280) -> tuple[bytes, int, int, int, int]:
    img = Image.open(io.BytesIO(img_bytes))
    ow, oh = img.size
    if max(ow, oh) > max_dim:
        ratio = max_dim / max(ow, oh)
        img = img.resize((int(ow * ratio), int(oh * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), ow, oh, img.size[0], img.size[1]


def _ask_gemini(screenshot_jpeg: str, prompt: str) -> dict:
    client = _get_client()
    if not client:
        return {"error": "GEMINI_API_KEY not set"}
    try:
        import asyncio
        response = asyncio.run(
            client.models.generate_content(
                model=MODEL,
                contents=[
                    {"role": "user", "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/jpeg", "data": screenshot_jpeg}}
                    ]}
                ]
            )
        )
        text = response.text.strip()
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return json.loads(text)
    except Exception as e:
        return {"error": str(e)}


def find(screenshot_bytes: bytes, description: str) -> dict:
    """
    Find a UI element by description on a screenshot.
    Returns {"success": True, "x": int, "y": int, "width": int, "height": int}
    or {"success": False, "error": str}
    """
    jpeg_bytes, orig_w, orig_h, view_w, view_h = _resize_for_api(screenshot_bytes)
    b64 = base64.b64encode(jpeg_bytes).decode("ascii")

    prompt = (
        f"You are looking at a screenshot of a computer screen ({view_w}x{view_h} pixels shown).\n"
        f"Find the UI element described as: '{description}'.\n"
        f"Return ONLY valid JSON: {{\"x\": center_x, \"y\": center_y, \"width\": w, \"height\": h}}\n"
        f"Coordinates must be relative to THIS image ({view_w}x{view_h}).\n"
        f"If you cannot find the element, return {{\"error\": \"not found\"}}.\n"
        f"No other text."
    )

    data = _ask_gemini(b64, prompt)
    if "error" in data:
        return {"success": False, "error": data["error"]}

    if isinstance(data.get("x"), (int, float)):
        scale_x = orig_w / view_w
        scale_y = orig_h / view_h
        return {
            "success": True,
            "x": int(data["x"] * scale_x),
            "y": int(data["y"] * scale_y),
            "width": int(data.get("width", 0) * scale_x),
            "height": int(data.get("height", 0) * scale_y),
        }
    return {"success": False, "error": f"Could not find: {description}"}


def find_text(screenshot_bytes: bytes, text: str) -> dict:
    """
    Find text on screen by OCR using Gemini Vision (more reliable than pytesseract).
    Returns {"success": True, "x": int, "y": int, "width": int, "height": int, "matched": str}
    """
    jpeg_bytes, orig_w, orig_h, view_w, view_h = _resize_for_api(screenshot_bytes)
    b64 = base64.b64encode(jpeg_bytes).decode("ascii")

    prompt = (
        f"Read the text on this screen ({view_w}x{view_h}).\n"
        f"Find the exact text: '{text}'.\n"
        f"Return ONLY valid JSON: {{\"x\": center_x, \"y\": center_y, \"width\": w, \"height\": h, \"matched\": \"exact text found\"}}\n"
        f"Coordinates relative to this image. If not found: {{\"error\": \"not found\"}}.\n"
        f"No other text."
    )

    data = _ask_gemini(b64, prompt)
    if "error" in data:
        return {"success": False, "error": data["error"]}

    if isinstance(data.get("x"), (int, float)):
        scale_x = orig_w / view_w
        scale_y = orig_h / view_h
        return {
            "success": True,
            "x": int(data["x"] * scale_x),
            "y": int(data["y"] * scale_y),
            "width": int(data.get("width", 0) * scale_x),
            "height": int(data.get("height", 0) * scale_y),
            "matched": data.get("matched", text),
        }
    return {"success": False, "error": f"Text not found: {text}"}
