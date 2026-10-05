"""
Shorts Maker - type an idea, get a finished YouTube Short.

What it does for every video:
  1. An open-source AI model (via Ollama) writes the script and picks a visual for each scene.
  2. A voice reads the script out loud.
  3. Pictures for each scene: either real stock footage (free, from Pexels) or AI images
     painted on your own computer by an open-source model.
  4. Big word-by-word captions and slow camera moves are added, and everything is stitched
     into a vertical 9:16 video.

Use it from the web page (run app.py or double-click "Start Shorts Maker.bat"),
or from the command line:

    python shorts_maker.py "3 weird facts about octopuses"
    python shorts_maker.py --demo

License: MIT (see LICENSE)
"""

import argparse
import asyncio
import functools
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

try:  # use the Windows certificate store, so downloads work behind antivirus/VPN/school/work HTTPS scanning
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

import ai_images

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(HERE, "output")
# Settings (including your API keys) live in your user folder, not in the app folder, so a new copy or
# an update of the app finds them automatically. Older versions kept settings.json next to the app.
SETTINGS_DIR = os.environ.get("SHORTS_SETTINGS_DIR") or os.path.join(os.path.expanduser("~"), ".shorts-maker")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")
OLD_SETTINGS_FILE = os.path.join(HERE, "settings.json")

WIDTH, HEIGHT, FPS = 1080, 1920, 30
CAPTION_Y, CAPTION_H = 1290, 300  # captions sit low and centered, just above where YouTube draws the title and buttons
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
CLAUDE_MODEL = "claude-sonnet-5-5"  # only used with --engine claude

HIGHLIGHT = (255, 214, 10)  # yellow for the word being spoken
GRADIENTS = [  # backgrounds used when no stock footage is available
    ((20, 24, 82), (88, 28, 135)),
    ((7, 89, 133), (21, 128, 61)),
    ((127, 29, 29), (30, 27, 75)),
    ((15, 23, 42), (14, 116, 144)),
]


class PipelineError(Exception):
    """A problem we can explain to the user in plain words."""


# --------------------------------------------------------------------------- settings

DEFAULT_SETTINGS = {
    "pexels_key": "",
    "pixabay_key": "",
    "ollama_model": "llama3.2",
    "ollama_url": "http://localhost:11434",
    "voice": "en-US-GuyNeural",
    "visual_mode": "stock",          # "stock" (Pexels) or "ai_images" (made on your computer)
    "intro_button": "subscribe",  # "subscribe", "follow" or "both"
    "ai_image_quality": "standard",  # "fast", "standard" or "high"
    "video_seconds": "45",           # how long the finished video should be (30 to 90)
    "image_style": "auto",           # a key of IMAGE_STYLES, or "auto" to let the script decide
}

# The looks you can pick for AI pictures: key -> (name shown on the page, words given to the picture model)
IMAGE_STYLES = {
    "photo": ("Photorealistic", "ultra realistic photograph, natural light, sharp detail, 35mm lens"),
    "cinematic": ("Cinematic film", "cinematic film still, dramatic lighting, shallow depth of field, rich color grading"),
    "illustration": ("Digital illustration", "polished digital illustration, bold shapes, vibrant colors, clean lines"),
    "anime": ("Anime", "anime style illustration, expressive, soft cel shading, vivid colors, detailed background"),
    "render3d": ("3D render", "stylized 3D render, soft studio lighting, smooth materials, high detail"),
    "watercolor": ("Watercolor", "watercolor painting, soft washes of color, paper texture, delicate brush strokes"),
    "comic": ("Comic book", "comic book art, bold ink outlines, halftone shading, dynamic composition, bright colors"),
    "moody": ("Dark and moody", "dark moody atmosphere, low key lighting, deep shadows, subtle fog, muted colors"),
    "neon": ("Neon cyberpunk", "neon cyberpunk, glowing lights, wet streets, magenta and cyan colors, futuristic"),
    "vintage": ("Vintage film", "vintage film photograph, faded colors, film grain, warm nostalgic tones"),
    "flat": ("Flat vector", "flat vector illustration, simple geometric shapes, limited color palette, minimal"),
}

MIN_SECONDS, MAX_SECONDS = 30, 90
WORDS_PER_SECOND = 2.5  # how fast the voices speak, roughly


def clamp_seconds(value):
    try:
        return max(MIN_SECONDS, min(MAX_SECONDS, int(float(value))))
    except (TypeError, ValueError):
        return 45


def length_plan(seconds):
    """How many scenes and words a script needs to fill that many seconds."""
    seconds = clamp_seconds(seconds)
    words = round(seconds * WORDS_PER_SECOND)
    scenes = max(4, min(12, round(seconds / 7.5)))
    return {"seconds": seconds, "words": words, "words_lo": int(words * 0.9), "words_hi": int(words * 1.1),
            "scenes_lo": max(3, scenes - 1), "scenes_hi": min(12, scenes + 1)}


def _migrate_old_settings():
    """First run after the move: bring over a settings.json (and keys) saved next to the app."""
    if os.path.exists(OLD_SETTINGS_FILE) and not os.path.exists(SETTINGS_FILE):
        try:
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            with open(OLD_SETTINGS_FILE, encoding="utf-8") as f:
                data = f.read()
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                f.write(data)
        except OSError:
            pass


def load_settings():
    s = dict(DEFAULT_SETTINGS)
    for key, env in (("pexels_key", "PEXELS_API_KEY"), ("pixabay_key", "PIXABAY_API_KEY"),
                     ("ollama_model", "OLLAMA_MODEL"),
                     ("ollama_url", "OLLAMA_URL")):
        if os.environ.get(env):
            s[key] = os.environ[env]
    _migrate_old_settings()
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            saved = json.load(f)
        s.update({k: v for k, v in saved.items() if k in DEFAULT_SETTINGS and v})
    except (OSError, ValueError):
        pass
    return s


def save_settings(updates):
    _migrate_old_settings()
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            saved = json.load(f)
    except (OSError, ValueError):
        saved = {}
    saved.update({k: str(v).strip() for k, v in updates.items() if k in DEFAULT_SETTINGS})
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(saved, f, indent=2)


# --------------------------------------------------------------------------- script writing

DEFAULT_LOOK = "cinematic photography, dramatic lighting, rich colors, sharp detail"

