"""
Shorts Maker - the web page and the little server behind it.

Run this file (or double-click "Start Shorts Maker.bat"). Your browser opens a page
where you type an idea and get a finished short vertical video.
Everything runs on your own computer; nothing here is reachable from the internet.

The page itself (HTML, CSS, JavaScript) lives in ui.py. The story tools live in story.py.

License: MIT (see LICENSE)
"""

import json
import os
import subprocess
import sys
import threading
import time
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

import ai_images as ai
import shorts_maker as sm
import story as storylib
from ui import PAGE

PORT = int(os.environ.get("SHORTS_PORT", "8765"))
FAKE_AUDIO = bool(os.environ.get("SHORTS_FAKE_AUDIO"))  # for testing only
JOBS = {}
LOCK = threading.Lock()

VOICES = [
    ("en-US-GuyNeural", "Guy (US, male)"),
    ("en-US-AndrewNeural", "Andrew (US, male)"),
    ("en-US-DavisNeural", "Davis (US, male, deep)"),
    ("en-US-JennyNeural", "Jenny (US, female)"),
    ("en-US-AriaNeural", "Aria (US, female)"),
    ("en-US-EmmaNeural", "Emma (US, female)"),
    ("en-GB-RyanNeural", "Ryan (UK, male)"),
    ("en-GB-SoniaNeural", "Sonia (UK, female)"),
]

BUSY = "Something is already running. Please wait for it to finish."


# --------------------------------------------------------------------------- background jobs

class Busy(Exception):
    pass


def start_job(kind, target, *args, message="Starting...", pct=1):
    """Run one job at a time in a background thread. Returns the job id (the page polls /api/status)."""
    with LOCK:
        if any(j["state"] == "running" for j in JOBS.values()):
            raise Busy()
        job_id = uuid.uuid4().hex[:8]
        JOBS[job_id] = {"state": "running", "kind": kind, "pct": pct, "message": message}
    threading.Thread(target=target, args=(job_id,) + args, daemon=True).start()
    return job_id


def guarded(job, work):
    """Run work(); turn problems into a message the page can show."""
    try:
        work()
    except (sm.PipelineError, ai.AIError) as err:
        job.update(state="error", message=str(err) + (saved_note() if job.get("kind") == "video" else ""))
    except Exception as err:  # something unexpected: show it, and print details in the console
        traceback.print_exc()
        job.update(state="error", message=f"Something unexpected went wrong: {err}"
                   + (saved_note() if job.get("kind") == "video" else ""))


def saved_note():
    """After a failed video: tell the person their finished scenes are kept."""
    return ("\n\nYour progress is saved. Click Continue under the button (or Make my video again with the same "
            "settings) and it picks up where it stopped.") if sm.list_unfinished() else ""


def run_setup(job_id):
    job = JOBS[job_id]

    def progress(pct, msg):
        job["pct"] = pct
        job["message"] = msg

    def work():
        ai.setup_ai(progress)
        job.update(state="done", pct=100, message="AI images are ready!")
    guarded(job, work)


def run_job(job_id, idea, style, mode, seconds=None, script=None, image_style=None, story=None):
    job = JOBS[job_id]

    def progress(pct, msg):
        if pct is not None:
            job["pct"] = pct
        job["message"] = msg

    def work():
        result = sm.make_video(idea, style, "ollama", progress, fake_audio=FAKE_AUDIO, visual_mode=mode,
                               steps=lambda items: job.update(steps=items), seconds=seconds, script=script,
                               image_style=image_style, story=story)
        if story and story.get("series_id") and story.get("part"):  # remember which part of the series this is
            storylib.mark_part_done(sm.SETTINGS_DIR, story["series_id"], story["part"] - 1, result["name"])
        job.update(state="done", pct=100, message="Done!", result={
            "name": result["name"], "title": result["title"],
            "description": result["description"], "script": result["script"],
            "warnings": result.get("warnings", [])})
    guarded(job, work)


def run_draft(job_id, idea, style, seconds, story):
    job = JOBS[job_id]

    def work():
        script = sm.draft_script(idea, style, "ollama", lambda pct, msg: job.update(message=msg), seconds, story)
        job.update(state="done", pct=100, message="Script ready.", result={"script": script})
    guarded(job, work)


def run_hooks(job_id, idea, script):
    job = JOBS[job_id]

    def work():
        job["message"] = "Thinking up new hooks..."
        try:
            clean = sm.clean_script(script) if script else None
        except ValueError:
            clean = None
        hooks = sm.suggest_hooks(idea, clean, sm.load_settings())
        job.update(state="done", pct=100, message="Here are some hooks.", result={"hooks": hooks})
    guarded(job, work)


