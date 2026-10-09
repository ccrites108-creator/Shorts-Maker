"""
Shorts Maker - storytelling tools.

Plain data and small helpers that shape *how* a video tells its story: story formats (the beats a script
follows), narrator tones, ways to end a video, a "story bible" for consistent pictures, and multi-part series.
Nothing in here talks to the network, so it is easy to test and to extend.

To add your own story format, add an entry to STORY_FORMATS below. See CONTRIBUTING.md.

License: MIT (see LICENSE)
"""

import json
import os
import re
import time
import uuid

# --------------------------------------------------------------------------- story formats

STORY_FORMATS = {
    "explainer": {
        "name": "Fact explainer",
        "tagline": "Clear, surprising facts",
        "beats": ["Hook", "Context", "Key facts", "Surprise", "Takeaway"],
        "guide": "Open with the most surprising fact. Explain it simply, build to one detail that changes how "
                 "the viewer sees it, and end on the takeaway.",
    },
    "mystery": {
        "name": "Mystery",
        "tagline": "A puzzle with a twist",
        "beats": ["Hook", "Setup", "Clues", "Twist", "Open question"],
        "guide": "Start with the strange thing that cannot be explained. Lay out the clues one by one, "
                 "land a twist, and finish with the question that still has no answer.",
    },
    "countdown": {
        "name": "Countdown",
        "tagline": "Top 3 or Top 5, best last",
        "beats": ["Hook", "Number 3", "Number 2", "Number 1", "Wrap up"],
        "guide": "Promise a countdown in the first line. Give each item its own scene, with the most "
                 "amazing one last. Say the number at the start of each item.",
    },
    "whatif": {
        "name": "What if...",
        "tagline": "Imagine a big change",
        "beats": ["Hook", "How it is now", "The change", "Consequences", "Final thought"],
        "guide": "Pose the 'what if' as the hook. Describe normal life, then the change, then escalate "
                 "the consequences one step at a time until the final unsettling thought.",
    },
    "myth": {
        "name": "Myth vs truth",
        "tagline": "Bust a popular belief",
        "beats": ["Hook", "The myth", "Why people believe it", "The truth", "Proof"],
        "guide": "State what everyone believes, explain why it feels true, then reveal what is really "
                 "going on with one convincing piece of evidence.",
    },
    "legend": {
        "name": "Legend",
        "tagline": "A story told like a tale",
        "beats": ["Hook", "Once upon a time", "Rising trouble", "Climax", "Aftermath"],
        "guide": "Tell it as a story with a person or an object at the center. Give it a beginning, "
                 "trouble that grows, one decisive moment, and what was left behind.",
    },
    "journey": {
        "name": "Journey",
        "tagline": "Travel through time or space",
        "beats": ["Hook", "Departure", "First stop", "Farther out", "Destination"],
        "guide": "Take the viewer on a trip. Each scene is a new stop that is bigger, older or stranger "
                 "than the last, ending at the most mind-bending place.",
    },
}

DEFAULT_FORMAT = "explainer"

# --------------------------------------------------------------------------- narrator tones
# (display name, how to write it, speaking speed for the voice)

TONES = {
    "documentary": ("Documentary", "calm, authoritative documentary narrator who sounds sure of every fact", "+0%"),
    "mysterious": ("Mysterious", "hushed, mysterious storyteller who lets pauses and short sentences build tension", "-6%"),
    "energetic": ("Energetic", "fast, excited host who makes everything sound amazing, with punchy sentences", "+8%"),
    "dramatic": ("Dramatic", "dramatic trailer voice with big, vivid words and a strong sense of stakes", "-4%"),
    "friendly": ("Friendly", "warm, curious friend explaining something cool over coffee", "+3%"),
    "playful": ("Playful", "witty, lightly funny narrator who is never mean", "+5%"),
}

DEFAULT_TONE = "documentary"

# --------------------------------------------------------------------------- how a video ends

ENDINGS = {
    "follow": ("Invite to follow", "The last scene warmly invites viewers to follow for more videos like this."),
    "cliffhanger": ("Cliffhanger", "End on a cliffhanger: hint at something bigger that comes next and leave it "
                                    "unanswered. Tell viewers to follow so they do not miss it."),
    "loop": ("Seamless loop", "Write the very last sentence so it flows straight back into the first sentence, "
                              "so the video feels endless when it replays. Do not say goodbye."),
    "question": ("Ask a question", "End by asking viewers one fun, specific question that makes them want to "
                                    "answer in the comments."),
}

DEFAULT_ENDING = "follow"

# --------------------------------------------------------------------------- cleaning up what the page sends


def _pick(value, allowed, default):
    return value if value in allowed else default


def normalize(raw):
    """Turn whatever the page sent into a safe story dict (or None for 'no special story')."""
    if not isinstance(raw, dict):
        return None
    story = {
        "format": _pick(raw.get("format"), STORY_FORMATS, DEFAULT_FORMAT),
        "tone": _pick(raw.get("tone"), TONES, DEFAULT_TONE),
        "ending": _pick(raw.get("ending"), ENDINGS, DEFAULT_ENDING),
        "bible": " ".join(str(raw.get("bible") or "").split())[:400],
    }
    try:
        part, parts = int(raw.get("part") or 0), int(raw.get("parts") or 0)
    except (TypeError, ValueError):
        part = parts = 0
    if 1 <= part <= parts <= 12:
        story.update(part=part, parts=parts,
                     series_title=" ".join(str(raw.get("series_title") or "").split())[:80],
                     prev=" ".join(str(raw.get("prev") or "").split())[:300],
                     next=" ".join(str(raw.get("next") or "").split())[:300],
                     series_id=str(raw.get("series_id") or "")[:16])
    return story