DEMO_SCRIPT = {
    "title": "3 Weird Octopus Facts #shorts",
    "description": "Three strange facts about octopuses. #shorts #octopus #facts",
    "visual_style": "cinematic underwater photography, deep blue light, sharp detail",
    "scenes": [
        {"narration": "Octopuses are wild. Here are three facts that sound fake but are true.",
         "visual_query": "octopus underwater",
         "image_prompt": "A large octopus drifting above a dark coral reef, shafts of blue light from the surface"},
        {"narration": "First, an octopus has three hearts. Two pump blood to the gills, and one to the body.",
         "visual_query": "octopus swimming ocean",
         "image_prompt": "Close-up of an octopus with a soft red glow inside its body, dark water around it"},
        {"narration": "Second, their blood is blue, because it uses copper instead of iron to carry oxygen.",
         "visual_query": "blue ocean waves",
         "image_prompt": "Deep blue ocean water with bright glowing blue swirls flowing like liquid"},
        {"narration": "Third, an octopus can squeeze through any gap bigger than its beak. Follow for more!",
         "visual_query": "octopus coral reef",
         "image_prompt": "An octopus squeezing its soft body through a narrow crack in a rock, coral all around"},
    ],
}

PROMPT = """You write scripts for YouTube Shorts (vertical videos, about {seconds} seconds long).

Idea: {topic}
{style}
Return ONLY valid JSON with this exact shape:
{{
  "title": "catchy title under 70 characters, ending with #shorts",
  "description": "1-2 sentences plus 3-5 hashtags",
  "visual_style": "a short phrase giving every picture the same look, e.g. 'cinematic photography, moody lighting' or 'bold flat illustration, bright colors'",
  "scenes": [
    {{"narration": "what the voice says (1-2 short sentences)",
      "visual_query": "2-4 English words describing something concrete a camera could film",
      "image_prompt": "one detailed sentence describing the picture for this scene: the subject, the setting, the lighting and the mood"}}
  ]
}}

Rules:
- {scenes_lo} to {scenes_hi} scenes. Scene 1 must be a strong hook that grabs attention in the first 3 seconds.
- The last scene invites viewers to follow or comment.
- Conversational, accurate, no filler. Total narration must be {words_lo} to {words_hi} words (about {seconds} seconds when spoken).
- visual_query must be a concrete, filmable thing like "octopus swimming underwater",
  "city traffic at night" or "hands typing laptop". Never an abstract idea like "curiosity" or "success".
  Each scene should have a different visual_query.
- image_prompt must show something concrete and visible, and never include words, letters or logos.
  Even in the last scene (the follow or comment one), image_prompt and visual_query must show the video's
  subject, never a screen, button, speech bubble, bell, thumbs-up or subscribe icon."""


def _first_json(text):
    """Find the first complete {...} block in a reply, even when there is chatter around it."""
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for k in range(start, len(text)):
            ch = text[k]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:k + 1])
                    except ValueError:
                        break
        start = text.find("{", start + 1)
    raise ValueError("no usable JSON found in the reply")


def parse_script(text):
    """Pull the JSON out of a model's reply and check it has what we need. Forgiving on purpose:
    small models often rename keys or wrap things oddly."""
    text = re.sub(r"```(?:json)?", "", text)
    return clean_script(_first_json(text))


def clean_script(data):
    """Check a script (from the model or from the page's editor) and tidy it up."""
    if not isinstance(data, dict):
        raise ValueError("the script isn't in the right shape")
    raw = data.get("scenes")
    if raw is None:  # a different key name for the list
        raw = next((v for v in data.values() if isinstance(v, list) and v and isinstance(v[0], (dict, str))), None)
    if not isinstance(raw, list):
        raise ValueError("no list of scenes")
    scenes = []
    for s in raw:
        if isinstance(s, str):
            s = {"narration": s}
        if not isinstance(s, dict):
            continue
        narration = s.get("narration") or s.get("text") or s.get("voiceover") or s.get("script") or ""
        if isinstance(narration, list):
            narration = " ".join(str(x) for x in narration)
        narration = str(narration).strip()
        if narration:
            style_key = s.get("style") if s.get("style") in IMAGE_STYLES else ""
            scenes.append({"narration": narration,
                           "visual_query": str(s.get("visual_query") or s.get("visual") or "").strip(),
                           "image_prompt": str(s.get("image_prompt") or "").strip(),
                           "style": style_key, "fresh": bool(s.get("fresh"))})
    if len(scenes) < 2:
        raise ValueError("too few scenes")
    scenes = scenes[:14]
    return {
        "title": str(data.get("title") or "My Short #shorts").strip(),
        "description": str(data.get("description") or "#shorts").strip(),
        "visual_style": str(data.get("visual_style") or DEFAULT_LOOK).strip(),
        "scenes": scenes,
    }


HOOK_PROMPT = """You write the opening lines (the "hook") of YouTube Shorts. The first 3 seconds decide whether people keep watching.

Video idea: {topic}
{current}
Write 5 different hooks, each a different type, each 8 to 20 words, spoken out loud, with no hashtags or emojis:
1. A surprising question
2. A bold claim
3. A shocking fact or number
4. A short story opener ("Last week...", "Nobody told me...")
5. A direct challenge or promise to the viewer

Return ONLY valid JSON: {{"hooks": [{{"type": "Question", "text": "..."}}, {{"type": "Bold claim", "text": "..."}}, {{"type": "Shocking fact", "text": "..."}}, {{"type": "Story", "text": "..."}}, {{"type": "Challenge", "text": "..."}}]}}"""


def suggest_hooks(topic, script, settings, engine="ollama"):
    """Ask the model for a handful of alternative opening lines. Returns [{"type", "text"}]."""
    ask = ask_ollama if engine == "ollama" else ask_claude
    current = ""
    if script and script.get("scenes"):
        current = ("The rest of the script, for context: " +
                   " ".join(sc["narration"] for sc in script["scenes"][1:4])[:500] + "\n")
    prompt = HOOK_PROMPT.format(topic=topic or (script or {}).get("title", "this video"), current=current)
    last = "no reply"
    for _ in range(3):
        try:
            data = _first_json(re.sub(r"```(?:json)?", "", ask(prompt, settings)))
            raw = data.get("hooks")
            if raw is None:
                raw = next((v for v in data.values() if isinstance(v, list)), None)
            hooks = []
            for h in raw or []:
                if isinstance(h, str):
                    h = {"type": "Hook", "text": h}
                text = str(h.get("text") or h.get("hook") or "").strip().strip('"')
                if text:
                    hooks.append({"type": str(h.get("type") or "Hook").strip()[:24], "text": text})
            if hooks:
                return hooks[:6]
            last = "no hooks in the reply"
        except (ValueError, KeyError, TypeError, AttributeError) as err:
            last = str(err)
    raise PipelineError(f"The AI model couldn't come up with hooks ({last}). Try again.")


