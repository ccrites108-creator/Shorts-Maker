"""
Open-source AI image generation for Shorts Maker, running on your own computer.

  * Program:  stable-diffusion.cpp (MIT license), the Vulkan build, which works on
              AMD, Intel and NVIDIA graphics (including built-in graphics).
  * Model:    Z-Image-Turbo (Apache 2.0) in a compressed (GGUF) form, plus its text
              encoder (Qwen3, Apache 2.0) and image decoder (the FLUX.1 autoencoder, Apache 2.0).

Everything is downloaded once into the "ai" folder next to this file.

License: MIT (see LICENSE)
"""

import hashlib
import json
import os
import random
import shutil
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile

try:  # use the Windows certificate store, so downloads work behind antivirus/VPN/school/work HTTPS scanning
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass


HERE = os.path.dirname(os.path.abspath(__file__))
AI_DIR = os.environ.get("SHORTS_AI_DIR") or os.path.join(HERE, "ai")
SD_DIR = os.path.join(AI_DIR, "sd")
SD_CPU_DIR = os.path.join(AI_DIR, "sd-cpu")  # plain-processor build, used if the graphics chip runs out of memory
CPU_MARK = os.path.join(AI_DIR, "use_cpu.txt")
MODEL_DIR = os.path.join(AI_DIR, "models")

SD_RELEASE_API = os.environ.get(
    "SD_RELEASE_API", "https://api.github.com/repos/leejet/stable-diffusion.cpp/releases/latest")
HF = os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")
PROGRESS_EVERY = float(os.environ.get("SD_PROGRESS_SECONDS", "10"))
GENERATE_TIMEOUT = 40 * 60  # give up on a single picture after 40 minutes

# Picture sizes (width, height). Smaller is faster. All are 9:16 and divisible by 16.
SIZES = {"fast": (384, 672), "standard": (512, 896), "high": (640, 1120)}

# What to download. "prefer" lists compression levels from best fit to worst fit.
MODELS = [
    {"file": "zimage.gguf", "repo": "leejet/Z-Image-Turbo-GGUF", "ext": ".gguf",
     "prefer": ["Q4_K", "Q4_0", "Q5_K", "Q5_0", "Q3_K", "Q8_0"], "label": "the picture model", "band": (6, 56)},
    {"file": "qwen3.gguf", "repo": "unsloth/Qwen3-4B-Instruct-2507-GGUF", "ext": ".gguf",
     "prefer": ["Q4_K_M", "Q4_K_S", "Q5_K_M", "Q8_0"], "label": "the language model", "band": (56, 92)},
    # The decoder is the same small file in several places. Some of them ask for a login, so try
    # the ones that don't first and move on if one says no.
    {"file": "ae.safetensors", "label": "the image decoder", "band": (92, 100),
     "sources": [("Comfy-Org/z_image_turbo", "split_files/vae/ae.safetensors"),
                 ("receptektas/black-forest-labs-ae_safetensors", "ae.safetensors"),
                 ("black-forest-labs/FLUX.1-schnell", "ae.safetensors")]},
]


class AIError(Exception):
    """A problem we can explain to the user in plain words."""


# --------------------------------------------------------------------------- what's installed

def _find_in(folder):
    names = ("sd-cli.exe",) if sys.platform == "win32" else ("sd-cli",)
    for root, _, files in os.walk(folder):
        for n in names:
            if n in files:
                return os.path.join(root, n)
    return None


def using_cpu():
    """True once the graphics chip has failed and we switched to the processor-only program."""
    if sys.platform != "win32":
        return False  # only Windows has a separate processor-only program; Macs use their own chip
    try:
        with open(CPU_MARK, encoding="utf-8") as f:
            wanted = f.read().startswith("The graphics")  # a file that says "off" turns this back off
    except OSError:
        return False
    return wanted and bool(_find_in(SD_CPU_DIR))


def find_sd_cli():
    if using_cpu():
        return _find_in(SD_CPU_DIR)
    return _find_in(SD_DIR)


def mode_note():
    return " (using your computer's processor because the graphics chip ran out of memory)" if using_cpu() else ""


def model_path(name):
    return os.path.join(MODEL_DIR, name)


def ai_ready():
    return bool(find_sd_cli()) and all(os.path.exists(model_path(m["file"])) for m in MODELS)


# --------------------------------------------------------------------------- downloading

def _open(url, headers=None, timeout=60):
    h = {"User-Agent": "ShortsMaker/1.0"}
    h.update(headers or {})
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout)


def _size(n):
    return f"{n / 1e9:.1f} GB" if n >= 1e9 else f"{n / 1e6:.0f} MB"


