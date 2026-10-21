"""
Shorts Maker - character episodes.

One main character, a new self-contained adventure in every video. This file keeps:
  - the character profile (look, personality, world, sidekicks, narrator voice, success sound),
  - the episode log (which adventures were already made, so new ones don't repeat and get the next number),
  - the little "bip-bip" success sound that plays when the character wins.

The default character is Pip, a palm-sized robot in a giant human house. Change everything on the
Episodes tab (or in ~/.shorts-maker/character.json) to star someone else.
Nothing in here talks to the network, so it is easy to test.

License: MIT (see LICENSE)
"""

import json
import math
import os
import struct
import time
import uuid
import wave

# --------------------------------------------------------------------------- the default character (Pip)

DEFAULT_CHARACTER = {
    "name": "Pip",
    "pronoun": "he",
    "look": ("Pip, a tiny palm-sized robot, round slightly dented mint-green tin body, single orange rivet on chest, "
             "dome head with one large round glowing cyan eye-screen, short bendy arms with two-finger grippers, "
             "small tank-tread feet, carrying a red thumbtack like a sword"),
    "art_style": ("soft 3D animated film style, warm cinematic lighting, shallow depth of field, low camera angle "
                  "at Pip's eye level, giant everyday household objects around him"),
    "personality": "brave, curious, never gives up, a bit clumsy, gets startled easily, celebrates every small win",
    "world": ("A giant human house where every room is an unexplored world: the kitchen counter, the bookshelf "
              "mountains, the dark under-the-couch cave and the bathtub sea. Pip is about 8 cm tall."),
    "sidekicks": "Mittens the cat, the big scary 'monster' who is secretly gentle.",
    "speaks": False,                 # False: the character only makes sounds, a narrator tells the story
    "success_sound": "bip-bip!",     # shown as a caption when the sound plays
    "sound_file": "",                # optional: your own .wav/.mp3 to use instead of the built-in bip-bip
    "voice": "en-US-AndrewNeural",   # the narrator; the same voice every episode
    "seconds": 35,
    "seed": 8817,                    # the same seed every picture helps the character look alike
    "ideas": [
        "The Crumb Summit: Pip climbs the table leg to reach a cookie crumb, then rides a falling napkin down like a parachute",
        "Sock Rescue: Pip pulls a lost sock out from under the couch, using a dangling phone charger as a rope swing",
        "The Bathtub Sea: Pip crosses the full tub to fetch a rubber duck, sailing in a bottle cap with a tissue sail",
        "Mittens Attacks: Pip escapes the cat on the kitchen floor by turning his eye into a laser dot",
        "Power Low: Pip races to the charger before his battery dies, and a toy car gives him the final ride",
        "Midnight Snack Heist: Pip steals one blueberry from the fridge, wedging the door open with a fridge magnet",
        "Bookshelf Mountain: Pip reaches the top shelf to see the sunrise by building a staircase out of dominoes",
        "Rainy Window: Pip saves a bug stuck on the windowsill and turns a leaf into an umbrella for both of them",
        "Vacuum Monster: Pip survives cleaning day by hiding inside a shoe and riding out the storm",
        "Birthday Surprise: Pip delivers a candle to the owner's cake and lights the way with his eye",
    ],
}

LIMITS = {"name": 40, "pronoun": 10, "look": 700, "art_style": 400, "personality": 300, "world": 500,
          "sidekicks": 300, "success_sound": 30, "sound_file": 400, "voice": 60}

# The beats every episode follows, so viewers know what to expect (and the story always flows the same way).
EPISODE_BEATS = ["Hook", "Goal", "Attempt and fail", "Clever twist", "Payoff"]


def _line(value, limit):
    return " ".join(str(value or "").split())[:limit]


def clean_character(raw):
    """Tidy a character from the page or the file. Missing fields fall back to Pip's."""
    raw = raw if isinstance(raw, dict) else {}
    ch = {}
    for key, limit in LIMITS.items():
        value = _line(raw.get(key), limit)
        ch[key] = value if value or key == "sound_file" else DEFAULT_CHARACTER[key]
    ch["speaks"] = bool(raw.get("speaks", DEFAULT_CHARACTER["speaks"]))
    try:
        ch["seconds"] = max(30, min(90, int(raw.get("seconds") or DEFAULT_CHARACTER["seconds"])))
    except (TypeError, ValueError):
        ch["seconds"] = DEFAULT_CHARACTER["seconds"]
    try:
        ch["seed"] = max(1, min(2 ** 31 - 1, int(raw.get("seed") or DEFAULT_CHARACTER["seed"])))
    except (TypeError, ValueError):
        ch["seed"] = DEFAULT_CHARACTER["seed"]
    ideas = raw.get("ideas")
    if isinstance(ideas, str):
        ideas = ideas.splitlines()
    if not isinstance(ideas, list):
        ideas = DEFAULT_CHARACTER["ideas"]
    ch["ideas"] = [i for i in (_line(x, 300) for x in ideas) if i][:50]
    return ch


def character_path(settings_dir):
    return os.path.join(settings_dir, "character.json")


def load_character(settings_dir):
    try:
        with open(character_path(settings_dir), encoding="utf-8") as f:
            return clean_character(json.load(f))
    except (OSError, ValueError):
        return clean_character(DEFAULT_CHARACTER)


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def save_character(settings_dir, raw):
    ch = clean_character(raw)
    _save(character_path(settings_dir), ch)
    return ch