def script_from_prose(text, topic):
    """Last resort: the model ignored the JSON format but wrote a script. Turn its sentences into scenes."""
    text = re.sub(r"```\w*|[*#_>]+", " ", text)
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", " ".join(text.split())) if len(x.split()) >= 4]
    if len(sentences) < 3:
        raise ValueError("reply too short to use")
    scenes, buf = [], ""
    for sent in sentences[:14]:
        buf = (buf + " " + sent).strip()
        if len(buf.split()) >= 12:
            scenes.append({"narration": buf, "visual_query": topic[:60], "image_prompt": f"{topic[:80]}, scene {len(scenes) + 1}"})
            buf = ""
    if buf:
        if scenes:
            scenes[-1]["narration"] += " " + buf
        else:
            scenes.append({"narration": buf, "visual_query": topic[:60], "image_prompt": topic[:80]})
    if len(scenes) < 2:
        raise ValueError("reply too short to use")
    return {"title": f"{topic[:55].strip().capitalize()} #shorts", "description": f"{topic[:100]} #shorts",
            "visual_style": DEFAULT_LOOK, "scenes": scenes[:7]}


def ask_ollama(prompt, settings):
    """Talk to a free, open-source model running on your own computer (via Ollama)."""
    body = json.dumps({
        "model": settings["ollama_model"],
        "messages": [{"role": "user", "content": prompt}],
        "format": "json",
        "stream": False,
    }).encode()
    req = urllib.request.Request(settings["ollama_url"].rstrip("/") + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            return json.loads(resp.read())["message"]["content"]
    except urllib.error.HTTPError as err:
        if err.code == 404:
            raise PipelineError(f"Ollama doesn't have the model '{settings['ollama_model']}' yet. "
                                f"Open a terminal and run:  ollama pull {settings['ollama_model']}")
        raise PipelineError(f"Ollama returned an error ({err.code}).")
    except OSError:
        raise PipelineError("Couldn't reach Ollama. Is it installed and running? "
                            "Install it from https://ollama.com, then try again.")


def ask_claude(prompt, settings):
    """Optional: use Claude through the paid Anthropic API (needs ANTHROPIC_API_KEY)."""
    try:
        import anthropic
    except ImportError:
        raise PipelineError("The 'anthropic' add-on isn't installed. Run: pip install anthropic")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise PipelineError("Missing ANTHROPIC_API_KEY (only needed for --engine claude).")
    msg = anthropic.Anthropic().messages.create(
        model=CLAUDE_MODEL, max_tokens=1500, messages=[{"role": "user", "content": prompt}])
    return msg.content[0].text


CTA_WORDS = re.compile(r"subscrib|follow|\blike\b|\bbell\b|notif|comment|channel|button|share|click|tap\b|screen|icon|logo", re.I)


def sanitize_scenes(script, topic):
    """Scenes about 'subscribe / bell / comment' make ugly pictures; give them a picture of the topic instead."""
    scenes = script["scenes"]
    if not scenes:
        return script
    base_q = (scenes[0].get("visual_query") or topic)[:60]
    base_p = scenes[0].get("image_prompt") or topic
    for k, sc in enumerate(scenes):
        if CTA_WORDS.search(sc.get("image_prompt", "") + " " + sc.get("visual_query", "")):
            sc["visual_query"] = base_q if k else (topic[:60] or base_q)
            sc["image_prompt"] = f"Wide cinematic establishing shot related to: {base_p}" if k else base_p
    return script


def generate_script(topic, style, engine, settings, progress, seconds=45):
    ask = ask_ollama if engine == "ollama" else ask_claude
    plan = length_plan(seconds)
    base = PROMPT.format(topic=topic, style=f"Style / niche notes: {style}\n" if style else "", **plan)
    prompt, last_reply, last_err = base, "", "no reply"
    for attempt in range(1, 6):  # small models sometimes slip; try up to 5 times
        try:
            last_reply = ask(prompt, settings)
            script = parse_script(last_reply)
            spoken = sum(len(sc["narration"].split()) for sc in script["scenes"])
            if spoken < plan["words"] * 0.65 and attempt < 3:  # small models tend to write too little for long videos
                raise ValueError(f"too short: {spoken} words, need about {plan['words']}")
            return sanitize_scenes(script, topic)
        except (ValueError, KeyError, TypeError, AttributeError) as err:
            last_err = str(err)
            progress(None, f"The model's answer wasn't usable ({err}); trying again ({attempt}/5)...")
            if attempt >= 2:  # shorter, stricter wording works better for small models
                prompt = (base + "\n\nIMPORTANT: your last answer could not be read (" + last_err +
                          "). Reply with the JSON object only, starting with { and ending with }.")
    try:  # last resort: use the text it wrote even though it wasn't in the right format
        return script_from_prose(last_reply, topic)
    except ValueError:
        pass
    raise PipelineError(f"The AI model couldn't produce a usable script ({last_err}). Click Make my video again, "
                        "which usually works. If it keeps happening, try a bigger model (see the README).")


# --------------------------------------------------------------------------- stock footage (Pexels)

def _http_get(url, headers=None, timeout=60):
    h = {"User-Agent": "ShortsMaker/1.0"}
    h.update(headers or {})
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout)


def pexels_search(kind, query, key):
    """kind is 'videos' or 'photos'. Returns a list of results (maybe empty)."""
    base = os.environ.get("PEXELS_API_BASE", "https://api.pexels.com")
    path = "/videos/search" if kind == "videos" else "/v1/search"
    params = {"query": query, "orientation": "portrait", "per_page": 10}
    if kind == "videos":
        params["size"] = "medium"
    try:
        with _http_get(f"{base}{path}?{urllib.parse.urlencode(params)}", {"Authorization": key}, 30) as r:
            return json.loads(r.read()).get(kind, [])
    except urllib.error.HTTPError as err:
        if err.code in (401, 403):
            raise PipelineError("Pexels didn't accept your API key. Check it in Settings "
                                "(get a free one at https://www.pexels.com/api/).")
        return []
    except (OSError, ValueError):
        return []


def pick_video_file(video):
    files = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("link")]
    tall = [f for f in files if (f.get("height") or 0) >= (f.get("width") or 0)]
    pool = tall or files
    good = [f for f in pool if (f.get("height") or 0) >= 1280]
    if good:
        return min(good, key=lambda f: abs((f.get("height") or 0) - 1920))
    return max(pool, key=lambda f: f.get("height") or 0) if pool else None