def run_rewrite(job_id, script, index, instruction, story):
    job = JOBS[job_id]

    def work():
        job["message"] = "Rewriting the scene..."
        scene = sm.rewrite_scene(script, index, instruction, sm.load_settings(), story)
        job.update(state="done", pct=100, message="Scene rewritten.", result={"index": index, "scene": scene})
    guarded(job, work)


def run_series_plan(job_id, topic, parts, fmt, tone, bible):
    job = JOBS[job_id]

    def work():
        job["message"] = "Planning the series..."
        series = sm.plan_series(topic, parts, fmt, tone, sm.load_settings(), bible)
        note = series.pop("note", "")
        items = storylib.load_series(sm.SETTINGS_DIR)
        items.insert(0, series)
        storylib.save_series(sm.SETTINGS_DIR, items[:30])
        job.update(state="done", pct=100, message="Series planned.", result={"series": series, "note": note})
    guarded(job, work)


# --------------------------------------------------------------------------- helpers

def list_videos():
    items = []
    if os.path.isdir(sm.OUTPUT_DIR):
        for f in sorted(os.listdir(sm.OUTPUT_DIR), reverse=True):
            if f.endswith(".mp4"):
                title, desc = f[:-4], ""
                try:
                    with open(os.path.join(sm.OUTPUT_DIR, f[:-4] + ".txt"), encoding="utf-8") as t:
                        parts = t.read().split("\n\n")
                    title = parts[0].strip() or title
                    desc = parts[1].strip() if len(parts) > 1 and not parts[1].startswith("---") else ""
                except OSError:
                    pass
                when = ""
                try:
                    when = time.strftime("%b %d, %I:%M %p", time.strptime(f[:15], "%Y%m%d-%H%M%S"))
                except ValueError:
                    pass
                items.append({"name": f, "title": title, "when": when, "desc": desc})
    return items[:60]


def story_options():
    return {
        "formats": [{"key": k, "name": v["name"], "tagline": v["tagline"], "beats": v["beats"]}
                    for k, v in storylib.STORY_FORMATS.items()],
        "tones": [{"key": k, "name": v[0]} for k, v in storylib.TONES.items()],
        "endings": [{"key": k, "name": v[0]} for k, v in storylib.ENDINGS.items()],
    }


def story_from_body(body):
    """Build the story settings for a request. A series part takes its story from the series."""
    series_id, index = body.get("series_id"), body.get("part_index")
    if storylib.slug_ok(series_id) and isinstance(index, int):
        series = next((s for s in storylib.load_series(sm.SETTINGS_DIR) if s["id"] == series_id), None)
        if series and 0 <= index < len(series["parts"]):
            return storylib.story_for_part(series, index)
    return storylib.normalize({"format": body.get("story_format"), "tone": body.get("tone"),
                               "ending": body.get("ending"), "bible": body.get("bible")})


# --------------------------------------------------------------------------- the web server