# --------------------------------------------------------------------------- the episode log

def log_path(settings_dir):
    return os.path.join(settings_dir, "episodes.json")


def load_episodes(settings_dir):
    try:
        with open(log_path(settings_dir), encoding="utf-8") as f:
            items = json.load(f).get("episodes", [])
        return [e for e in items if isinstance(e, dict)] if isinstance(items, list) else []
    except (OSError, ValueError, AttributeError):
        return []


def save_episodes(settings_dir, items):
    _save(log_path(settings_dir), {"episodes": items})


def next_number(settings_dir):
    return max([int(e.get("number") or 0) for e in load_episodes(settings_dir)] + [0]) + 1


def unused_ideas(character, episodes):
    """Ideas from the character's list that haven't been made yet, in order."""
    done = {_line(e.get("idea"), 300).lower() for e in episodes}
    return [i for i in character["ideas"] if i.lower() not in done]


def record_episode(settings_dir, story, title, video_name):
    """Remember a finished episode (a remake of the same number replaces the old entry)."""
    items = [e for e in load_episodes(settings_dir) if e.get("number") != story["episode"]]
    items.append({"id": story.get("episode_id") or uuid.uuid4().hex[:8], "number": story["episode"],
                  "idea": story.get("idea", ""), "title": title, "video": video_name,
                  "character": story["character"]["name"], "made": time.time()})
    items.sort(key=lambda e: e.get("number") or 0)
    save_episodes(settings_dir, items)


def delete_episode(settings_dir, number):
    save_episodes(settings_dir, [e for e in load_episodes(settings_dir) if e.get("number") != number])


def story_for_episode(character, idea, number, episodes, tone="storybook"):
    """The story settings for making one episode. Earlier episodes are listed so the new one doesn't repeat them."""
    past = [f"Ep {e.get('number')}: {_line(e.get('title') or e.get('idea'), 90)}"
            for e in episodes if e.get("number") != number][-12:]
    return {"format": "episode", "tone": tone, "ending": "loop", "bible": "",
            "character": character, "episode": number, "idea": _line(idea, 300),
            "past": past, "episode_id": uuid.uuid4().hex[:8]}


def character_block(story):
    """The extra instructions that go into the script prompt for an episode."""
    ch = story["character"]
    name, he = ch["name"], ch.get("pronoun") or "they"
    lines = [
        f"This is episode {story['episode']} of an ongoing series. The star of every episode is {name}.",
        f"Who {name} is: {ch['look']}. Personality: {ch['personality']}.",
        f"The world: {ch['world']}",
    ]
    if ch.get("sidekicks"):
        lines.append(f"Recurring characters who may appear (only if they fit this adventure): {ch['sidekicks']}")
    if ch.get("speaks"):
        lines.append(f"{name} may say a few short words in quotes, but a narrator tells most of the story.")
    else:
        lines.append(f"{name} never speaks words. A narrator tells the adventure in the third person, present tense, "
                     f"and calls {name} by name and '{he}'.")
    lines += [
        "This episode is ONE complete, self-contained adventure: a viewer who has never seen another episode must "
        "understand it, and it must end with the problem solved.",
        "Make it flow like one continuous story, not a list: every scene follows directly from the one before "
        "(use links like 'but', 'so', 'then', 'just as'), stays in the same place with the same props unless "
        f"{name} moves on, and no scene jumps to a new topic. No facts, no lessons, no talking to the viewer.",
        f"Every image_prompt shows {name} (call {name} by name) doing exactly what that scene's narration says, "
        "in this episode's setting, seen from a low angle so the world looks gigantic.",
        f"The moment {name} succeeds, put \"sfx\": \"success\" on that scene. {name}'s happy sound "
        f"(\"{ch['success_sound']}\") plays right after that scene's narration, so end the narration just before it "
        "and do not write the sound in the narration. Use \"sfx\": \"success\" on one scene, or two at most.",
    ]
    if story.get("past"):
        lines.append("Earlier episodes (make this one a different adventure): " + "; ".join(story["past"]) + ".")
    return "\n".join(lines) + "\n"


def picture_notes(story):
    """What is added to every AI picture prompt for an episode: the character's exact look and the art style."""
    ch = story["character"]
    return f"{ch['look']}. {ch['art_style']}"


# --------------------------------------------------------------------------- the success sound

def make_success_sound(path, rate=44100):
    """A cheerful two-note robot 'bip-bip!' as a short wav file."""
    n = int(rate * 0.55)
    buf = [0.0] * n

    def bip(t0, f0, f1, length=0.11):
        i0 = int(t0 * rate)
        for i in range(int(length * rate)):
            t = i / rate
            freq = f0 + (f1 - f0) * t / length
            env = min(1.0, t / 0.006) * math.exp(-t * 9)
            square = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
            buf[i0 + i] += env * (0.22 * square + 0.30 * math.sin(2 * math.pi * freq * t)
                                  + 0.10 * math.sin(4 * math.pi * freq * t))

    bip(0.02, 1250, 1450)
    bip(0.19, 1650, 2050, 0.14)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 30000)) for v in buf))
    return path