def _download(url, dest, on_progress):
    """Download with resume: if it stops half way, run it again and it carries on."""
    part = dest + ".part"
    have = os.path.getsize(part) if os.path.exists(part) else 0
    try:
        try:
            r = _open(url, {"Range": f"bytes={have}-"} if have else None)
        except urllib.error.HTTPError as err:
            if err.code == 416 and have:  # we already have all of it
                os.replace(part, dest)
                return
            raise
        with r:
            resumed = have > 0 and getattr(r, "status", 200) == 206
            if have and not resumed:
                have = 0
            total = int(r.headers.get("Content-Length") or 0) + have or None
            done, last = have, 0.0
            with open(part, "ab" if resumed else "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if time.time() - last > 1:
                        on_progress(done, total)
                        last = time.time()
            on_progress(done, total)
    except OSError as err:
        raise AIError("The download stopped (check your internet connection). "
                      f"Click the button again and it will continue where it left off. Details: {err}") from err
    os.replace(part, dest)


def _asset_pattern(cpu=False):
    if cpu:
        if sys.platform == "win32":
            return r"bin-win-cpu-x64\.zip$"
        return r"bin-Linux-Ubuntu-[\d.]+-x86_64\.zip$"
    if sys.platform == "win32":
        return r"bin-win-vulkan-x64\.zip$"
    if sys.platform == "darwin":
        return r"bin-Darwin-.*arm64\.zip$"
    return r"bin-Linux-Ubuntu-.*x86_64-vulkan\.zip$"


def check_supported():
    """Intel Macs have no usable build of the picture program and too little graphics memory."""
    import platform
    if sys.platform == "darwin" and platform.machine() == "x86_64":
        raise AIError("AI pictures can't run on this Mac (it has an Intel chip, and the picture program only supports "
                      "Apple-chip Macs or Windows). Choose 'Stock footage' for pictures here, and make AI-picture "
                      "videos on your Windows gaming PC.")


def _find_program_url(cpu=False):
    check_supported()
    try:
        with _open(SD_RELEASE_API) as r:
            release = json.loads(r.read())
    except (OSError, ValueError) as err:
        raise AIError(f"Couldn't look up the image program on GitHub. Check your internet connection. ({err})")
    for asset in release.get("assets", []):
        if re.search(_asset_pattern(cpu), asset.get("name", "")):
            return asset["browser_download_url"]
    raise AIError("Couldn't find the right image program download for this computer in the latest release.")


def switch_to_cpu():
    """Download the processor-only image program (small) and use it from now on."""
    if not _find_in(SD_CPU_DIR):
        os.makedirs(SD_CPU_DIR, exist_ok=True)
        zip_path = os.path.join(AI_DIR, "program-cpu.zip")
        _download(_find_program_url(cpu=True), zip_path, lambda d, t: None)
        try:
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(SD_CPU_DIR)
        except zipfile.BadZipFile:
            os.remove(zip_path)
            raise AIError("The processor-only program download was damaged. Please try again.")
        os.remove(zip_path)
        exe = _find_in(SD_CPU_DIR)
        if not exe:
            raise AIError("The processor-only download didn't contain the image program.")
        if sys.platform != "win32":
            os.chmod(exe, 0o755)
    with open(CPU_MARK, "w", encoding="utf-8") as f:
        f.write("The graphics chip ran out of memory, so pictures are made with the processor. Replace the text with the word off to try the graphics chip again.\n")


GPU_MEMORY_PROBLEM = re.compile(
    r"alloc.*buffer failed|failed during weight preparation|out of memory|vk::|vulkan.*(error|fail)|"
    r"ErrorOutOfDeviceMemory|device lost", re.I)


def _pick_model_file(spec):
    if spec.get("exact"):
        return spec["exact"]
    try:
        with _open(f"{HF}/api/models/{spec['repo']}") as r:
            names = [s["rfilename"] for s in json.loads(r.read()).get("siblings", [])]
    except (OSError, ValueError, KeyError) as err:
        raise AIError(f"Couldn't look up {spec['label']} on Hugging Face. Check your internet connection. ({err})")
    names = [n for n in names if n.lower().endswith(spec["ext"]) and "mmproj" not in n.lower()]
    for token in spec["prefer"]:
        for n in names:
            if token.lower() in n.lower():
                return n
    if names:
        return names[0]
    raise AIError(f"Couldn't find {spec['label']} in its Hugging Face download page.")


def setup_ai(progress):
    """One-time download of the image program and models. progress(percent, message)."""
    os.makedirs(SD_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)

    if not find_sd_cli():
        progress(1, "Finding the image program...")
        url = _find_program_url()
        zip_path = os.path.join(AI_DIR, "program.zip")
        _download(url, zip_path, lambda d, t: progress(2, f"Downloading the image program... {_size(d)}"))
        progress(5, "Unpacking the image program...")
        try:
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(SD_DIR)
        except zipfile.BadZipFile:
            os.remove(zip_path)
            raise AIError("The program download was damaged. Please click the button to try again.")
        os.remove(zip_path)
        exe = find_sd_cli()
        if not exe:
            raise AIError("The download didn't contain the image program. Please tell Claude about this.")
        if sys.platform != "win32":
            os.chmod(exe, 0o755)

    for spec in MODELS:
        dest = model_path(spec["file"])
        lo, hi = spec["band"]
        if os.path.exists(dest):
            progress(hi, f"Already have {spec['label']}.")
            continue
        progress(lo, f"Looking up {spec['label']}...")

        def on_progress(done, total, lo=lo, hi=hi, label=spec["label"]):
            pct = lo + (hi - lo) * (done / total if total else 0)
            progress(int(pct), f"Downloading {label}... {_size(done)}" + (f" of {_size(total)}" if total else ""))

        if spec.get("sources"):
            last_err = None
            for repo, name in spec["sources"]:
                try:
                    _download(f"{HF}/{repo}/resolve/main/{name}", dest, on_progress)
                    last_err = None
                    break
                except AIError as err:
                    code = getattr(err.__cause__, "code", None)
                    if code not in (401, 403, 404):  # a real network problem: stop and say so
                        raise
                    last_err = err
            if last_err:
                raise AIError(f"None of the download sites would give out {spec['label']} "
                              "(they asked for a login). Please tell Claude about this.")
        else:
            name = _pick_model_file(spec)
            _download(f"{HF}/{spec['repo']}/resolve/main/{name}", dest, on_progress)
    progress(100, "AI images are ready!")


# --------------------------------------------------------------------------- making pictures

def _run(cmd, cwd, progress):
    start = time.time()
    try:
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, errors="replace")
    except OSError as err:
        raise AIError("The image program can't run on this computer (it was probably copied from a different kind of "
                      "computer). Delete the folders ai/sd and ai/sd-cpu and the file ai/use_cpu.txt, then try again "
                      f"and the right one will download. Details: {err}")
    while True:
        try:
            out, err = proc.communicate(timeout=PROGRESS_EVERY)
            return proc.returncode, (out or "") + (err or "")
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            if elapsed > GENERATE_TIMEOUT:
                proc.kill()
                proc.communicate()
                raise AIError("The picture was taking far too long, so I stopped it.")
            if progress:
                progress(int(elapsed))