class Handler(BaseHTTPRequestHandler):
    server_version = "ShortsMaker"

    def log_message(self, *args):
        pass

    # ---- helpers
    def send_json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            return body if isinstance(body, dict) else {}
        except ValueError:
            return {}

    def start(self, kind, target, *args, message="Starting...", pct=1):
        try:
            self.send_json({"id": start_job(kind, target, *args, message=message, pct=pct)})
        except Busy:
            self.send_json({"error": BUSY}, 409)

    def send_file(self, path, ctype, download_name=None):
        size = os.path.getsize(path)
        start, end, code = 0, size - 1, 200
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            try:
                if a == "":
                    start = max(size - int(b), 0)
                else:
                    start = int(a)
                    if b:
                        end = min(int(b), size - 1)
                code = 206
            except ValueError:
                start, end, code = 0, size - 1, 200
            if code == 206 and (start > end or start >= size):
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        if download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        self.end_headers()
        remaining = end - start + 1
        try:
            with open(path, "rb") as f:
                f.seek(start)
                while remaining > 0:
                    chunk = f.read(min(1 << 16, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ---- GET
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            data = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif url.path == "/api/status":
            job = JOBS.get(parse_qs(url.query).get("id", [""])[0])
            self.send_json(job or {"state": "error", "message": "Unknown job."}, 200 if job else 404)
        elif url.path == "/api/settings":
            s = sm.load_settings()
            self.send_json({"has_key": bool(s["pexels_key"]), "has_pixabay_key": bool(s["pixabay_key"]),
                            "ollama_model": s["ollama_model"], "version": sm.__version__,
                            "voice": s["voice"], "voices": VOICES, "ai_ready": ai.ai_ready(),
                            "visual_mode": s["visual_mode"], "ai_image_quality": s["ai_image_quality"],
                            "video_seconds": sm.clamp_seconds(s["video_seconds"]),
                            "image_style": s["image_style"], "intro_button": s["intro_button"],
                            "story_format": s["story_format"], "story_tone": s["story_tone"],
                            "story_ending": s["story_ending"],
                            "image_styles": [[k, v[0]] for k, v in sm.IMAGE_STYLES.items()]})
        elif url.path == "/api/story-options":
            self.send_json(story_options())
        elif url.path == "/api/series":
            self.send_json({"items": storylib.load_series(sm.SETTINGS_DIR)})
        elif url.path == "/api/unfinished":
            self.send_json({"items": sm.list_unfinished()[:3]})
        elif url.path == "/api/videos":
            self.send_json(list_videos())
        elif url.path.startswith("/video/"):
            name = os.path.basename(unquote(url.path[7:]))
            path = os.path.join(sm.OUTPUT_DIR, name)
            if name.endswith(".mp4") and os.path.isfile(path):
                dl = name if "download" in parse_qs(url.query) else None
                self.send_file(path, "video/mp4", dl)
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    # ---- POST
    def do_POST(self):
        url = urlparse(self.path)
        body = self.read_json()
        route = url.path
        if route == "/api/generate":
            return self.post_generate(body)
        if route == "/api/resume":
            return self.post_resume(body)
        if route == "/api/discard":
            sm.discard_unfinished(str(body.get("key", "")))
            return self.send_json({"ok": True})
        if route == "/api/draft":
            idea = str(body.get("idea", "")).strip()
            if not idea:
                return self.send_json({"error": "Type an idea first."}, 400)
            seconds = sm.clamp_seconds(body.get("seconds", 45))
            story = story_from_body(body)
            sm.save_settings({"video_seconds": seconds})
            return self.start("draft", run_draft, idea, str(body.get("style", "")).strip(), seconds, story, pct=5)
        if route == "/api/hooks":
            script = body.get("script") if isinstance(body.get("script"), dict) else None
            return self.start("hooks", run_hooks, str(body.get("idea", "")).strip(), script, pct=5)
        if route == "/api/rewrite":
            script = body.get("script") if isinstance(body.get("script"), dict) else None
            index = body.get("index")
            if not script or not isinstance(index, int):
                return self.send_json({"error": "Nothing to rewrite."}, 400)
            return self.start("rewrite", run_rewrite, script, index, str(body.get("instruction", ""))[:300],
                              story_from_body(body), pct=10)
        if route == "/api/series/plan":
            topic = str(body.get("topic", "")).strip()
            if not topic:
                return self.send_json({"error": "Type what the series is about first."}, 400)
            try:
                parts = max(2, min(8, int(body.get("parts", 4))))
            except (TypeError, ValueError):
                parts = 4
            story = storylib.normalize({"format": body.get("story_format"), "tone": body.get("tone"),
                                        "bible": body.get("bible")})
            return self.start("series", run_series_plan, topic, parts, story["format"], story["tone"], story["bible"], pct=10)
        if route == "/api/series/save":
            try:
                series = storylib.clean_series(body.get("series"))
            except ValueError as err:
                return self.send_json({"error": f"That series can't be saved ({err})."}, 400)
            if not storylib.slug_ok(series["id"]):
                series["id"] = uuid.uuid4().hex[:8]
            items = [s for s in storylib.load_series(sm.SETTINGS_DIR) if s.get("id") != series["id"]]
            items.insert(0, series)
            storylib.save_series(sm.SETTINGS_DIR, items[:30])
            return self.send_json({"series": series})
        if route == "/api/series/delete":
            sid = str(body.get("id", ""))
            items = [s for s in storylib.load_series(sm.SETTINGS_DIR) if s.get("id") != sid]
            storylib.save_series(sm.SETTINGS_DIR, items)
            return self.send_json({"ok": True})
        if route == "/api/reveal":
            return self.post_reveal(body)
        if route == "/api/delete":
            return self.post_delete(body)
        if route == "/api/setup-ai":
            return self.start("setup", run_setup, pct=0)
        if route == "/api/settings":
            return self.post_settings(body)
        self.send_error(404)

    def post_generate(self, body):
        idea = str(body.get("idea", "")).strip()
        script = body.get("script") if isinstance(body.get("script"), dict) else None
        if not idea and not script:
            return self.send_json({"error": "Type an idea first."}, 400)
        mode = body.get("mode") if body.get("mode") in ("stock", "ai_images") else None
        if mode == "ai_images" and not ai.ai_ready():
            return self.send_json({"error": "AI images aren't set up yet. Click \"Set up AI images\" first."}, 400)
        story = story_from_body(body)
        remember = {}
        if mode:
            remember["visual_mode"] = mode
        if body.get("quality") in ai.SIZES:
            remember["ai_image_quality"] = body["quality"]
        seconds = sm.clamp_seconds(body.get("seconds", 45))
        remember["video_seconds"] = seconds
        if body.get("intro") in ("subscribe", "follow", "both"):
            remember["intro_button"] = body["intro"]
        image_style = body.get("image_style") if body.get("image_style") in sm.IMAGE_STYLES else "auto"
        remember["image_style"] = image_style
        if story and not story.get("part"):   # a series part follows its series, so don't overwrite the person's usual choices
            remember.update(story_format=story["format"], story_tone=story["tone"], story_ending=story["ending"])
        sm.save_settings(remember)
        self.start("video", run_job, idea, str(body.get("style", "")).strip(), mode, seconds, script,
                   None if image_style == "auto" else image_style, story)

    def post_resume(self, body):
        st = sm.get_unfinished(str(body.get("key", "")))
        if not st:
            return self.send_json({"error": "That unfinished video is no longer available."}, 404)
        if st.get("mode_arg") == "ai_images" and not ai.ai_ready():
            return self.send_json({"error": "AI images aren't set up on this computer."}, 400)
        self.start("video", run_job, st.get("idea", ""), st.get("style", ""), st.get("mode_arg"), st.get("seconds"),
                   st["script"] if st.get("from_project") else None, st.get("image_arg"), st.get("story_arg"),
                   message="Picking up where it left off...")

    def post_reveal(self, body):
        name = os.path.basename(str(body.get("name", "")))
        path = os.path.join(sm.OUTPUT_DIR, name)
        if not name.endswith(".mp4") or not os.path.isfile(path):
            return self.send_json({"error": "That video wasn't found."}, 404)
        try:  # show the file in File Explorer / Finder so it can be dragged onto an upload page
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", path])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(path)])
        except OSError as err:
            return self.send_json({"error": f"Couldn't open the folder ({err}). The video is in: {os.path.dirname(path)}"}, 500)
        self.send_json({"ok": True})

    def post_delete(self, body):
        name = os.path.basename(str(body.get("name", "")))
        path = os.path.join(sm.OUTPUT_DIR, name)
        if not name.endswith(".mp4") or not os.path.isfile(path):
            return self.send_json({"error": "That video wasn't found."}, 404)
        try:
            os.remove(path)
            notes = path[:-4] + ".txt"
            if os.path.isfile(notes):
                os.remove(notes)
        except OSError as err:
            return self.send_json({"error": f"Couldn't delete it ({err}). Close anything that is playing it and try again."}, 500)
        self.send_json({"ok": True})

    def post_settings(self, body):
        updates = {}
        for k in ("pexels_key", "pixabay_key"):
            if str(body.get(k, "")).strip():
                updates[k] = body[k]
        for k in ("ollama_model", "voice", "ai_image_quality", "visual_mode", "image_style"):
            if str(body.get(k, "")).strip():
                updates[k] = body[k]
        if body.get("story_format") in storylib.STORY_FORMATS:
            updates["story_format"] = body["story_format"]
        if body.get("story_tone") in storylib.TONES:
            updates["story_tone"] = body["story_tone"]
        if body.get("story_ending") in storylib.ENDINGS:
            updates["story_ending"] = body["story_ending"]
        sm.save_settings(updates)
        self.send_json({"ok": True})


def main():
    os.makedirs(sm.OUTPUT_DIR, exist_ok=True)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        raise SystemExit(f"Port {PORT} is already in use. Is Shorts Maker already open in another window?")
    url = f"http://localhost:{PORT}"
    print(f"\nShorts Maker is running at {url}")
    print("Keep this window open while you use it. Press Ctrl+C (or close the window) to stop.\n")
    if not os.environ.get("SHORTS_NO_BROWSER"):
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
