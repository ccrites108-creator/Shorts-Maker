"""Offline tests: no network, no Ollama. Run with:  python -m unittest discover tests"""
import os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SHORTS_SETTINGS_DIR", tempfile.mkdtemp())

import story  # noqa: E402
import shorts_maker as sm  # noqa: E402


class StoryTests(unittest.TestCase):
    def test_normalize_defaults(self):
        s = story.normalize({"format": "nope", "tone": "x", "ending": "y"})
        self.assertEqual((s["format"], s["tone"], s["ending"]),
                         (story.DEFAULT_FORMAT, story.DEFAULT_TONE, story.DEFAULT_ENDING))
        self.assertIsNone(story.normalize("junk"))

    def test_every_format_has_beats_and_block(self):
        for key, fmt in story.STORY_FORMATS.items():
            self.assertGreaterEqual(len(fmt["beats"]), 4, key)
            block = story.story_block(story.normalize({"format": key}))
            self.assertIn(fmt["name"], block)

    def test_series_clean_and_parts(self):
        s = story.fallback_series("Ancient Egypt", 4, "mystery", "dramatic")
        self.assertEqual(len(s["parts"]), 4)
        first, last = story.story_for_part(s, 0), story.story_for_part(s, 3)
        self.assertEqual(first["ending"], "cliffhanger")
        self.assertEqual(last["ending"], "follow")
        self.assertEqual(last["part"], 4)
        with self.assertRaises(ValueError):
            story.clean_series({"parts": [{"idea": "only one"}]})

    def test_series_roundtrip(self):
        d = tempfile.mkdtemp()
        s = story.fallback_series("Space", 3, "journey", "friendly")
        story.save_series(d, [s])
        self.assertTrue(story.mark_part_done(d, s["id"], 1, "a.mp4"))
        self.assertEqual(story.load_series(d)[0]["parts"][1]["video"], "a.mp4")

    def test_speech_rate(self):
        self.assertEqual(story.speech_rate({"tone": "energetic"}), "+8%")


class ScriptTests(unittest.TestCase):
    def test_clamp_seconds(self):
        self.assertEqual(sm.clamp_seconds(5), 30)
        self.assertEqual(sm.clamp_seconds(500), 90)

    def test_clean_script_keeps_beat(self):
        raw = {"title": "T", "description": "D", "scenes": [
            {"narration": "One.", "beat": "Hook", "visual_query": "a", "image_prompt": "p"},
            {"narration": "Two.", "beat": "Twist", "visual_query": "b", "image_prompt": "q"}]}
        script = sm.clean_script(raw)
        self.assertEqual(script["scenes"][1]["beat"], "Twist")


if __name__ == "__main__":
    unittest.main()
