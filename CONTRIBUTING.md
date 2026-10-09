# Contributing

Thanks for helping! Keep it simple: Python standard library plus the packages in `requirements.txt`.

## Run it
```
pip install -r requirements.txt
python app.py
```
Run the tests: `python -m unittest discover tests`

## Add a story format
Open `story.py` and add an entry to `STORY_FORMATS`:
```python
"heist": {"name": "Heist", "tagline": "Plan, twist, escape",
          "beats": ["Hook", "The plan", "The snag", "The escape", "Aftermath"],
          "guide": "Tell it like a heist: ..."},
```
It then appears on the Create page automatically. Add a test in `tests/test_core.py` if you change behavior.

## Add a tone or ending
Add to `TONES` (name, writing description, voice rate like `"+5%"`) or `ENDINGS` in `story.py`.

## Rules
- The page lives in `ui.py` as a Python string, because the self-updater only delivers top-level `.py` files on older installs.
- Be kind: see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