# ---- remembering pictures, so re-making a video only repaints what changed
CACHE_DIR = os.path.join(AI_DIR, "cache")
CACHE_KEEP = 300  # how many pictures to remember


def _cache_file(prompt, quality):
    width, height = SIZES.get(quality, SIZES["standard"])
    key = hashlib.sha1(f"{prompt}|{width}x{height}".encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, key + ".png")


def _remember(prompt, quality, src):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        shutil.copyfile(src, _cache_file(prompt, quality))
        files = sorted((os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR)), key=os.path.getmtime)
        for old in files[:-CACHE_KEEP]:
            os.remove(old)
    except OSError:
        pass  # remembering is a bonus; never let it break a video


def _command(exe, prompt, out_path, width, height, seed, cpu):
    base = [exe, "--diffusion-model", model_path("zimage.gguf"), "--vae", model_path("ae.safetensors"),
            "--llm", model_path("qwen3.gguf"), "-p", prompt, "--cfg-scale", "1.0", "--steps", "8",
            "-H", str(height), "-W", str(width), "-o", out_path, "--diffusion-fa"]
    if not cpu:
        base.append("--offload-to-cpu")  # keeps most of the model in normal memory, helps small graphics chips
    return base, ["--vae-tiling", "-s", str(seed)]


def generate_image(prompt, out_path, quality="standard", seed=None, progress=None, use_cache=True):
    """Paint one AI picture into out_path (a .png). progress(seconds_so_far) is called while waiting.
    Returns True if an earlier picture for the very same prompt was reused instead of painting a new one."""
    check_supported()
    if not find_sd_cli() or not ai_ready():
        raise AIError("AI images aren't set up yet.")
    cached = _cache_file(prompt, quality)
    if use_cache and os.path.exists(cached):
        try:
            shutil.copyfile(cached, out_path)
            os.utime(cached, None)
            return True
        except OSError:
            pass
    width, height = SIZES.get(quality, SIZES["standard"])
    seed = random.randint(1, 2 ** 31 - 1) if seed is None else seed

    def attempt():
        exe = find_sd_cli()
        base, extras = _command(exe, prompt, out_path, width, height, seed, using_cpu())
        cwd = os.path.dirname(exe)
        code, log = _run(base + extras, cwd, progress)
        if code != 0 and re.search(r"unknown|unrecogni[sz]ed|invalid (argument|option)", log, re.I):
            code, log = _run(base, cwd, progress)  # try again with only the essential settings
        return code, log, base + extras

    code, log, cmd = attempt()
    if (code != 0 or not os.path.exists(out_path)) and sys.platform == "win32" and not using_cpu() \
            and GPU_MEMORY_PROBLEM.search(log):
        switch_to_cpu()  # the graphics chip can't hold the model: use the processor instead
        code, log, cmd = attempt()
    if code != 0 or not os.path.exists(out_path):
        try:  # keep the whole report so it can be sent to Claude
            with open(os.path.join(AI_DIR, "last_error.log"), "w", encoding="utf-8") as f:
                f.write(f"exit code: {code}\ncommand: {' '.join(cmd)}\n\n{log}")
        except OSError:
            pass
        lines = [l.strip() for l in log.strip().splitlines() if l.strip()]
        raise AIError(f"The image program stopped (code {code}). Last lines of its report: "
                      + " | ".join(lines[-6:])[:700] + "  (Full report saved as ai\\last_error.log)")
    _remember(prompt, quality, out_path)
    return False
