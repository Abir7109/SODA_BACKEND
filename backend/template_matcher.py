"""
Template matching for SODA using OpenCV (cv2.matchTemplate).
Tier 1.5 vision: <100ms, offline, free — before falling back to Gemini Vision.
"""

import os
import cv2
import numpy as np
try:
    import mss
    HAS_MSS = True
except ImportError:
    mss = None
    HAS_MSS = False
from logger import log


def find_on_screen(template_path, confidence=0.8, region=None):
    """
    Find a template image on screen using OpenCV template matching.

    Args:
        template_path: Path to template PNG file.
        confidence: Match confidence threshold (0.0 - 1.0).
        region: Optional (left, top, width, height) bounding box to restrict search.

    Returns:
        (x, y) center coordinates of best match on the full screen, or None.
    """
    if not os.path.isfile(template_path):
        log.warning(f"[TemplateMatcher] Template not found: {template_path}")
        return None

    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        log.warning(f"[TemplateMatcher] Failed to load template: {template_path}")
        return None

    th, tw = template.shape[:2]

    with mss.mss() as sct:
        if region:
            left, top, width, height = region
            capture = {"left": left, "top": top, "width": width, "height": height}
        else:
            capture = sct.monitors[1]
            left = top = 0
        screenshot = np.array(sct.grab(capture))

    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= confidence:
        cx = max_loc[0] + tw // 2
        cy = max_loc[1] + th // 2
        cx += left
        cy += top
        log.info(f"[TemplateMatcher] Found at ({cx},{cy}) confidence={max_val:.3f}")
        return (cx, cy)

    log.info(f"[TemplateMatcher] Best confidence {max_val:.3f} < {confidence}")
    return None


def capture_template(filepath, region):
    """
    Capture a screen region and save as a grayscale PNG template.

    Args:
        filepath: Output PNG path.
        region: (left, top, width, height).
    """
    left, top, width, height = region
    with mss.mss() as sct:
        capture = {"left": left, "top": top, "width": width, "height": height}
        img = sct.grab(capture)
        mss.tools.to_png(img.rgb, img.size, output=filepath)
    log.info(f"[TemplateMatcher] Saved template: {filepath} ({width}x{height})")
