"""Keeps Shorts Maker up to date: on start, fetches the newest code from GitHub and replaces the program files.
Your videos, settings and AI models are never touched. It stays quiet and harmless if there's no internet."""
import io
import json
import os
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_FILE = os.path.join(HERE, "update_source.txt")   # contains: owner/repo   (optional :branch)
VERSION_FILE = os.path.join(HERE, ".version")
KEEP = {"update_source.txt"}                             # never overwritten
ALLOWED = (".py", ".md", ".txt", ".bat", ".command", ".gitignore")


def _get(url, timeout=20):
    try:
        import truststore
        truststore.inject_into_ssl()
    except Exception:
        pass
    req = urllib.request.Request(url, headers={"User-Agent": "ShortsMaker-updater"})
    return urllib.request.urlopen(req, timeout=timeout).read()


def main():
    try:
        spec = open(SOURCE_FILE, encoding="utf-8").read().strip()
    except OSError:
        return
    if not spec or "/" not in spec:
        return
    repo, _, branch = spec.partition(":")
    branch = branch or "main"
    try:
        sha = json.loads(_get(f"https://api.github.com/repos/{repo}/commits/{branch}", 10))["sha"]
    except Exception:
        print("(Couldn't check for updates, carrying on with the current version.)")
        return
    try:
        have = open(VERSION_FILE, encoding="utf-8").read().strip()
    except OSError:
        have = ""
    if have == sha:
        print("Shorts Maker is up to date.")
        return
    try:
        data = _get(f"https://codeload.github.com/{repo}/zip/{sha}", 60)
        z = zipfile.ZipFile(io.BytesIO(data))
        changed = 0
        for info in z.infolist():
            parts = info.filename.split("/", 1)
            if info.is_dir() or len(parts) < 2:
                continue
            name = parts[1]
            if "/" in name:   # only the tests/ and docs/ folders, one level deep
                folder, _, base = name.partition("/")
                if folder not in ("tests", "docs") or "/" in base or not base.endswith((".py", ".md")):
                    continue
                os.makedirs(os.path.join(HERE, folder), exist_ok=True)
            if name in KEEP or not (name.endswith(ALLOWED) or name in ("LICENSE",)):
                continue
            dest = os.path.join(HERE, name)
            new = z.read(info)
            try:
                if open(dest, "rb").read() == new:
                    continue
            except OSError:
                pass
            with open(dest, "wb") as f:
                f.write(new)
            if name.endswith(".command") and sys.platform != "win32":
                os.chmod(dest, 0o755)
            changed += 1
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(sha)
        print(f"Updated Shorts Maker ({changed} file(s) changed).")
    except Exception as err:
        print(f"(Update didn't finish: {err}. Carrying on with the current version.)")


if __name__ == "__main__":
    main()
