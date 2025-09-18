#!/usr/bin/env python3
# LM Studio JSON-robust analyzer (json_schema mode)
# Requires: requests, pillow; ffmpeg in PATH

import os, sys, json, base64, subprocess, re
from pathlib import Path
import requests
from PIL import Image

LMSTUDIO_URL   = os.getenv("LMSTUDIO_URL", "http://localhost:1234/v1/chat/completions")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "llama3-llava-next-8b:2")
TIMEOUT_S      = float(os.getenv("LM_TIMEOUT", "120"))
DEBUG_LOG      = os.getenv("LM_DEBUG", "0") == "1"

DEFAULT_META_DIRS = [
    Path(os.getenv("META_DIR")) if os.getenv("META_DIR") else None,
    Path("E:/n8n-docker/data/meta"),
    Path("D:/n8n-docker/data/meta"),
    Path("C:/n8n-docker/data/meta"),
    Path.cwd() / "meta",
]
META_DIR = next((p for p in DEFAULT_META_DIRS if p and (p.parent.exists() or not p.exists())), Path.cwd() / "meta")
META_DIR.mkdir(parents=True, exist_ok=True)

TMP_DIR = Path(os.getenv("TMP_DIR", "E:/n8n-docker/data/tmp"))
if not TMP_DIR.parent.exists():
    TMP_DIR = Path.cwd() / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

VIDEO = Path(sys.argv[1]).resolve()
BASE  = VIDEO.stem
START_JPG = TMP_DIR / f"{BASE}_start.jpg"
END_JPG   = TMP_DIR / f"{BASE}_end.jpg"

SYS_PROMPT = (
    "You are a meticulous film editor. Analyze a single image and return JSON ONLY matching the schema. "
    "No markdown, no code fences, no explanations."
)

# JSON Schema for LM Studio `response_format: json_schema`
JSON_SCHEMA = {
    "name": "frame_analysis",
    "schema": {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "action": {"type": "string"},
            "motion": {"type": "string"},
            "lighting": {"type": "string"},
            "tone": {"type": "string"},
            "scene_type": {"type": "string"},
            "dominant_colors": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 3
            }
        },
        "required": ["subject","action","motion","lighting","tone","scene_type","dominant_colors"],
        "additionalProperties": False
    }
}

def ffmpeg_extract_frames(video_path: Path, start_out: Path, end_out: Path):
    for args in (
        ["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(video_path),"-frames:v","1",str(start_out)],
        ["ffmpeg","-hide_banner","-loglevel","error","-y","-sseof","-1","-i",str(video_path),"-frames:v","1",str(end_out)],
    ):
        subprocess.run(args, check=True)

def img_to_data_url(p: Path) -> str:
    im = Image.open(p).convert("RGB")
    im.thumbnail((1024, 1024))
    buf = TMP_DIR / f"resized_{p.name}"
    im.save(buf, format="JPEG", quality=90)
    b64 = base64.b64encode(buf.read_bytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"

def extract_json_block(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    # Try balanced object
    depth = 0; start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0: start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                blk = text[start:i+1]
                try:
                    json.loads(blk)
                    return blk
                except Exception:
                    pass
    # Fallback: first {...} via regex
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return m.group(0)
    return text

def call_lmstudio(image_data_url: str) -> dict:
    payload = {
        "model": LMSTUDIO_MODEL,
        "temperature": 0,
        "response_format": {
            "type": "json_schema",
            "json_schema": JSON_SCHEMA
        },
        "messages": [
            {"role": "system", "content": SYS_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this frame and return JSON only."},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ],
    }
    r = requests.post(LMSTUDIO_URL, json=payload, timeout=TIMEOUT_S)
    r.raise_for_status()
    data = r.json()

    # Most OpenAI-compatible servers return string content; some may include a parsed form.
    msg = data["choices"][0]["message"]
    content = msg.get("content")
    if content is None and "parsed" in msg:
        # Some servers provide structured `parsed` when using json_schema
        return msg["parsed"]

    if DEBUG_LOG:
        (TMP_DIR / "lmstudio_raw.txt").write_text(str(content), encoding="utf-8")

    cleaned = extract_json_block(content if isinstance(content, str) else json.dumps(content))
    return json.loads(cleaned)

def main():
    ffmpeg_extract_frames(VIDEO, START_JPG, END_JPG)
    start_url = img_to_data_url(START_JPG)
    end_url   = img_to_data_url(END_JPG)

    start_json = call_lmstudio(start_url)
    end_json   = call_lmstudio(end_url)

    out = {
        "file": str(VIDEO),
        "base": BASE,
        "start": start_json,
        "end": end_json,
    }

    out_path = META_DIR / f"{BASE}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"ok": True, "file": str(VIDEO), "meta": str(out_path), "data": out}))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Usage: analyze_clip.py <video_path>"})); sys.exit(1)
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(json.dumps({"ok": False, "error": f"ffmpeg failed: {e}"})); sys.exit(2)
    except requests.HTTPError as e:
        print(json.dumps({"ok": False, "error": f"HTTP {e.response.status_code}: {e.response.text[:300]}"})); sys.exit(3)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)})); sys.exit(4)
