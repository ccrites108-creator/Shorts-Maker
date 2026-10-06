"""
Shorts Maker - the web page.

Run this file (or double-click "Start Shorts Maker.bat"). Your browser opens a page
where you type an idea and get a finished YouTube Short.
Everything runs on your own computer; nothing here is reachable from the internet.

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


def run_setup(job_id):
    job = JOBS[job_id]

    def progress(pct, msg):
        job["pct"] = pct
        job["message"] = msg

    try:
        ai.setup_ai(progress)
        job.update(state="done", pct=100, message="AI images are ready!")
    except ai.AIError as err:
        job.update(state="error", message=str(err))
    except Exception as err:
        traceback.print_exc()
        job.update(state="error", message=f"Something unexpected went wrong: {err}")


def run_job(job_id, idea, style, mode, seconds=None, script=None, image_style=None):
    job = JOBS[job_id]

    def progress(pct, msg):
        if pct is not None:
            job["pct"] = pct
        job["message"] = msg

    try:
        def steps(items):
            job["steps"] = items

        result = sm.make_video(idea, style, "ollama", progress, fake_audio=FAKE_AUDIO, visual_mode=mode,
                               steps=steps, seconds=seconds, script=script, image_style=image_style)
        job.update(state="done", pct=100, message="Done!", result={
            "name": result["name"], "title": result["title"],
            "description": result["description"], "script": result["script"],
            "warnings": result.get("warnings", [])})
    except sm.PipelineError as err:
        job.update(state="error", message=str(err) + saved_note())
    except Exception as err:  # something unexpected: show it, and print details in the console
        traceback.print_exc()
        job.update(state="error", message=f"Something unexpected went wrong: {err}" + saved_note())


def saved_note():
    """After a failed video: tell the person their finished scenes are kept."""
    return ("\n\nYour progress is saved. Click Continue under the button (or Make my video again with the same "
            "settings) and it picks up where it stopped.") if sm.list_unfinished() else ""


def run_draft(job_id, idea, style, seconds):
    job = JOBS[job_id]

    def progress(pct, msg):
        job["message"] = msg

    try:
        script = sm.draft_script(idea, style, "ollama", progress, seconds)
        job.update(state="done", pct=100, message="Script ready.", result={"script": script})
    except sm.PipelineError as err:
        job.update(state="error", message=str(err))
    except Exception as err:
        traceback.print_exc()
        job.update(state="error", message=f"Something unexpected went wrong: {err}")


def run_hooks(job_id, idea, script):
    job = JOBS[job_id]
    try:
        job["message"] = "Thinking up new hooks..."
        try:
            script = sm.clean_script(script) if script else None
        except ValueError:
            script = None
        hooks = sm.suggest_hooks(idea, script, sm.load_settings())
        job.update(state="done", pct=100, message="Here are some hooks.", result={"hooks": hooks})
    except sm.PipelineError as err:
        job.update(state="error", message=str(err))
    except Exception as err:
        traceback.print_exc()
        job.update(state="error", message=f"Something unexpected went wrong: {err}")


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
    return items[:30]


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
            return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except ValueError:
            return {}

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

    # ---- routes
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
                            "ollama_model": s["ollama_model"],
                            "voice": s["voice"], "voices": VOICES, "ai_ready": ai.ai_ready(),
                            "visual_mode": s["visual_mode"], "ai_image_quality": s["ai_image_quality"],
                            "video_seconds": sm.clamp_seconds(s["video_seconds"]),
                            "image_style": s["image_style"], "intro_button": s["intro_button"],
                            "image_styles": [[k, v[0]] for k, v in sm.IMAGE_STYLES.items()]})
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

    def do_POST(self):
        url = urlparse(self.path)
        body = self.read_json()
        if url.path == "/api/generate":
            idea = str(body.get("idea", "")).strip()
            script = body.get("script") if isinstance(body.get("script"), dict) else None
            if not idea and not script:
                return self.send_json({"error": "Type an idea first."}, 400)
            mode = body.get("mode") if body.get("mode") in ("stock", "ai_images") else None
            if mode == "ai_images" and not ai.ai_ready():
                return self.send_json({"error": "AI images aren't set up yet. Click \"Set up AI images\" first."}, 400)
            with LOCK:
                if any(j["state"] == "running" for j in JOBS.values()):
                    return self.send_json({"error": "Something is already running. Please wait for it to finish."}, 409)
                job_id = uuid.uuid4().hex[:8]
                JOBS[job_id] = {"state": "running", "kind": "video", "pct": 1, "message": "Starting..."}
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
            if remember:
                sm.save_settings(remember)
            threading.Thread(target=run_job, args=(job_id, idea, str(body.get("style", "")).strip(), mode, seconds, script,
                                   None if image_style == "auto" else image_style),
                             daemon=True).start()
            self.send_json({"id": job_id})
        elif url.path == "/api/discard":
            sm.discard_unfinished(str(body.get("key", "")))
            self.send_json({"ok": True})
        elif url.path == "/api/resume":
            st = sm.get_unfinished(str(body.get("key", "")))
            if not st:
                return self.send_json({"error": "That unfinished video is no longer available."}, 404)
            if st.get("mode_arg") == "ai_images" and not ai.ai_ready():
                return self.send_json({"error": "AI images aren't set up on this computer."}, 400)
            with LOCK:
                if any(j["state"] == "running" for j in JOBS.values()):
                    return self.send_json({"error": "Something is already running. Please wait for it to finish."}, 409)
                job_id = uuid.uuid4().hex[:8]
                JOBS[job_id] = {"state": "running", "kind": "video", "pct": 1, "message": "Picking up where it left off..."}
            threading.Thread(target=run_job, args=(job_id, st.get("idea", ""), st.get("style", ""), st.get("mode_arg"),
                                                   st.get("seconds"), st["script"] if st.get("from_project") else None,
                                                   st.get("image_arg")), daemon=True).start()
            self.send_json({"id": job_id})
        elif url.path in ("/api/draft", "/api/hooks"):
            idea = str(body.get("idea", "")).strip()
            if url.path == "/api/draft" and not idea:
                return self.send_json({"error": "Type an idea first."}, 400)
            with LOCK:
                if any(j["state"] == "running" for j in JOBS.values()):
                    return self.send_json({"error": "Something is already running. Please wait for it to finish."}, 409)
                job_id = uuid.uuid4().hex[:8]
                kind = "draft" if url.path == "/api/draft" else "hooks"
                JOBS[job_id] = {"state": "running", "kind": kind, "pct": 5, "message": "Starting..."}
            if kind == "draft":
                sm.save_settings({"video_seconds": sm.clamp_seconds(body.get("seconds", 45))})
                args = (job_id, idea, str(body.get("style", "")).strip(), sm.clamp_seconds(body.get("seconds", 45)))
                threading.Thread(target=run_draft, args=args, daemon=True).start()
            else:
                script = body.get("script") if isinstance(body.get("script"), dict) else None
                threading.Thread(target=run_hooks, args=(job_id, idea, script), daemon=True).start()
            self.send_json({"id": job_id})
        elif url.path == "/api/reveal":
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
        elif url.path == "/api/delete":
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
        elif url.path == "/api/setup-ai":
            with LOCK:
                if any(j["state"] == "running" for j in JOBS.values()):
                    return self.send_json({"error": "Something is already running. Please wait for it to finish."}, 409)
                job_id = uuid.uuid4().hex[:8]
                JOBS[job_id] = {"state": "running", "kind": "setup", "pct": 0, "message": "Starting..."}
            threading.Thread(target=run_setup, args=(job_id,), daemon=True).start()
            self.send_json({"id": job_id})
        elif url.path == "/api/settings":
            updates = {}
            for k in ("pexels_key", "pixabay_key"):
                if str(body.get(k, "")).strip():
                    updates[k] = body[k]
            for k in ("ollama_model", "voice", "ai_image_quality", "visual_mode", "image_style"):
                if str(body.get(k, "")).strip():
                    updates[k] = body[k]
            sm.save_settings(updates)
            self.send_json({"ok": True})
        else:
            self.send_error(404)


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shorts Maker</title>
<style>
  :root { --bg:#f5f5f7; --panel:#ffffff; --line:#d2d2d7; --soft:#f5f5f7; --text:#1d1d1f; --muted:#6e6e73;
          --accent:#0071e3; --accent-hover:#0077ed; --bad:#d70015; --ok:#34c759;
          --notice-bg:#fff8e5; --notice-line:#f2dba0; --notice-text:#6b4e00;
          --shadow:0 1px 2px rgba(0,0,0,.04), 0 8px 28px rgba(0,0,0,.06); }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#000000; --panel:#1c1c1e; --line:#38383a; --soft:#2c2c2e; --text:#f5f5f7; --muted:#98989d;
            --accent:#0a84ff; --accent-hover:#409cff; --bad:#ff6961;
            --notice-bg:#2b2410; --notice-line:#5b4a10; --notice-text:#ffe08a; --shadow:none; }
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text); -webkit-font-smoothing:antialiased;
         font:16px/1.47 -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", system-ui, Roboto, sans-serif; }
  .wrap { max-width:1000px; margin:0 auto; padding:56px 24px 80px; }
  header { text-align:center; margin-bottom:40px; }
  h1 { font-size:44px; line-height:1.1; font-weight:700; letter-spacing:-.03em; margin:0; }
  .sub { color:var(--muted); font-size:19px; margin:10px 0 0; letter-spacing:-.01em; }
  .grid { display:grid; grid-template-columns:minmax(0,1fr) 320px; gap:32px; align-items:start; }
  @media (max-width:860px) { .grid { grid-template-columns:1fr; } h1 { font-size:36px; } }
  .side { position:sticky; top:24px; }
  @media (max-width:860px) { .side { position:static; } }
  .card { background:var(--panel); border-radius:22px; padding:28px; box-shadow:var(--shadow); }
  .card + .card { margin-top:24px; }
  h2 { font-size:21px; font-weight:600; letter-spacing:-.02em; margin:0 0 16px; }
  label { display:block; font-size:14px; font-weight:600; color:var(--muted); margin:0 0 8px; letter-spacing:-.005em; }
  textarea, input, select { width:100%; background:var(--panel); color:var(--text); border:1px solid var(--line);
         border-radius:12px; padding:13px 15px; font:inherit; transition:border-color .15s, box-shadow .15s; }
  textarea { min-height:104px; resize:vertical; }
  textarea:focus, input:focus, select:focus { outline:0; border-color:var(--accent); box-shadow:0 0 0 4px color-mix(in srgb, var(--accent) 25%, transparent); }
  ::placeholder { color:#a1a1a6; }
  .field { margin-bottom:22px; }
  .hint { color:var(--muted); font-size:14px; margin-top:8px; }
  button { font:inherit; font-weight:600; border:0; border-radius:980px; padding:12px 22px; cursor:pointer; transition:background .15s, opacity .15s; }
  .primary { background:var(--accent); color:#fff; width:100%; font-size:17px; padding:15px 22px; }
  .primary:hover { background:var(--accent-hover); }
  .primary:disabled { opacity:.5; cursor:wait; }
  .ghost { background:var(--soft); color:var(--accent); padding:9px 18px; font-size:15px; }
  .ghost:hover { filter:brightness(.96); }
  .seg { display:flex; background:var(--soft); border-radius:12px; padding:3px; gap:2px; }
  .seg button { flex:1; background:transparent; color:var(--text); border-radius:10px; padding:9px 10px; font-size:15px; font-weight:500; }
  .seg button small { display:block; font-size:11px; font-weight:400; color:var(--muted); margin-top:1px; letter-spacing:0; }
  .seg button.on { background:var(--panel); box-shadow:0 1px 3px rgba(0,0,0,.15); font-weight:600; }
  @media (prefers-color-scheme: dark) { .seg button.on { background:#636366; } }
  .bar { height:6px; background:var(--soft); border-radius:99px; overflow:hidden; margin:18px 0 10px; }
  .bar i { display:block; height:100%; width:0; background:var(--accent); border-radius:99px; transition:width .6s; }
  .msg { color:var(--muted); min-height:24px; font-size:15px; }
  #progress { margin-top:26px; }
  .steps { list-style:none; margin:0; padding:0; }
  .steps li { display:flex; align-items:center; gap:14px; padding:11px 2px; border-top:1px solid var(--line); color:var(--muted); font-size:15px; }
  .steps li:first-child { border-top:0; }
  .steps .dot { flex:none; width:24px; height:24px; border-radius:50%; border:2px solid var(--line); display:grid; place-items:center;
                font-size:13px; font-weight:700; color:transparent; }
  .steps li.active, .steps li.done { color:var(--text); }
  .steps li.active .dot { border-color:var(--accent); border-top-color:transparent; animation:spin 1s linear infinite; }
  .steps li.done .dot { background:var(--ok); border-color:var(--ok); color:#fff; }
  .steps li.done .dot::before { content:"\2713"; }
  @keyframes spin { to { transform:rotate(360deg); } }
  .err { color:var(--bad); white-space:pre-wrap; font-size:15px; }
  .notice { background:var(--notice-bg); border:1px solid var(--notice-line); color:var(--notice-text); border-radius:14px;
            padding:14px 16px; margin-bottom:22px; font-size:15px; }
  a { color:var(--accent); text-decoration:none; }
  a:hover { text-decoration:underline; }
  details summary { cursor:pointer; font-size:21px; font-weight:600; letter-spacing:-.02em; list-style:none; display:flex; justify-content:space-between; align-items:center; }
  details summary::-webkit-details-marker { display:none; }
  details summary::after { content:"\203A"; font-size:28px; color:var(--muted); transform:rotate(90deg); transition:transform .2s; }
  details[open] summary::after { transform:rotate(-90deg); }
  details .inner { margin-top:22px; }
  .phone { aspect-ratio:9/16; background:#000; border-radius:36px; overflow:hidden; display:grid; place-items:center;
           color:#8e8e93; text-align:center; padding:24px; box-shadow:0 12px 40px rgba(0,0,0,.18); font-size:15px; }
  .phone video { width:100%; height:100%; object-fit:cover; background:#000; }
  .row { display:flex; gap:8px; flex-wrap:wrap; margin-top:14px; }
  .meta { margin-top:20px; }
  .meta b { display:block; font-size:17px; letter-spacing:-.01em; }
  .meta p { margin:4px 0 8px; color:var(--muted); font-size:15px; }
  ul.list { list-style:none; padding:0; margin:0; }
  ul.list li { padding:13px 0; border-top:1px solid var(--line); font-size:15px; }
  ul.list li:first-child { border-top:0; padding-top:0; }
  ul.list a { color:var(--text); cursor:pointer; }
  .vrow { display:flex; align-items:center; justify-content:space-between; gap:12px; }
  .vrow a { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .del { flex:none; display:flex; gap:6px; }
  .mini { background:var(--soft); color:var(--muted); font-size:13px; font-weight:600; padding:6px 12px; }
  .mini:hover { filter:brightness(.95); }
  .mini.danger { background:#ff3b30; color:#fff; }
  ul.list a:hover { color:var(--accent); text-decoration:none; }
  input[type=range] { -webkit-appearance:none; appearance:none; padding:0; height:6px; border:0; border-radius:99px;
                      background:var(--soft); box-shadow:none; margin:8px 0 4px; }
  input[type=range]::-webkit-slider-thumb { -webkit-appearance:none; width:26px; height:26px; border-radius:50%; background:#fff;
                      border:0; box-shadow:0 1px 4px rgba(0,0,0,.35); cursor:pointer; }
  input[type=range]::-moz-range-thumb { width:26px; height:26px; border-radius:50%; background:#fff; border:0;
                      box-shadow:0 1px 4px rgba(0,0,0,.35); cursor:pointer; }
  input[type=range]:focus { box-shadow:0 0 0 4px color-mix(in srgb, var(--accent) 25%, transparent); }
  .scale { display:flex; justify-content:space-between; color:var(--muted); font-size:13px; }
  .scene { background:var(--soft); border-radius:16px; padding:16px; margin-bottom:14px; }
  .scene .field { margin-bottom:14px; }
  .scene textarea, .scene input, .scene select { background:var(--panel); }
  .scene textarea { min-height:64px; }
  .sh { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
  .sh b { font-size:15px; }
  .acts { display:flex; gap:6px; }
  .acts .mini { background:var(--panel); padding:5px 11px; }
  .acts .mini:disabled { opacity:.35; cursor:default; }
  #editor:not(.ai) .ai-only { display:none; }
  #editor.ai .stock-only { display:none; }
  .chips { display:flex; flex-direction:column; gap:8px; margin-top:12px; }
  .chip { text-align:left; background:var(--panel); color:var(--text); border-radius:14px; padding:10px 14px; font-weight:400; font-size:15px; }
  .chip small { display:block; color:var(--accent); font-weight:600; font-size:12px; margin-bottom:2px; }
  .chip:hover { box-shadow:0 0 0 2px var(--accent) inset; }
  .post { margin-top:22px; padding-top:18px; border-top:1px solid var(--line); }
  .post p { margin:4px 0 0; color:var(--muted); font-size:14px; }
  .check { display:flex; align-items:center; gap:8px; font-weight:400; font-size:14px; color:var(--muted); margin:-4px 0 14px; }
  .check input { width:auto; }
  .summary { color:var(--muted); font-size:14px; margin:6px 0 16px; }
  code { background:var(--soft); border-radius:6px; padding:1px 6px; font-size:.9em; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Shorts Maker</h1>
    <p class="sub">Type an idea. Get a finished video.</p>
  </header>

  <div class="grid">
    <div>
      <div class="card">
        <div id="keyNotice" class="notice" hidden>
          For real footage that matches each scene, add a free Pixabay key in <b>Settings</b> below.
          Without it, videos use colored backgrounds.
        </div>
        <div class="field">
          <label for="idea">Idea</label>
          <textarea id="idea" placeholder="e.g. 3 strange facts about octopuses"></textarea>
        </div>
        <div class="field">
          <label for="style">Style or niche <span style="font-weight:400">(optional)</span></label>
          <input id="style" placeholder="e.g. calm and motivational, or fast and funny">
        </div>
        <div class="field">
          <label for="length">Length <span id="lengthVal" style="font-weight:600;color:var(--text)">45 seconds</span></label>
          <input type="range" id="length" min="30" max="90" step="5" value="45">
          <div class="scale"><span>30 s</span><span>60 s</span><span>90 s</span></div>
          <div class="hint" id="lengthHint"></div>
        </div>
        <div class="field">
          <label for="intro">Button at the start</label>
          <div class="seg" data-for="intro">
            <button type="button" data-v="subscribe">Subscribe</button>
            <button type="button" data-v="follow">Follow</button>
            <button type="button" data-v="both">Both</button>
          </div>
          <select id="intro" hidden>
            <option value="subscribe">Subscribe</option>
            <option value="follow">Follow</option>
            <option value="both">Both</option>
          </select>
          <div class="hint">Subscribe suits YouTube, Follow suits TikTok. Both shows one after the other (the intro is a little longer).</div>
        </div>
        <div class="field">
          <label for="mode">Pictures</label>
          <div class="seg" data-for="mode">
            <button type="button" data-v="stock">Stock footage</button>
            <button type="button" data-v="ai_images">AI images</button>
          </div>
          <select id="mode" hidden>
            <option value="stock">Stock footage</option>
            <option value="ai_images">AI images</option>
          </select>
          <div class="hint" id="modeHint"></div>
        </div>
        <div class="field" id="qualityField" hidden>
          <label for="quality">AI picture detail</label>
          <div class="seg" data-for="quality">
            <button type="button" data-v="fast">Fast<small>Quickest, a bit softer</small></button>
            <button type="button" data-v="standard">Standard<small>Balanced</small></button>
            <button type="button" data-v="high">High<small>Sharpest, slowest</small></button>
          </div>
          <select id="quality" hidden>
            <option value="fast">Fast</option>
            <option value="standard">Standard</option>
            <option value="high">High</option>
          </select>
        </div>
        <div id="aiSetup" class="notice" hidden>
          AI images need a one-time download (about 7 GB) of open-source software and models.
          Keep this window open while it downloads. If it stops, click the button again and it continues.
          <div style="margin-top:10px"><button class="ghost" id="setupBtn">Set up AI images</button></div>
        </div>
        <div class="field" id="styleField" hidden>
          <label for="imgstyle">Look of the AI pictures</label>
          <select id="imgstyle"></select>
          <div class="hint">Auto lets the script pick a look that fits the idea.</div>
        </div>
        <div class="field">
          <label>How do you want to make it?</label>
          <div class="seg" data-for="flow">
            <button type="button" data-v="quick">Quick create<small>Just a prompt</small></button>
            <button type="button" data-v="project">Custom project<small>Edit scenes and hook</small></button>
          </div>
          <select id="flow" hidden><option value="quick">Quick create</option><option value="project">Custom project</option></select>
          <div class="hint" id="flowHint"></div>
        </div>
        <button id="go" class="primary">Make my video</button>
        <div id="resumeBox" class="notice" hidden></div>
        <div id="progress" hidden>
          <ul class="steps" id="steps"></ul>
          <div class="bar"><i id="fill"></i></div>
          <div class="msg" id="msg"></div>
        </div>
        <div id="error" class="err" style="margin-top:14px"></div>
      </div>

      <div class="card" id="editor" hidden>
        <h2>Your project</h2>
        <div class="field">
          <label for="ptitle">Title</label>
          <input id="ptitle">
        </div>
        <div class="field">
          <label for="pdesc">Description</label>
          <textarea id="pdesc" style="min-height:70px"></textarea>
        </div>
        <label>Scenes</label>
        <div id="scenes"></div>
        <button class="ghost needs-idle" id="addScene">+ Add scene</button>
        <div class="summary" id="projLen" style="margin-top:16px"></div>
        <button id="makeProject" class="primary needs-idle">Make video from this project</button>
      </div>

      <div class="card">
        <details id="settings">
          <summary>Settings</summary>
          <div class="inner">
          <div class="field">
            <label for="pixabay">Pixabay API key (stock pictures and clips)</label>
            <input id="pixabay" type="password" autocomplete="off" placeholder="Paste your key here">
            <div class="hint">Free: make an account at <a href="https://pixabay.com/accounts/register/" target="_blank" rel="noopener">pixabay.com</a>, then your key is shown on <a href="https://pixabay.com/api/docs/" target="_blank" rel="noopener">pixabay.com/api/docs</a>.</div>
          </div>
          <div class="field">
            <label for="pexels">Pexels API key (optional)</label>
            <input id="pexels" type="password" autocomplete="off" placeholder="Paste your key here">
            <div class="hint">Pexels has paused new keys. If you already have one, it works here too.</div>
          </div>
          <div class="field">
            <label for="voice">Voice</label>
            <select id="voice"></select>
          </div>
          <div class="field">
            <label for="model">Script model (Ollama)</label>
            <input id="model" placeholder="llama3.2">
            <div class="hint">Any model you've downloaded with <code>ollama pull</code>. Bigger models write better scripts.</div>
          </div>
          <button class="ghost" id="save">Save settings</button>
          <span class="hint" id="saved" style="margin-left:10px"></span>
          </div>
        </details>
      </div>

      <div class="card">
        <h2>Your videos</h2>
        <ul class="list" id="videos"><li class="hint">Nothing yet.</li></ul>
      </div>
    </div>

    <div class="side">
      <div class="phone" id="phone">Your video will appear here</div>
      <div class="meta" id="meta" hidden>
        <b id="mtitle"></b>
        <p id="mdesc"></p>
        <div class="row">
          <button class="ghost" id="copyTitle">Copy title</button>
          <button class="ghost" id="copyDesc">Copy description</button>
          <a id="dl" class="ghost" style="text-decoration:none;border-radius:980px;padding:9px 18px;font-weight:600;font-size:15px">Download</a>
        </div>
        <div class="post">
          <b>Post it</b>
          <p>Show the file, open the upload page, then drag the video onto it. Your title and description are one click away.</p>
          <div class="row">
            <button class="ghost" id="reveal">Show video file</button>
            <a class="ghost" href="https://www.youtube.com/upload" target="_blank" rel="noopener" style="text-decoration:none">YouTube upload</a>
            <a class="ghost" href="https://www.tiktok.com/upload" target="_blank" rel="noopener" style="text-decoration:none">TikTok upload</a>
          </div>
        </div>
        <p class="hint" style="margin-top:12px">Read the script text before posting. AI can get facts wrong.</p>
      </div>
    </div>
  </div>
</div>

<script>
const $ = id => document.getElementById(id);
let timer = null, current = null;

async function api(path, body) {
  const opts = body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {};
  const r = await fetch(path, opts);
  return r.json();
}

function show(name, title, desc) {
  current = {name, title, desc};
  $('phone').innerHTML = '';
  const v = document.createElement('video');
  v.src = '/video/' + encodeURIComponent(name) + '?t=' + Date.now();
  v.controls = true; v.autoplay = true; v.playsInline = true;
  $('phone').appendChild(v);
  $('mtitle').textContent = title;
  $('mdesc').textContent = desc || '';
  $('dl').href = '/video/' + encodeURIComponent(name) + '?download=1';
  $('meta').hidden = false;
}

async function removeVideo(name) {
  if (current && current.name === name) {  // stop playing it first, Windows won't delete a file that is open
    $('phone').innerHTML = 'Your video will appear here'; $('meta').hidden = true; current = null;
  }
  await new Promise(r => setTimeout(r, 300));
  const res = await api('/api/delete', {name});
  if (res.error) $('error').textContent = res.error;
  loadVideos();
}

async function loadVideos() {
  const items = await api('/api/videos');
  const ul = $('videos');
  ul.innerHTML = '';
  if (!items.length) { ul.innerHTML = '<li class="hint">Nothing yet.</li>'; return; }
  for (const it of items) {
    const li = document.createElement('li'), a = document.createElement('a'), del = document.createElement('span');
    li.className = 'vrow';
    a.textContent = it.title + (it.when ? '  ·  ' + it.when : '');
    a.onclick = () => show(it.name, it.title, it.desc || '');
    del.className = 'del';
    const ask = () => {
      del.innerHTML = '<button class="mini danger">Delete</button><button class="mini">Keep</button>';
      del.firstChild.onclick = () => removeVideo(it.name);
      del.lastChild.onclick = idle;
    };
    const idle = () => { del.innerHTML = '<button class="mini" aria-label="Delete video">Delete…</button>'; del.firstChild.onclick = ask; };
    idle();
    li.appendChild(a); li.appendChild(del); ul.appendChild(li);
  }
}

let cfg = {has_key: false, ai_ready: false};

async function loadSettings() {
  const s = await api('/api/settings');
  cfg = s;
  $('pexels').placeholder = s.has_key ? 'Key saved. Paste a new one to replace it.' : 'Paste your key here';
  $('pixabay').placeholder = s.has_pixabay_key ? 'Key saved. Paste a new one to replace it.' : 'Paste your key here';
  $('model').value = s.ollama_model;
  $('voice').innerHTML = s.voices.map(v => `<option value="${v[0]}">${v[1]}</option>`).join('');
  $('voice').value = s.voice;
  $('mode').value = (!s.has_key && !s.has_pixabay_key && s.ai_ready) ? 'ai_images' : s.visual_mode;
  $('quality').value = s.ai_image_quality;
  $('intro').value = s.intro_button || 'subscribe';
  $('length').value = s.video_seconds || 45;
  updateLength();
  const opts = '<option value="auto">Auto</option>' + (s.image_styles || []).map(x => `<option value="${x[0]}">${x[1]}</option>`).join('');
  $('imgstyle').innerHTML = opts; $('imgstyle').value = s.image_style || 'auto';
  updateFlow();
  updateMode();
}

function updateMode() {
  const ai = $('mode').value === 'ai_images';
  $('qualityField').hidden = !ai;
  $('styleField').hidden = !ai;
  $('editor').classList.toggle('ai', ai);
  $('keyNotice').hidden = ai || cfg.has_key || cfg.has_pixabay_key;
  $('aiSetup').hidden = !(ai && !cfg.ai_ready);
  syncSegs();
  if ($('length')) updateLength();
  $('modeHint').textContent = ai
    ? 'Pictures are painted by an open-source AI on your own computer. On built-in graphics each picture can take several minutes, so a video may take 15 to 30+ minutes.'
    : 'Real video clips and photos matched to each scene.';
}
$('mode').onchange = updateMode;

function updateLength() {
  const sec = +$('length').value, scenes = Math.max(4, Math.min(12, Math.round(sec / 7.5)));
  $('lengthVal').textContent = sec + ' seconds';
  const pct = (sec - 30) / 60 * 100;
  $('length').style.background = `linear-gradient(to right, var(--accent) ${pct}%, var(--soft) ${pct}%)`;
  const ai = $('mode').value === 'ai_images';
  $('lengthHint').textContent = 'About ' + scenes + ' scenes.' +
    (ai ? ' With AI images, every scene is painted one by one, so longer videos take much longer to make.' : '');
}
$('length').oninput = updateLength;

function syncSegs() {
  document.querySelectorAll('.seg').forEach(seg => [...seg.children].forEach(
    b => b.classList.toggle('on', b.dataset.v === $(seg.dataset.for).value)));
}
document.querySelectorAll('.seg').forEach(seg => seg.addEventListener('click', e => {
  const b = e.target.closest('button');
  if (!b) return;
  const sel = $(seg.dataset.for);
  sel.value = b.dataset.v;
  if (sel.onchange) sel.onchange();
  syncSegs();
}));

$('save').onclick = async () => {
  await api('/api/settings', {pexels_key: $('pexels').value, pixabay_key: $('pixabay').value,
                              ollama_model: $('model').value, voice: $('voice').value});
  $('pexels').value = ''; $('pixabay').value = '';
  $('saved').textContent = 'Saved.';
  setTimeout(() => $('saved').textContent = '', 2500);
  loadSettings();
};

$('go').onclick = async () => {
  const idea = $('idea').value.trim();
  $('error').textContent = '';
  if (!idea) { $('error').textContent = 'Type an idea first.'; return; }
  if ($('flow').value === 'project') return draftScript(idea);
  const res = await api('/api/generate', {idea, style: $('style').value, mode: $('mode').value, quality: $('quality').value, seconds: +$('length').value, image_style: $('imgstyle').value, intro: $('intro').value});
  if (res.error) { $('error').textContent = res.error; return; }
  setBusy(true, 'Making your video...');
  $('progress').hidden = false; $('meta').hidden = true;
  renderSteps([{label: 'Write the script', state: 'active'}]);
  $('phone').textContent = 'Working on it. This takes a while.';
  clearInterval(timer);
  timer = setInterval(() => poll(res.id), 1500);
};

$('setupBtn').onclick = async () => {
  $('error').textContent = '';
  const res = await api('/api/setup-ai', {});
  if (res.error) { $('error').textContent = res.error; return; }
  $('setupBtn').disabled = true; setBusy(true);
  $('progress').hidden = false;
  clearInterval(timer);
  timer = setInterval(() => poll(res.id), 1500);
};

function renderSteps(items) {
  $('steps').innerHTML = items.map(i =>
    `<li class="${i.state}"><span class="dot"></span><span></span></li>`).join('');
  [...$('steps').children].forEach((li, n) => li.lastChild.textContent = items[n].label);
}

async function poll(id) {
  const s = await api('/api/status?id=' + id);
  $('fill').style.width = (s.pct || 0) + '%';
  $('msg').textContent = s.message || '';
  renderSteps(s.steps || []);
  if (s.state === 'done') {
    clearInterval(timer); finish();
    if (s.kind === 'setup') { await loadSettings(); $('modeHint').textContent = 'AI images are ready to use.'; return; }
    if (s.kind === 'draft') {
      project = s.result.script; hooks = []; renderEditor(); $('editor').hidden = false;
      $('editor').scrollIntoView({behavior: 'smooth'}); return;
    }
    if (s.kind === 'hooks') { hooks = s.result.hooks; renderEditor(); return; }
    show(s.result.name, s.result.title, s.result.description);
    $('error').style.whiteSpace = 'pre-wrap';
    $('error').textContent = (s.result.warnings || []).join('\n\n');
    loadVideos();
  } else if (s.state === 'error') {
    clearInterval(timer); finish();
    if (s.kind === 'video') $('phone').textContent = 'Your video will appear here';
    $('error').textContent = s.message;
  }
}

async function loadUnfinished() {
  let items = [];
  try { items = (await api('/api/unfinished')).items || []; } catch (e) {}
  const box = $('resumeBox');
  box.hidden = !items.length;
  box.innerHTML = '';
  items.forEach(it => {
    const row = el('div', {style: 'margin:4px 0'},
      el('b', {}, (it.idea || 'Unfinished video').slice(0, 60)), ' - ' + it.done + ' of ' + it.total + ' scenes finished  ',
      el('button', {class: 'ghost', onclick: () => resumeVideo(it.key)}, 'Continue'), ' ',
      el('button', {class: 'ghost', onclick: async () => { await api('/api/discard', {key: it.key}); loadUnfinished(); }}, 'Discard'));
    box.append(row);
  });
}

async function resumeVideo(key) {
  $('error').textContent = '';
  const res = await api('/api/resume', {key});
  if (res.error) { $('error').textContent = res.error; return; }
  setBusy(true, 'Making your video...');
  $('progress').hidden = false; $('meta').hidden = true;
  renderSteps([{label: 'Picking up where it left off', state: 'active'}]);
  $('phone').textContent = 'Working on it. This takes a while.';
  clearInterval(timer);
  timer = setInterval(() => poll(res.id), 1500);
}

function finish() {
  loadUnfinished();
  setBusy(false, goLabel());
  $('setupBtn').disabled = false;
  $('progress').hidden = true;
}


// ---------------------------------------------------------------- custom project editor
let project = null, hooks = [];

function el(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v; else if (k.startsWith('on')) e[k] = v; else e.setAttribute(k, v);
  }
  kids.flat().forEach(c => e.append(c));
  return e;
}
const field = (label, input, cls = '') => el('div', {class: 'field ' + cls}, el('label', {}, label), input);
const miniBtn = (text, fn, disabled) => { const b = el('button', {class: 'mini', type: 'button'}, text); b.onclick = fn; b.disabled = !!disabled; return b; };

function updateProjLen() {
  const words = project.scenes.reduce((n, s) => n + s.narration.split(/\s+/).filter(Boolean).length, 0);
  $('projLen').textContent = 'About ' + Math.round(words / 2.5) + ' seconds spoken, ' + project.scenes.length + ' scenes.';
}

function styleOptions(selected) {
  const sel = el('select', {});
  sel.append(el('option', {value: ''}, 'Same as the whole project'));
  (cfg.image_styles || []).forEach(([k, name]) => sel.append(el('option', {value: k}, name)));
  sel.value = selected || '';
  return sel;
}

function renderEditor() {
  $('ptitle').value = project.title; $('pdesc').value = project.description;
  const box = $('scenes'); box.innerHTML = '';
  const last = project.scenes.length - 1;
  project.scenes.forEach((sc, i) => {
    const nar = el('textarea', {rows: '3'}); nar.value = sc.narration;
    nar.oninput = () => { sc.narration = nar.value; updateProjLen(); };
    const img = el('textarea', {rows: '2', placeholder: 'Describe the picture: the subject, the setting, the light'}); img.value = sc.image_prompt;
    img.oninput = () => { sc.image_prompt = img.value; };
    const look = styleOptions(sc.style); look.onchange = () => { sc.style = look.value; };
    const q = el('input', {placeholder: 'e.g. cat closeup'}); q.value = sc.visual_query;
    q.oninput = () => { sc.visual_query = q.value; };
    const head = el('div', {class: 'sh'}, el('b', {}, i === 0 ? 'Scene 1 · Hook' : 'Scene ' + (i + 1)),
      el('span', {class: 'acts'},
        miniBtn('↑', () => moveScene(i, -1), i === 0), miniBtn('↓', () => moveScene(i, 1), i === last),
        miniBtn('✕', () => removeScene(i), project.scenes.length <= 2)));
    const card = el('div', {class: 'scene'}, head,
      field(i === 0 ? 'Hook: the first thing people hear' : 'What the voice says', nar));
    if (i === 0) {
      const hb = el('button', {class: 'ghost needs-idle', type: 'button'}, 'Suggest new hooks');
      hb.onclick = suggestHooks;
      card.append(el('div', {class: 'field'}, hb, el('div', {class: 'chips'}, hooks.map(h => {
        const c = el('button', {class: 'chip needs-idle', type: 'button'}, el('small', {}, h.type), h.text);
        c.onclick = () => { project.scenes[0].narration = h.text; renderEditor(); };
        return c;
      }))));
    }
    const fresh = el('input', {type: 'checkbox'}); fresh.checked = !!sc.fresh;
    fresh.onchange = () => { sc.fresh = fresh.checked; };
    const freshRow = el('label', {class: 'check'}, fresh, ' Paint this picture again (otherwise the last one is reused)');
    card.append(el('div', {class: 'ai-only'}, field('Picture', img), field('Look of this picture', look), freshRow),
                el('div', {class: 'stock-only'}, field('Stock footage search words', q)));
    box.append(card);
  });
  updateProjLen();
  $('editor').classList.toggle('ai', $('mode').value === 'ai_images');
}

function moveScene(i, d) {
  const j = i + d, s = project.scenes;
  if (j < 0 || j >= s.length) return;
  [s[i], s[j]] = [s[j], s[i]]; renderEditor();
}
function removeScene(i) { project.scenes.splice(i, 1); renderEditor(); }
$('addScene').onclick = () => { project.scenes.push({narration: '', image_prompt: '', visual_query: '', style: ''}); renderEditor(); };
$('ptitle').oninput = () => { if (project) project.title = $('ptitle').value; };
$('pdesc').oninput = () => { if (project) project.description = $('pdesc').value; };

function setBusy(b, label) {
  document.querySelectorAll('.needs-idle, #go').forEach(x => x.disabled = b);
  if (label) $('go').textContent = label;
}

async function suggestHooks() {
  $('error').textContent = '';
  const res = await api('/api/hooks', {idea: $('idea').value, script: project});
  if (res.error) { $('error').textContent = res.error; return; }
  setBusy(true); $('progress').hidden = false; renderSteps([]);
  $('msg').textContent = 'Thinking up new hooks...'; $('fill').style.width = '10%';
  $('progress').scrollIntoView({behavior: 'smooth', block: 'center'});
  clearInterval(timer); timer = setInterval(() => poll(res.id), 1500);
}

async function draftScript(idea) {
  const res = await api('/api/draft', {idea, style: $('style').value, seconds: +$('length').value});
  if (res.error) { $('error').textContent = res.error; return; }
  setBusy(true, 'Writing the script...'); $('progress').hidden = false; renderSteps([]);
  clearInterval(timer); timer = setInterval(() => poll(res.id), 1500);
}

$('makeProject').onclick = async () => {
  $('error').textContent = '';
  const res = await api('/api/generate', {idea: $('idea').value.trim(), script: project, mode: $('mode').value,
    quality: $('quality').value, seconds: +$('length').value, image_style: $('imgstyle').value, intro: $('intro').value});
  if (res.error) { $('error').textContent = res.error; return; }
  setBusy(true, 'Making your video...'); $('progress').hidden = false; $('meta').hidden = true;
  $('phone').textContent = 'Working on it. This takes a while.';
  $('progress').scrollIntoView({behavior: 'smooth', block: 'center'});
  clearInterval(timer); timer = setInterval(() => poll(res.id), 1500);
};

function goLabel() { return $('flow').value === 'project' ? 'Write the script' : 'Make my video'; }
function updateFlow() {
  $('go').textContent = goLabel();
  $('flowHint').textContent = $('flow').value === 'project'
    ? 'Writes the script first, so you can edit the scenes, pictures and hook before the video is made.'
    : 'One click: type an idea and get a finished video.';
  syncSegs();
}
$('flow').onchange = updateFlow;
$('imgstyle').onchange = () => {};

$('reveal').onclick = async () => {
  if (!current) return;
  const res = await api('/api/reveal', {name: current.name});
  if (res.error) $('error').textContent = res.error;
};
$('copyTitle').onclick = () => navigator.clipboard.writeText(current.title);
$('copyDesc').onclick = () => navigator.clipboard.writeText(current.desc);

loadSettings(); loadVideos(); loadUnfinished();
</script>
</body>
</html>
"""


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