def beats_for(story):
    return STORY_FORMATS[(story or {}).get("format") or DEFAULT_FORMAT]["beats"]


def speech_rate(story):
    return TONES[(story or {}).get("tone") or DEFAULT_TONE][2]


def ending_rule(story):
    return ENDINGS[(story or {}).get("ending") or DEFAULT_ENDING][1]


def story_block(story):
    """The extra instructions that go into the script prompt."""
    if not story:
        return ""
    fmt = STORY_FORMATS[story["format"]]
    lines = [
        f"Story format: {fmt['name']}. {fmt['guide']}",
        "Build the script around these story beats, in this order: " + " > ".join(fmt["beats"]) +
        ". A beat may take two scenes but never skip one, and each scene's \"beat\" field names the beat it belongs to.",
        "Narrator voice: " + TONES[story["tone"]][1] + ". Write every line so it sounds like that when read aloud.",
    ]
    if story.get("bible"):
        lines.append("Story world and recurring look (work this into every image_prompt so the pictures feel like one "
                     "story): " + story["bible"])
    if story.get("part"):
        n, total = story["part"], story["parts"]
        lines.append(f"This video is part {n} of {total} of the series \"{story.get('series_title') or 'this series'}\".")
        if story.get("prev"):
            lines.append(f"The previous part covered: {story['prev']} Start with one short line that recaps it, then hook the viewer.")
        if story.get("next"):
            lines.append(f"The next part will cover: {story['next']} Tease it in the final line without giving it away.")
        elif n == total:
            lines.append("This is the final part, so resolve the story with a satisfying ending.")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- series (multi-part stories)


def series_path(settings_dir):
    return os.path.join(settings_dir, "series.json")


def load_series(settings_dir):
    try:
        with open(series_path(settings_dir), encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("series", [])
        return items if isinstance(items, list) else []
    except (OSError, ValueError, AttributeError):
        return []


def save_series(settings_dir, items):
    os.makedirs(settings_dir, exist_ok=True)
    tmp = series_path(settings_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"series": items}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, series_path(settings_dir))


def clean_series(raw):
    """Check a series from the model or the page and tidy it. Raises ValueError if it can't be used."""
    if not isinstance(raw, dict):
        raise ValueError("the series isn't in the right shape")
    parts_raw = raw.get("parts")
    if not isinstance(parts_raw, list):
        raise ValueError("no list of parts")
    parts = []
    for p in parts_raw[:12]:
        if isinstance(p, str):
            p = {"idea": p}
        if not isinstance(p, dict):
            continue
        idea = " ".join(str(p.get("idea") or p.get("summary") or p.get("description") or "").split())
        title = " ".join(str(p.get("title") or "").split())
        if not (idea or title):
            continue
        parts.append({"title": (title or idea)[:90], "idea": (idea or title)[:300],
                      "teaser": " ".join(str(p.get("teaser") or p.get("cliffhanger") or "").split())[:200],
                      "video": p.get("video") if isinstance(p.get("video"), str) else None})
    if len(parts) < 2:
        raise ValueError("a series needs at least two parts")
    return {"id": str(raw.get("id") or uuid.uuid4().hex[:8]),
            "title": " ".join(str(raw.get("title") or "My series").split())[:80] or "My series",
            "topic": " ".join(str(raw.get("topic") or "").split())[:300],
            "format": _pick(raw.get("format"), STORY_FORMATS, DEFAULT_FORMAT),
            "tone": _pick(raw.get("tone"), TONES, DEFAULT_TONE),
            "ending": _pick(raw.get("ending"), ENDINGS, "cliffhanger"),
            "bible": " ".join(str(raw.get("bible") or "").split())[:400],
            "created": raw.get("created") or time.time(),
            "parts": parts}


def fallback_series(topic, parts, fmt, tone):
    """Used when the model can't plan a series: simple, honest placeholders the person can edit."""
    topic = " ".join(topic.split())[:120]
    plan = [{"title": f"{topic}: part {n}", "idea": f"{topic} (part {n} of {parts})", "teaser": ""}
            for n in range(1, parts + 1)]
    return clean_series({"title": topic[:60], "topic": topic, "format": fmt, "tone": tone, "parts": plan})


def story_for_part(series, index):
    """The story settings for making part `index` (0-based) of a series."""
    parts = series["parts"]
    prev = parts[index - 1]["idea"] if index > 0 else ""
    nxt = parts[index + 1]["idea"] if index + 1 < len(parts) else ""
    return {"format": series["format"], "tone": series["tone"],
            "ending": "cliffhanger" if index + 1 < len(parts) else "follow",
            "bible": series.get("bible", ""), "part": index + 1, "parts": len(parts),
            "series_title": series["title"], "prev": prev, "next": nxt, "series_id": series["id"]}


def mark_part_done(settings_dir, series_id, index, video_name):
    items = load_series(settings_dir)
    for s in items:
        if s.get("id") == series_id and 0 <= index < len(s.get("parts", [])):
            s["parts"][index]["video"] = video_name
            save_series(settings_dir, items)
            return True
    return False


def slug_ok(value):
    return bool(re.fullmatch(r"[0-9a-f]{8}", value or ""))
