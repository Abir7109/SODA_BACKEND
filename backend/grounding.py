import io
from PIL import Image

UIA_AVAILABLE = False
try:
    import uiautomation as auto
    UIA_AVAILABLE = True
except ImportError:
    pass

TESSERACT_AVAILABLE = False
try:
    import pytesseract
    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
except Exception:
    pass

_FILLER = {"the", "a", "an", "button", "icon", "link", "tab", "field", "box",
           "label", "menu", "item", "contact", "name", "with", "in", "on",
           "of", "and", "red", "heart", "emoji", "chat", "list", "left",
           "side", "screen"}


def _keywords(description: str) -> list[str]:
    words = [w for w in description.lower().strip().split() if w not in _FILLER and len(w) > 1]
    return words or [description.lower().strip()]


def _rect_to_dict(ctl) -> dict | None:
    try:
        rect = ctl.BoundingRectangle
        if rect and rect.right > rect.left and rect.bottom > rect.top:
            return {
                "x": (rect.left + rect.right) // 2,
                "y": (rect.top + rect.bottom) // 2,
                "width": rect.right - rect.left,
                "height": rect.bottom - rect.top,
                "matched": ctl.Name,
            }
    except Exception:
        pass
    return None


def _find_by_uia(description: str) -> dict | None:
    """Find element by name via Windows UI Automation. Thread-safe COM init."""
    if not UIA_AVAILABLE:
        return None
    try:
        import pythoncom
        pythoncom.CoInitialize()
        with auto.UIAutomationInitializerInThread():
            kw = _keywords(description)

            def match(name: str) -> int:
                n = name.lower().strip()
                return sum(1 for k in kw if k in n)

            # Search foreground window first
            fg = auto.GetForegroundControl()
            if fg:
                result = _walk(fg, kw, match, depth=0)
                if result:
                    return result

            # Fallback: search all top-level windows
            root = auto.GetRootControl()
            for w in root.GetChildren():
                try:
                    if w.Name:
                        result = _walk(w, kw, match, depth=0)
                        if result:
                            return result
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass
    return None


def _walk(parent, kw, match_fn, depth=0):
    if depth > 8:
        return None
    try:
        children = parent.GetChildren()
    except Exception:
        return None

    best, best_score = None, 0
    for c in children:
        try:
            name = c.Name or ""
            if not name.strip():
                continue
            s = match_fn(name)
            if s >= len(kw):
                r = _rect_to_dict(c)
                if r:
                    return r
            if s > best_score:
                best_score = s
                best = c
        except Exception:
            pass

    # Recurse for better match
    for c in children:
        result = _walk(c, kw, match_fn, depth + 1)
        if result:
            return result

    if best:
        return _rect_to_dict(best)
    return None


# ── OCR fallback ──────────────────────────────────────────────────────

def _ocr_words(screenshot_bytes: bytes) -> list[dict]:
    if not TESSERACT_AVAILABLE:
        return []
    img = Image.open(io.BytesIO(screenshot_bytes))
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    results = []
    for i in range(len(data["text"])):
        text = (data["text"][i] or "").strip()
        if text and int(data["conf"][i] if data["conf"][i] != "-1" else 0) > 30:
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            results.append({
                "text": text,
                "x": x + w // 2,
                "y": y + h // 2,
                "left": x,
                "top": y,
                "width": w,
                "height": h,
            })
    return results


def _ocr_match(description: str, words: list[dict]) -> dict | None:
    kw = _keywords(description)
    best, best_score = None, 0
    for w in words:
        txt = w["text"].lower().strip()
        score = sum(1 for k in kw if k in txt or txt in k)
        if score >= len(kw):
            return w
        if score > best_score:
            best_score = score
            best = w
    return best if best_score > 0 else None


def _expand_rect(match: dict, img_w: int = 0, img_h: int = 0) -> dict:
    """Expand OCR bounding box to cover the likely clickable row area."""
    w = max(match["width"] * 3, 200)
    h = max(match["height"] * 2, 40)
    return {
        "x": match["x"],
        "y": match["y"],
        "width": w,
        "height": h,
    }


def find(screenshot_bytes: bytes, description: str) -> dict:
    # Try uiautomation first — pixel-perfect element finding
    match = _find_by_uia(description)
    if match:
        return {"success": True, **match}

    # Fallback: OCR
    words = _ocr_words(screenshot_bytes)
    match = _ocr_match(description, words)
    if not match:
        return {"success": False, "error": f"Could not find: {description}"}

    # Expand bounding box for clickable area
    expanded = _expand_rect(match)
    return {
        "success": True,
        "x": expanded["x"],
        "y": expanded["y"],
        "width": expanded["width"],
        "height": expanded["height"],
        "matched": match["text"],
    }


def find_text(screenshot_bytes: bytes, text: str) -> dict:
    # Try uiautomation first
    match = _find_by_uia(text)
    if match:
        return {"success": True, **match}

    # Fallback: OCR
    words = _ocr_words(screenshot_bytes)
    exact = [w for w in words if w["text"].lower().strip() == text.lower().strip()]
    if exact:
        w = exact[0]
        return {"success": True, "x": w["x"], "y": w["y"], "width": w["width"], "height": w["height"], "matched": w["text"]}
    match = _ocr_match(text, words)
    if match:
        return {"success": True, "x": match["x"], "y": match["y"], "width": match["width"], "height": match["height"], "matched": match["text"]}
    return {"success": False, "error": f"Text not found: {text}"}
