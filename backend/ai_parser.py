import os
import json
import re
import hashlib
import time
import io
from datetime import datetime
from typing import Optional, Dict, Any
from functools import lru_cache
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ---- Tesseract path fix ----
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    print("✅ Tesseract found at:", TESSERACT_PATH)
else:
    print("⚠️ Tesseract not found. Image OCR will not work.")
    print("   Install from: https://github.com/UB-Mannheim/tesseract/wiki")

# ---- Groq API setup ----
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is required")

client = Groq(api_key=GROQ_API_KEY)

# ---- Retry with exponential backoff ----
def retry_with_backoff(func, max_retries=3, initial_delay=1):
    """Retry a function with exponential backoff."""
    delay = initial_delay
    last_error = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
    raise last_error

# ---- Cached parsing ----
@lru_cache(maxsize=50)
def parse_receipt_with_groq_cached(text_hash: str, text: str) -> Dict[str, Any]:
    """Cached parsing to avoid duplicate API calls."""
    prompt = """You are a receipt parsing system. Extract data from the receipt text below and return ONLY valid JSON matching this exact schema. No markdown, no explanation, no code fences.

Schema:
{
  "vendor": string,
  "date": string (YYYY-MM-DD),
  "amount": number,
  "category": one of ["meals", "travel", "lodging", "supplies", "software", "other"],
  "description": string
}

If a field cannot be determined, use null. Never omit a field.

Receipt text:
""" + text[:2000]

    def _parse():
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",  # ✅ Working free model
            messages=[
                {"role": "system", "content": "You are a receipt parser. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=300
        )
        content = response.choices[0].message.content
        # Clean up markdown fences
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        return json.loads(content)

    return retry_with_backoff(_parse)

# ---- Image preprocessing ----
def preprocess_image(image: Image) -> Image:
    """Preprocess image for better OCR accuracy."""
    if image.mode != 'L':
        image = image.convert('L')
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)
    image = image.filter(ImageFilter.SHARPEN)
    max_size = 2000
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = tuple(int(dim * ratio) for dim in image.size)
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    return image

def parse_receipt_from_image(image_bytes: bytes) -> str:
    """Extract text with preprocessing."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = preprocess_image(image)
        text = pytesseract.image_to_string(image, config='--psm 6')
        return text.strip()
    except Exception as e:
        return f"OCR Error: {str(e)}"

# ---- Main parse function ----
def parse_receipt(text: Optional[str] = None, image_bytes: Optional[bytes] = None) -> Dict[str, Any]:
    """Main entry point with caching and optimization."""
    raw_text = ""

    if image_bytes:
        raw_text = parse_receipt_from_image(image_bytes)

    if text:
        raw_text = text + "\n" + raw_text if raw_text else text

    if not raw_text.strip():
        return {
            "vendor": None,
            "date": None,
            "amount": None,
            "category": "other",
            "description": None,
            "confidence": 0.0,
            "raw_text": "",
            "error": "No text provided"
        }

    text_hash = hashlib.md5(raw_text.encode()).hexdigest()

    try:
        parsed = parse_receipt_with_groq_cached(text_hash, raw_text[:2000])
    except Exception as e:
        return {
            "vendor": None,
            "date": None,
            "amount": None,
            "category": "other",
            "description": None,
            "confidence": 0.0,
            "raw_text": raw_text[:200],
            "error": f"Parsing failed: {str(e)}"
        }

    # Calculate confidence
    confidence = 0.0
    if parsed.get("vendor"):
        confidence += 0.3
    if parsed.get("date"):
        confidence += 0.3
    if parsed.get("amount") and parsed["amount"] > 0:
        confidence += 0.4

    # Validate date
    if parsed.get("date"):
        try:
            datetime.strptime(parsed["date"], "%Y-%m-%d")
        except ValueError:
            parsed["date"] = None

    return {
        "vendor": parsed.get("vendor"),
        "date": parsed.get("date"),
        "amount": parsed.get("amount"),
        "category": parsed.get("category", "other"),
        "description": parsed.get("description"),
        "confidence": confidence,
        "raw_text": raw_text[:200]
    }