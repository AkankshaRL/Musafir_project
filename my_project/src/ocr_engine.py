from paddleocr import PaddleOCR
import json

ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False
)

def extract_text_from_image(image_path: str) -> dict:
    try:
        result = ocr.predict(image_path)

        # Convert to Python-native list/dict if result is an OCRResult object
        if not isinstance(result, list):
            try:
                result = json.loads(json.dumps(result, default=lambda o: o.__dict__))
            except:
                result = [result]

        full_text = ""
        boxes = []

        # ---- CASE 1: New style output ----
        for res in result:
            if isinstance(res, dict) and "content" in res:
                for item in res["content"]:
                    text = item.get("text", "")
                    box = item.get("box", [])
                    score = item.get("score", 1.0)

                    full_text += text + " "
                    boxes.append(_poly_to_bbox(text, box, score))
                continue

            # ---- CASE 2: Older output formats ----
            if isinstance(res, dict) and "rec_text" in res:
                for text, box, score in zip(
                    res["rec_text"], res["boxes"], res["rec_scores"]
                ):
                    full_text += text + " "
                    boxes.append(_poly_to_bbox(text, box, score))
                continue

            # ---- CASE 3: Fallback for unknown PaddleOCR format ----
            # Try to find ANY text-like fields
            if isinstance(res, dict):
                flat_text = _extract_text_from_unknown(res)
                full_text += flat_text + " "

        return {
            "page": 0,
            "text": full_text.strip(),
            "boxes": boxes,
            "total_boxes": len(boxes)
        }

    except Exception as e:
        return {
            "page": 0,
            "text": "",
            "boxes": [],
            "error": str(e)
        }


def _poly_to_bbox(text, box, score):
    """Convert polygon to a bounding box safely."""
    try:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        return {
            "text": text,
            "x": int(min(xs)),
            "y": int(min(ys)),
            "w": int(max(xs) - min(xs)),
            "h": int(max(ys) - min(ys)),
            "conf": float(score),
        }
    except:
        return {"text": text, "x": 0, "y": 0, "w": 0, "h": 0, "conf": float(score)}


def _extract_text_from_unknown(obj):
    """Recursively extract any string values from unknown structures."""
    text = ""

    if isinstance(obj, dict):
        for v in obj.values():
            text += _extract_text_from_unknown(v) + " "

    elif isinstance(obj, list):
        for item in obj:
            text += _extract_text_from_unknown(item) + " "

    elif isinstance(obj, str):
        return obj

    return text.strip()
