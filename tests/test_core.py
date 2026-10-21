"""Offline tests: no network, no Ollama. Run with:  python -m unittest discover tests"""
import os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SHORTS_SETTINGS_DIR", tempfile.mkdtemp())

import episodes  # noqa: E402
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


class EpisodeTests(unittest.TestCase):
    def test_default_character_is_pip(self):
        ch = episodes.clean_character(None)
        self.assertEqual(ch["name"], "Pip")
        self.assertIn("mint-green", ch["look"])
        self.assertEqual(len(ch["ideas"]), 10)

    def test_character_roundtrip_and_fallbacks(self):
        d = tempfile.mkdtemp()
        self.assertEqual(episodes.load_character(d)["name"], "Pip")
        saved = episodes.save_character(d, {"name": "Moss", "look": "a glowing forest spirit", "ideas": "One\n\nTwo",
                                            "seconds": 500})
        self.assertEqual(saved["ideas"], ["One", "Two"])
        self.assertEqual(saved["seconds"], 90)
        self.assertEqual(saved["personality"], episodes.DEFAULT_CHARACTER["personality"])
        self.assertEqual(episodes.load_character(d)["name"], "Moss")

    def test_episode_log_numbers_and_unused_ideas(self):
        d = tempfile.mkdtemp()
        ch = episodes.load_character(d)
        self.assertEqual(episodes.next_number(d), 1)
        st = story.normalize(episodes.story_for_episode(ch, ch["ideas"][0], 1, []))
        episodes.record_episode(d, st, "Crumb | Ep 1 #shorts", "a.mp4")
        self.assertEqual(episodes.next_number(d), 2)
        self.assertEqual(episodes.unused_ideas(ch, episodes.load_episodes(d))[0], ch["ideas"][1])
        episodes.record_episode(d, st, "Crumb again", "b.mp4")  # a remake replaces the entry
        self.assertEqual(len(episodes.load_episodes(d)), 1)
        st2 = episodes.story_for_episode(ch, "new idea", 2, episodes.load_episodes(d))
        self.assertIn("Ep 1", st2["past"][0])

    def test_episode_story_block(self):
        ch = episodes.clean_character(None)
        st = story.normalize(episodes.story_for_episode(ch, "Pip saves a bug", 3, []))
        self.assertEqual((st["format"], st["ending"], st["episode"]), ("episode", "loop", 3))
        block = story.story_block(st)
        for text in ("episode 3", "Pip", "self-contained", '"sfx": "success"', "Attempt and fail"):
            self.assertIn(text, block)
        self.assertIn("mint-green", episodes.picture_notes(st))

    def test_episode_title_and_success_scene(self):
        st = story.normalize(episodes.story_for_episode(episodes.clean_character(None), "x", 4, []))
        script = sm.clean_script({"title": "The Cat Escape #shorts", "scenes": [
            {"narration": "A."}, {"narration": "B."}, {"narration": "C."}, {"narration": "D."}]})
        out = sm.apply_story(script, st)
        self.assertEqual(out["title"], "Pip: The Cat Escape | Ep 4 #shorts")
        self.assertEqual([sc["sfx"] for sc in out["scenes"]], ["", "", "success", ""])

    def test_success_sound_file(self):
        path = episodes.make_success_sound(os.path.join(tempfile.mkdtemp(), "s.wav"))
        self.assertGreater(os.path.getsize(path), 10_000)

    def test_hidden_format_not_on_create_page(self):
        import app
        self.assertNotIn("episode", [f["key"] for f in app.story_options()["formats"]])


if __name__ == "__main__":
    unittest.main()