def download(url, path):
    with _http_get(url, timeout=120) as r, open(path, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)


def find_visual_pexels(queries, used, key, tmp, idx):
    """Return ('video', path) or ('image', path) for the first query that works, else None."""
    for q in queries:
        for v in pexels_search("videos", q, key):
            f = pick_video_file(v)
            if f and ("v", v.get("id")) not in used:
                path = os.path.join(tmp, f"scene{idx}_bg.mp4")
                try:
                    download(f["link"], path)
                except OSError:
                    continue
                used.add(("v", v.get("id")))
                return "video", path
        for p in pexels_search("photos", q, key):
            if ("p", p.get("id")) in used:
                continue
            src = p.get("src", {})
            path = os.path.join(tmp, f"scene{idx}_bg.jpg")
            for url in (src.get("original", "") + "?auto=compress&cs=tinysrgb&fit=crop&w=1620&h=2880",
                        src.get("large2x")):
                if not url or url.startswith("?"):
                    continue
                try:
                    download(url, path)
                    used.add(("p", p.get("id")))
                    return "image", path
                except OSError:
                    continue
    return None


def pixabay_search(kind, query, key):
    """kind is 'photos' (vertical photos) or 'videos'. Returns a list of hits (maybe empty)."""
    base = os.environ.get("PIXABAY_API_BASE", "https://pixabay.com")
    path = "/api/videos/" if kind == "videos" else "/api/"
    params = {"key": key, "q": query[:100], "per_page": 10, "safesearch": "true"}
    if kind == "photos":
        params.update({"orientation": "vertical", "image_type": "photo", "min_height": 1200, "order": "popular"})
    try:
        with _http_get(f"{base}{path}?{urllib.parse.urlencode(params)}", timeout=30) as r:
            return json.loads(r.read()).get("hits", [])
    except urllib.error.HTTPError as err:
        if err.code in (400, 401, 403):
            raise PipelineError("Pixabay didn't accept your API key. Check it in Settings "
                                "(your key is shown at https://pixabay.com/api/docs/ when you are logged in).")
        return []
    except (OSError, ValueError):
        return []


def _pixabay_clip(hit, need):
    """Pick the best size of one Pixabay video: sharp (about 1080p) but not huge. Returns (url, w, h) or None."""
    sizes = hit.get("videos", {})
    for name in ("large", "medium", "small"):
        v = sizes.get(name) or {}
        if v.get("url") and (v.get("height") or 1080) >= 720:
            return v["url"], v.get("width") or 0, v.get("height") or 0
    v = sizes.get("medium") or sizes.get("small") or sizes.get("large") or {}
    return (v["url"], v.get("width") or 0, v.get("height") or 0) if v.get("url") else None


def find_visual_pixabay(queries, used, key, tmp, idx, need=0):
    """Return ('video', path) or ('image', path) from Pixabay, else None. Moving footage looks far better than
    still photos, so videos come first (long enough clips and vertical ones are preferred); then sharp vertical photos."""
    for q in queries:
        hits = [h for h in pixabay_search("videos", q, key) if ("pxb-v", h.get("id")) not in used]

        def score(h):
            clip = _pixabay_clip(h, need)
            if not clip:
                return 99
            tall = clip[2] >= clip[1] and clip[1] > 0
            long_enough = (h.get("duration") or 0) >= need
            return (0 if long_enough else 2) + (0 if tall else 1)
        for hit in sorted(hits, key=score):  # sorted() is stable, so search relevance still breaks ties
            clip = _pixabay_clip(hit, need)
            if not clip:
                continue
            path = os.path.join(tmp, f"scene{idx}_bg.mp4")
            try:
                download(clip[0], path)
            except OSError:
                continue
            used.add(("pxb-v", hit.get("id")))
            return "video", path
    for q in queries:
        for hit in pixabay_search("photos", q, key):
            if ("pxb-p", hit.get("id")) in used:
                continue
            path = os.path.join(tmp, f"scene{idx}_bg.jpg")
            for url in (hit.get("largeImageURL"), hit.get("webformatURL")):
                if not url:
                    continue
                try:
                    download(url, path)
                    used.add(("pxb-p", hit.get("id")))
                    return "image", path
                except OSError:
                    continue
    return None


def find_visual(queries, used, settings, tmp, idx, need=0):
    """Look for a picture or clip with whichever stock source has a key. Pexels first, then Pixabay."""
    if settings.get("pexels_key"):
        found = find_visual_pexels(queries, used, settings["pexels_key"], tmp, idx)
        if found:
            return found
    if settings.get("pixabay_key"):
        return find_visual_pixabay(queries, used, settings["pixabay_key"], tmp, idx, need)
    return None


# --------------------------------------------------------------------------- drawing

@functools.lru_cache(maxsize=None)
def load_font(size):
    candidates = [
        "C:/Windows/Fonts/ariblk.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def make_gradient(path, size, top, bottom):
    w, h = size
    mask = Image.linear_gradient("L").resize((w, h))
    Image.composite(Image.new("RGB", (w, h), bottom), Image.new("RGB", (w, h), top), mask).save(path, quality=92)


def prepare_photo(src, dst, size=(1620, 2880)):
    """Crop a photo to 9:16 and size it so slow zooming still looks sharp."""
    img = Image.open(src).convert("RGB")
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1), Image.LANCZOS)
    left, top = (img.width - tw) // 2, (img.height - th) // 2
    img.crop((left, top, left + tw, top + th)).save(dst, quality=92)


def make_shade(path):
    """A soft dark layer so white text stays readable on any footage."""
    img = Image.new("RGBA", (WIDTH, HEIGHT))
    d = ImageDraw.Draw(img)
    center = CAPTION_Y + CAPTION_H / 2
    for y in range(HEIGHT):
        alpha = 25 + max(0, 1 - y / 450) * 90 + max(0, 1 - abs(y - center) / 520) * 110
        d.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, int(min(alpha, 200))))
    img.save(path)


def clean_word(w):
    return w.strip("\"'“”‘’").rstrip(".,;:").upper()


def render_caption(chunk, active, path):
    """Draw one caption (a few words) with the word being spoken highlighted."""
    words = [clean_word(w) for w in chunk]
    max_w = WIDTH - 140
    size = 52
    while True:
        font = load_font(size)
        space = font.getlength(" ")
        widths = [font.getlength(w) for w in words]
        lines, cur, cur_w = [], [], 0
        for i, w in enumerate(widths):
            if cur and cur_w + space + w > max_w:
                lines.append(cur)
                cur, cur_w = [i], w
            else:
                cur_w += w if not cur else space + w
                cur.append(i)
        lines.append(cur)
        if (max(widths) <= max_w and len(lines) <= 3) or size <= 34:
            break
        size -= 8

    img = Image.new("RGBA", (WIDTH, CAPTION_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    line_h = int(size * 1.28)
    y = (CAPTION_H - line_h * len(lines)) // 2
    for line in lines:
        total = sum(widths[i] for i in line) + space * (len(line) - 1)
        x = (WIDTH - total) / 2
        for i in line:
            d.text((x, y), words[i], font=font, fill=HIGHLIGHT if i == active else (255, 255, 255),
                   stroke_width=max(4, size // 11), stroke_fill=(0, 0, 0))
            x += widths[i] + space
        y += line_h
    img.save(path)


# --------------------------------------------------------------------------- subscribe prompt

SUBSCRIBE_CENTER_Y = 470   # near the top, clear of the captions and of YouTube's buttons
SUBSCRIBE_START, SUBSCRIBE_CLICK, SUBSCRIBE_END = 0.30, 1.70, 3.10


def _fit_font(text, max_w, start):
    size = start
    while size > 30:
        font = load_font(size)
        if font.getlength(text) <= max_w:
            return font
        size -= 4
    return load_font(30)


def _outlined(draw, shape_fn, fill, outline=7, color=(0, 0, 0)):
    """Draw a shape with a thick black outline (the sticker look)."""
    for dx in range(-outline, outline + 1, 3):
        for dy in range(-outline, outline + 1, 3):
            if dx * dx + dy * dy <= outline * outline:
                shape_fn(dx, dy, color)
    shape_fn(0, 0, fill)


def _star(draw, cx, cy, r, fill):
    pts = [(cx, cy - r), (cx + r * 0.28, cy - r * 0.28), (cx + r, cy), (cx + r * 0.28, cy + r * 0.28),
           (cx, cy + r), (cx - r * 0.28, cy + r * 0.28), (cx - r, cy), (cx - r * 0.28, cy - r * 0.28)]
    draw.polygon(pts, fill=fill)


def make_subscribe_cards(path_before, path_after, kind="subscribe"):
    """Two loud, bold pictures for the opening: a big red SUBSCRIBE button with a mouse arrow, then the
    pressed SUBSCRIBED button with a ringing bell and sparkles."""
    W, H = WIDTH, 460
    bx0, by0, bx1, by1 = 110, 120, 970, 310
    bell_c = (885, (by0 + by1) // 2)
    yellow = (255, 214, 10)
    follow = kind == "follow"
    base_color = (254, 44, 85, 255) if follow else (238, 20, 20, 255)
    shine_color = (255, 112, 140, 255) if follow else (255, 84, 84, 255)
    for path, done in ((path_before, False), (path_after, True)):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # shadow, white sticker border, then the button itself
        d.rounded_rectangle((bx0 + 4, by0 + 22, bx1 + 4, by1 + 22), radius=95, fill=(0, 0, 0, 130))
        d.rounded_rectangle((bx0 - 12, by0 - 12, bx1 + 12, by1 + 12), radius=105, fill=(255, 255, 255, 255))
        d.rounded_rectangle((bx0, by0, bx1, by1), radius=95, fill=(58, 58, 62, 255) if done else base_color)
        if not done:  # shiny top half
            d.rounded_rectangle((bx0 + 14, by0 + 10, bx1 - 14, (by0 + by1) // 2 - 4), radius=70, fill=shine_color)
        label = ("FOLLOWING" if done else "FOLLOW") if follow else ("SUBSCRIBED" if done else "SUBSCRIBE")
        tx0 = 265 if done else 150
        font = _fit_font(label, 500 if done else 600, 104)
        d.text((tx0, (by0 + by1) // 2 + 4), label, font=font, fill=(255, 255, 255), anchor="lm",
               stroke_width=9, stroke_fill=(0, 0, 0))
        if done:  # green tick in a circle on the left
            cx, cy = 190, (by0 + by1) // 2
            d.ellipse((cx - 44, cy - 44, cx + 44, cy + 44), fill=(52, 199, 89), outline=(255, 255, 255), width=6)
            d.line([(cx - 22, cy + 2), (cx - 6, cy + 20), (cx + 24, cy - 18)], fill=(255, 255, 255), width=11, joint="curve")
        # the bell, yellow with a black outline
        bx, by = bell_c

        def bell(dx, dy, color, bx=bx, by=by):
            d.pieslice((bx - 44 + dx, by - 58 + dy, bx + 44 + dx, by + 30 + dy), 180, 360, fill=color)
            d.polygon([(bx - 44 + dx, by - 14 + dy), (bx + 44 + dx, by - 14 + dy), (bx + 62 + dx, by + 36 + dy),
                       (bx - 62 + dx, by + 36 + dy)], fill=color)
            d.ellipse((bx - 15 + dx, by + 34 + dy, bx + 15 + dx, by + 62 + dy), fill=color)
            d.ellipse((bx - 8 + dx, by - 72 + dy, bx + 8 + dx, by - 56 + dy), fill=color)

        def heart(dx, dy, color, bx=bx, by=by):
            cx, cy = bx + dx, by + dy
            d.ellipse((cx - 56, cy - 48, cx, cy + 8), fill=color)
            d.ellipse((cx, cy - 48, cx + 56, cy + 8), fill=color)
            d.polygon([(cx - 54, cy - 8), (cx + 54, cy - 8), (cx, cy + 56)], fill=color)
        _outlined(d, heart if follow else bell, yellow, outline=6)
        if done:  # ring marks and sparkles
            for box, a0, a1 in (((bx - 90, by - 90, bx + 90, by + 70), 200, 245), ((bx - 90, by - 90, bx + 90, by + 70), 295, 340)):
                d.arc(box, a0, a1, fill=yellow, width=9)
            for (sx, sy, sr, col) in ((90, 70, 30, yellow), (1000, 90, 38, (255, 255, 255)), (60, 380, 26, (255, 255, 255)),
                                      (1010, 360, 32, yellow), (560, 60, 22, yellow), (330, 400, 24, yellow)):
                _star(d, sx, sy, sr, col)
        # the mouse arrow
        mx, my = (920, 300) if not done else (914, 294)

        def arrow(dx, dy, color):
            pts = [(0, 0), (0, 60), (16, 46), (28, 74), (42, 68), (30, 41), (50, 41)]
            d.polygon([(mx + dx + p[0] * 1.6, my + dy + p[1] * 1.6) for p in pts], fill=color)
        _outlined(d, arrow, (255, 255, 255), outline=6)
        if done:  # click burst around the arrow tip
            for ang_dx, ang_dy in ((-34, -8), (-24, -30), (4, -38)):
                d.line([(mx + ang_dx, my + ang_dy), (mx + ang_dx * 1.8, my + ang_dy * 1.8)], fill=yellow, width=8)
        img.save(path)


def make_subscribe_sounds(path, duration, timings=((SUBSCRIBE_START, SUBSCRIBE_CLICK, SUBSCRIBE_END),)):
    """A short pop, click and 'ding' like a video editor would add, saved as a wav file."""
    import math
    import random
    import struct
    import wave
    rate = 44100
    n = int(rate * max(duration, max(t[2] for t in timings) + 0.5))
    buf = [0.0] * n
    rnd = random.Random(7)

    def add(t0, length, fn):
        i0 = int(t0 * rate)
        for i in range(int(length * rate)):
            if i0 + i < n:
                buf[i0 + i] += fn(i / rate)

    for t_start, t_click, t_end in timings:
        add(t_start, 0.14, lambda t: 0.5 * math.sin(2 * math.pi * (350 + 3500 * t) * t) * math.exp(-t * 14))  # pop
        add(t_click, 0.07, lambda t: 0.5 * (rnd.random() * 2 - 1) * math.exp(-t * 70)
            + 0.4 * math.sin(2 * math.pi * 160 * t) * math.exp(-t * 40))  # click
        add(t_click + 0.06, 0.8, lambda t: 0.3 * (math.sin(2 * math.pi * 1318.5 * t) + 0.6 * math.sin(2 * math.pi * 1975.5 * t))
            * math.exp(-t * 6))  # ding
        add(t_end - 0.25, 0.25, lambda t: 0.25 * (rnd.random() * 2 - 1) * (t / 0.25) * math.exp(-((t - 0.25) * 6) ** 2 if t > 0.25 else 0))  # whoosh
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 30000)) for v in buf))


# --------------------------------------------------------------------------- voice + timing

async def synth(text, voice, path):
    import edge_tts
    try:
        comm = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    except TypeError:  # older versions of the library
        comm = edge_tts.Communicate(text, voice)
    marks = []
    with open(path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                marks.append(chunk["offset"] / 1e7)
    return marks


def make_voice(text, voice, path, fake=False):
    """Returns (word start times if known else [])."""
    if fake:  # testing only: a beep as long as the sentence would take to say
        secs = max(1.5, len(text.split()) * 0.35)
        run_ffmpeg([FFMPEG, "-y", "-f", "lavfi", "-i", f"sine=frequency=330:duration={secs:.2f}",
                    "-q:a", "6", path], "test audio")
        return []
    try:
        return asyncio.run(synth(text, voice, path))
    except ImportError:
        raise PipelineError("The voice add-on isn't installed. Run: pip install -r requirements.txt")
    except Exception as err:
        raise PipelineError("Couldn't create the voiceover. The free voices need an internet connection "
                            f"(they come from Microsoft's online service). Details: {err}")


def audio_seconds(path):
    r = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True, errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", r.stderr)
    if not m:
        raise PipelineError("Couldn't read the length of the voiceover.")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def word_windows(words, marks, total):
    """(start, end) seconds for each word. Uses exact timing when available, else estimates."""
    if marks and len(marks) == len(words):
        starts = list(marks)
    else:
        lead = 0.05
        weights = [len(re.sub(r"\W", "", w)) + 2 + (4 if re.search(r"[.!?]$", w) else 2 if re.search(r"[,;:]$", w) else 0)
                   for w in words]
        speech = max(total - 0.25 - lead, 0.5)
        starts, t = [], lead
        for w in weights:
            starts.append(t)
            t += speech * w / sum(weights)
    return list(zip(starts, starts[1:] + [total]))


def chunk_words(words, per=3):
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        if len(cur) >= per or re.search(r"[.!?]$", w):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


# --------------------------------------------------------------------------- video building

def run_ffmpeg(cmd, what):
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        raise PipelineError(f"A video step failed ({what}):\n{r.stderr[-1200:]}")


GRADE = "eq=contrast=1.08:saturation=1.18:brightness=0.01,unsharp=5:5:0.6:5:5:0.0"  # a little punch and crispness


def camera_move(idx, frames):
    """Zoom/pan settings for a still picture. Each scene gets a different move so it feels alive."""
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    t = f"on/{frames}"  # goes from 0 to 1 over the scene
    zoom_in, zoom_out, held = "min(1+0.0007*on,1.2)", "max(1.2-0.0007*on,1)", "1.15"
    moves = [
        (zoom_in, cx, cy),                                   # slow push in
        (zoom_out, cx, cy),                                  # slow pull out
        (held, f"(iw-iw/zoom)*{t}", cy),                     # pan right
        (held, f"(iw-iw/zoom)*(1-{t})", cy),                 # pan left
        (zoom_in, cx, "(ih-ih/zoom)*0.25"),                  # push in toward the upper part
        (held, cx, f"(ih-ih/zoom)*(1-{t})"),                 # tilt up
    ]
    return moves[idx % len(moves)]


def build_scene(idx, kind, bg_path, audio_path, shade_png, caps, duration, out_path, subscribe=None):
    """caps: list of (png_path, start, end). subscribe: optional dict {"badges": [{cards, start, click, end}], "sfx": wav}.
    Builds one finished scene clip."""
    inputs = (["-stream_loop", "-1"] if kind == "video" else []) + ["-i", bg_path, "-i", shade_png]
    for png, _, _ in caps:
        inputs += ["-i", png]
    inputs += ["-i", audio_path]
    audio_idx = 2 + len(caps)
    if subscribe:
        for bd in subscribe["badges"]:
            inputs += ["-loop", "1", "-t", f"{duration:.3f}", "-i", bd["cards"][0],
                       "-loop", "1", "-t", f"{duration:.3f}", "-i", bd["cards"][1]]
        inputs += ["-i", subscribe["sfx"]]

    if kind == "video":
        chain = (f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                 f"crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS},{GRADE}[bg]")
    else:  # a still picture: slow camera move
        frames = int(duration * FPS) + 2
        z, x, y = camera_move(idx, frames)
        chain = (f"[0:v]zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},setsar=1,{GRADE}[bg]")
    chain += ";[bg][1:v]overlay=0:0:format=auto[v0]"
    for i, (_, a, b) in enumerate(caps):
        chain += (f";[v{i}][{2 + i}:v]overlay=x=0:y={CAPTION_Y}:format=auto:"
                  f"enable='between(t,{a:.3f},{b:.3f})'[v{i + 1}]")

    last = f"v{len(caps)}"
    audio_chain = f"[{audio_idx}:a]apad[aout]"
    if subscribe:
        size = lambda e: f"w='max(2,trunc(iw*({e})/2)*2)':h='max(2,trunc(ih*({e})/2)*2)':eval=frame"
        place = f"x='(W-w)/2':y='{SUBSCRIBE_CENTER_Y}-h/2':format=auto"
        nb, k = len(subscribe["badges"]), audio_idx + 1
        for n, bd in enumerate(subscribe["badges"]):
            start, click, end = bd["times"]
            if start > duration - 0.9:   # the scene is too short for this one
                k += 2
                continue
            end = min(end, max(duration - 0.1, click + 0.4))
            click = min(click, end - 0.4)
            pa, pb = k, k + 1
            k += 2
            p_in = f"clip((t-{start:.3f})/0.35,0,1)"
            pop = f"(1+2.70158*pow({p_in}-1,3)+1.70158*pow({p_in}-1,2))"  # grows in with a bounce
            punch = f"(1+0.20*sin(PI*clip((t-{click:.3f})/0.30,0,1)))"      # a quick punch when it is clicked
            leave = f"(1-pow(clip((t-{end - 0.25:.3f})/0.25,0,1),2))"          # shrinks away
            chain += (f";[{pa}:v]format=rgba,scale={size(pop)}[sa{n}]"
                      f";[{pb}:v]format=rgba,scale={size(punch + '*' + leave)}[sb{n}]"
                      f";[{last}][sa{n}]overlay={place}:enable='between(t,{start:.3f},{click:.3f})'[vs{n}a]"
                      f";[vs{n}a][sb{n}]overlay={place}:enable='between(t,{click:.3f},{end - 0.01:.3f})'[vs{n}b]")
            last = f"vs{n}b"
        sfx = k
        audio_chain = f"[{audio_idx}:a]apad[a0];[a0][{sfx}:a]amix=inputs=2:duration=first:dropout_transition=0,volume=1.7[aout]"
    chain += ";" + audio_chain
    run_ffmpeg([FFMPEG, "-y", *inputs, "-filter_complex", chain,
                "-map", f"[{last}]", "-map", "[aout]",
                "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-ar", "44100", "-ac", "2",
                "-b:a", "160k", out_path], f"scene {idx + 1}")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50] or "video"


def ai_visual(i, n, scene, look, quality, tmp, say, pct, warnings, can_fall_back):
    """Paint an AI picture for one scene on this computer. Returns ('image', path) or None."""
    subject = scene.get("image_prompt") or scene.get("visual_query") or scene["narration"]
    prompt = (f"{subject}. {look}. Vertical composition. "
              "No text, no letters, no words, no logos, no interface elements.")
    path = os.path.join(tmp, f"s{i}_ai.png")
    label = f"Scene {i + 1} of {n}: painting the AI picture"

    def tick(seconds):
        say(pct, f"{label}... {seconds // 60}m {seconds % 60:02d}s so far{ai_images.mode_note()}. "
                 "This is slow on a laptop, so please keep waiting.")

    say(pct, label + "...")
    try:
        reused = ai_images.generate_image(prompt, path, quality, progress=tick, use_cache=not scene.get("fresh"))
        if reused:
            say(pct, f"Scene {i + 1} of {n}: reusing the picture painted earlier.")
    except ai_images.AIError as err:
        if not can_fall_back:  # nothing else to use, so say what went wrong instead of making colored screens
            raise PipelineError(f"The AI picture for scene {i + 1} didn't work. {err}")
        warnings.append(f"Scene {i + 1}: the AI picture didn't work, so stock footage was used. {err}")
        say(pct, f"Scene {i + 1}: the AI picture didn't work. Using other footage for this scene.")
        return None
    return "image", path


def draft_script(idea, style="", engine="ollama", progress=None, seconds=None):
    """Write just the script (no video), so it can be edited on the page first."""
    settings = load_settings()
    seconds = clamp_seconds(seconds if seconds is not None else settings["video_seconds"])
    say = progress or (lambda p, m: None)
    say(5, "Writing the script...")
    return generate_script(idea, style, engine, settings, say, seconds)


def make_video(idea, style="", engine="ollama", progress=None, demo=False, fake_audio=False,
               visual_mode=None, steps=None, seconds=None, script=None, image_style=None):
    """The whole pipeline. Returns a dict with the video path, title, description and script.
    steps(list) is called with a checklist like [{"label": ..., "state": "pending|active|done"}]."""
    plan = [{"label": "Write the script", "state": "active"}]

    def mark(index, state):
        plan[index]["state"] = state
        if steps:
            steps([dict(p) for p in plan])

    mark(0, "active")

    def say(pct, msg):
        (progress or (lambda p, m: print(f"[{'..' if p is None else p:>3}] {m}")))(pct, msg)

    settings = load_settings()
    mode = visual_mode or settings["visual_mode"]
    if mode == "ai_images" and not ai_images.ai_ready():
        raise PipelineError("AI images aren't set up yet. Click \"Set up AI images\" on the page "
                            "(a one-time download), or switch Visuals to Stock footage.")

    if script is None:
        say(2, "Writing the script..." if not demo else "Using the built-in sample script...")
    seconds = clamp_seconds(seconds if seconds is not None else settings["video_seconds"])
    if script is not None:  # a project the person edited on the page
        try:
            script = clean_script(script)
        except ValueError as err:
            raise PipelineError(f"That project can't be used ({err}).")
    else:
        script = DEMO_SCRIPT if demo else generate_script(idea, style, engine, settings, say, seconds)
    scenes = script["scenes"]
    chosen = image_style or settings["image_style"]
    look = IMAGE_STYLES[chosen][1] if chosen in IMAGE_STYLES else (script.get("visual_style") or DEFAULT_LOOK)
    has_stock = bool(settings["pexels_key"] or settings["pixabay_key"])
    if mode == "stock" and not has_stock and ai_images.ai_ready():
        mode = "ai_images"  # no stock key, but AI images are installed: use them instead of plain colors
        say(8, "No stock footage key is set, so this video will use AI images instead.")
    if mode == "stock" and not has_stock:
        say(8, "No stock footage key is set, so this video will use colored backgrounds. "
               "Add a free Pixabay key in Settings for real footage.")

    plan[0]["state"] = "done"
    for n, sc in enumerate(scenes, 1):
        words = sc["narration"].split()
        plan.append({"label": f"Scene {n}: " + " ".join(words[:6]) + ("..." if len(words) > 6 else ""),
                     "state": "pending"})
    plan.append({"label": "Put the video together", "state": "pending"})
    mark(0, "done")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        shade = os.path.join(tmp, "shade.png")
        make_shade(shade)
        used, clips, warnings = set(), [], []
        which = settings.get("intro_button") if settings.get("intro_button") in ("subscribe", "follow", "both") else "subscribe"
        kinds = ["subscribe", "follow"] if which == "both" else [which]
        gap, length, click_at = (2.2, 2.2, 1.1) if len(kinds) > 1 else (0, 2.8, 1.4)
        badges = []
        for n, kd in enumerate(kinds):
            cards = (os.path.join(tmp, f"{kd}1.png"), os.path.join(tmp, f"{kd}2.png"))
            make_subscribe_cards(cards[0], cards[1], kd)
            start = SUBSCRIBE_START + n * length
            badges.append({"cards": cards, "times": (start, start + click_at, start + length)})
        sfx_path = os.path.join(tmp, "sub.wav")
        make_subscribe_sounds(sfx_path, 6.0, [b["times"] for b in badges])
        subscribe_cards = {"badges": badges, "sfx": sfx_path}
        short_idea = " ".join((idea or script["title"]).replace("#shorts", "").split()[:4])

        for i, scene in enumerate(scenes):
            base = 10 + int(80 * i / len(scenes))
            step = 80 // len(scenes)
            mark(i + 1, "active")
            say(base, f"Scene {i + 1} of {len(scenes)}: recording the voice...")
            audio = os.path.join(tmp, f"s{i}.mp3")
            marks = make_voice(scene["narration"], settings["voice"], audio, fake=fake_audio)
            duration = audio_seconds(audio) + 0.25

            visual = None
            if mode == "ai_images":
                scene_look = IMAGE_STYLES[scene["style"]][1] if scene.get("style") in IMAGE_STYLES else look
                visual = ai_visual(i, len(scenes), scene, scene_look, settings["ai_image_quality"],
                                   tmp, say, base + step // 3, warnings, has_stock)
            if not visual and has_stock:
                say(base + step // 3, f"Scene {i + 1} of {len(scenes)}: finding footage...")
                q = scene["visual_query"]
                keywords = sorted({w.strip(".,!?\"'").lower() for w in scene["narration"].split()
                                   if len(w.strip(".,!?\"'")) > 5}, key=len, reverse=True)[:2]
                queries = [x for x in dict.fromkeys([q, " ".join(q.split()[:2]), " ".join(keywords), short_idea]) if x.strip()]
                visual = find_visual(queries, used, settings, tmp, i, need=duration)
            if visual and visual[0] == "image":
                prepared = os.path.join(tmp, f"s{i}_photo.jpg")
                prepare_photo(visual[1], prepared)
                visual = ("image", prepared)
            if not visual:
                grad = os.path.join(tmp, f"s{i}_grad.jpg")
                make_gradient(grad, (1620, 2880), *GRADIENTS[i % len(GRADIENTS)])
                visual = ("image", grad)

            say(base + 2 * step // 3, f"Scene {i + 1} of {len(scenes)}: adding captions and assembling...")
            words = [w for w in scene["narration"].split() if re.search(r"\w", w)]
            windows = word_windows(words, marks, duration)
            caps = []
            for chunk in chunk_words(words):
                for wi in chunk:
                    png = os.path.join(tmp, f"c{i}_{wi}.png")
                    render_caption([words[j] for j in chunk], chunk.index(wi), png)
                    caps.append((png, *windows[wi]))
            clip = os.path.join(tmp, f"scene{i}.mp4")
            scene_len = duration
            if i == 0:  # a short opening line is stretched a little so every intro button gets its full moment
                scene_len = max(duration, max(b["times"][2] for b in badges) + 0.2)
            build_scene(i, visual[0], visual[1], audio, shade, caps, scene_len, clip,
                        subscribe=subscribe_cards if i == 0 else None)
            clips.append(clip)
            mark(i + 1, "done")

        mark(len(plan) - 1, "active")
        say(92, "Putting the scenes together...")
        stamp = time.strftime("%Y%m%d-%H%M%S")
        name = f"{stamp}-{slugify(script['title'])}"
        out_path = os.path.join(OUTPUT_DIR, name + ".mp4")
        listfile = os.path.join(tmp, "list.txt")
        with open(listfile, "w", encoding="utf-8") as f:
            for c in clips:
                f.write("file '" + c.replace("\\", "/").replace("'", "'\\''") + "'\n")
        run_ffmpeg([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy",
                    "-movflags", "+faststart", out_path], "joining scenes")

    mark(len(plan) - 1, "done")
    with open(os.path.join(OUTPUT_DIR, name + ".txt"), "w", encoding="utf-8") as f:
        f.write(script["title"] + "\n\n" + script["description"] + "\n\n--- script (check the facts!) ---\n")
        for s in scenes:
            f.write(f"- {s['narration']}\n")
    say(100, "Done!")
    return {"video": out_path, "name": name + ".mp4", "title": script["title"],
            "description": script["description"], "script": scenes, "warnings": warnings}


def main():
    parser = argparse.ArgumentParser(description="Turn an idea into a YouTube Short.")
    parser.add_argument("idea", nargs="?", help="What the video is about")
    parser.add_argument("--style", default="", help="Optional style/niche notes, e.g. 'calm, motivational'")
    parser.add_argument("--demo", action="store_true", help="Use a built-in sample script")
    parser.add_argument("--engine", choices=["ollama", "claude"], default="ollama",
                        help="Who writes the script (default: free open-source model via Ollama)")
    parser.add_argument("--visuals", choices=["stock", "ai_images"],
                        help="stock = Pexels footage (default); ai_images = painted on your computer")
    parser.add_argument("--seconds", type=int, help="Video length in seconds (30 to 90)")
    parser.add_argument("--fake-audio", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    idea = args.idea or ("" if args.demo else input("What should the video be about? ").strip())
    try:
        result = make_video(idea, args.style, args.engine, demo=args.demo, fake_audio=args.fake_audio,
                            visual_mode=args.visuals, seconds=args.seconds)
    except PipelineError as err:
        sys.exit(f"\n{err}")
    print(f"\nDone! Your video: {result['video']}")


if __name__ == "__main__":
    main()
