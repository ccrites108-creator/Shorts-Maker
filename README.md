# Shorts Maker

Type an idea. Get a finished vertical video (1080x1920) with an AI-written script, a voiceover,
pictures for every scene, slow camera moves, and big word-by-word captions.
Then upload it to YouTube Shorts.

Open source (MIT license). Everything runs on your own computer.

## What's inside

| Piece | What it uses | Cost |
|---|---|---|
| Script + scene ideas | Open-source model (default `llama3.2`) run locally with Ollama | Free |
| Pictures, option 1 | Free stock photos and clips from Pixabay (needs a free key); Pexels also works if you already have a key | Free, fast |
| Pictures, option 2 | **AI images painted on your computer** by Z-Image-Turbo (Apache 2.0) using stable-diffusion.cpp (MIT) | Free, slow |
| Voiceover | `edge-tts` (open-source library, uses Microsoft's free online voices) | Free, needs internet |
| Video building | Pillow + FFmpeg | Free |

## One-time setup (about 20 minutes, plus downloads)

### 1. Install Python (skip if you already did)
https://www.python.org/downloads/ — on the first screen, check **"Add python.exe to PATH"**.

### 2. Unzip this folder
Right-click `shorts-maker.zip` and choose **Extract All**. Use the new folder it creates.
(Old copies of the app can be ignored or deleted.)

### 3. Install Ollama and a model (this writes the scripts)
- Download Ollama from https://ollama.com and install it.
- Open Command Prompt (Windows key, type `cmd`, Enter) and run:

      ollama pull llama3.2

  It's a few GB, one time only. Note: on some AMD built-in graphics chips Ollama can't use the
  graphics chip yet and runs on the processor instead. That still works, it's just slower
  (script writing can take a minute or two).

### 4. Pictures: pick one (or both)
**Stock footage (fast):** make a free account at https://pixabay.com/accounts/register/ , then open
https://pixabay.com/api/docs/ while logged in. Your API key is shown there in green. You'll paste it into
the app's Settings. (Pexels has paused new keys. If you already have a Pexels key you can use it too.)

**AI images (free, slow):** nothing to do now. The app has a button that downloads it for you
(see "AI images" below).

## Every time you want to make a video

1. Double-click **Start Shorts Maker.bat**.
   - The first time, it installs a few add-ons (about a minute). A black window stays open. Leave it open.
   - Your browser opens the page. (If it doesn't, go to http://localhost:8765)
2. First time only: open **Settings**, paste your Pixabay key (if using stock footage), click **Save settings**. You can also pick a voice.
3. Type your idea, choose **Pictures**, and click **Make my video**.
4. Wait. The progress bar shows each step. When it's done, the video plays on the right.
   Use **Download**, or find it in the `output` folder.
5. Copy the title and description with the buttons, then upload the video to YouTube Shorts.

To stop, close the black window.

## AI images (made on your computer)

Choose **Pictures → AI images** on the page. The first time, click **Set up AI images**.
It downloads, once (about 7 GB, so be patient):

- the image program (stable-diffusion.cpp, from GitHub), and
- the Z-Image-Turbo model files (from Hugging Face).

If the download stops, click the button again. It continues where it left off. Everything goes into
a folder called `ai` next to the app. Delete that folder to uninstall.

**Be realistic about speed.** The app uses your computer's graphics chip through Vulkan, which works
on AMD, Intel and NVIDIA. On AMD/Intel *built-in* graphics, each picture can take several minutes,
so a 6-scene video may take 15 to 30+ minutes. A stronger graphics card is much faster.
The **AI picture detail** option trades quality for speed (Fast is the quickest).
The page shows a running timer while it paints, so you can tell it's still working.

If your graphics chip runs out of memory (the error mentions "alloc compute params backend buffer failed"),
the app downloads a small processor-only version of the image program on its own and uses it from then on.
That works on any computer but is slower, so choose **AI picture detail → Fast** to keep each picture quicker.
To try the graphics chip again, delete `ai\use_cpu.txt`.

If a picture fails, that scene automatically uses stock footage (if you have a stock key) or a colored background.

Windows or your antivirus may warn about the downloaded program because it isn't commonly downloaded.
It comes from the project's official GitHub releases page: https://github.com/leejet/stable-diffusion.cpp/releases

**About AI video:** the open-source video models (Wan, LTX) need a powerful NVIDIA graphics card.
On a laptop with built-in graphics a single short clip would take hours, so this app doesn't try.
Instead, every AI picture gets a slow zoom or pan (a different move each scene) so it feels alive.
The image program supports those video models, so this can be added later if you get a stronger computer.

## Using it on a Mac or a second PC

The app is just this folder, so it moves easily.

- **Another Windows PC:** copy the whole folder. You can copy the `ai` folder too, so you skip the big download,
  but delete `ai\use_cpu.txt` and the `ai\sd-cpu` folder first, because those are specific to one computer.
- **Mac (Apple chip):** install Python from https://www.python.org/downloads/ and Ollama from https://ollama.com
  (then `ollama pull llama3.2`). Copy this folder over, but from the `ai` folder copy **only the `models` folder**
  (the Windows program inside `ai/sd` won't run on a Mac; the app downloads the Mac one itself).
  Then double-click **Start Shorts Maker.command**. If macOS says it can't be opened, right-click it and choose Open.
  If double-clicking does nothing, open Terminal in this folder and run `chmod +x "Start Shorts Maker.command"`.
  The Mac version is untested, so tell Claude if anything fails.

## Quick create or Custom project

Under the idea box, choose how you want to make the video:

- **Quick create:** type an idea and get a finished video.
- **Custom project:** the app writes the script first. You can then edit the title and description, rewrite any
  scene, change what each AI picture shows, give single scenes their own look (photorealistic, anime, watercolor,
  comic book and more), move, add or delete scenes, and change the **hook** (the first scene). **Suggest new hooks**
  gives you five openers of different types (question, bold claim, shocking fact, story, challenge). Click one to use it.
  When you're happy, click **Make video from this project**.

## Pictures are remembered

The app keeps the AI pictures it has painted (in `ai/cache`). If you re-make a video and a scene's picture
description and look are unchanged, that picture is reused instantly, so only changed scenes get repainted.
In a Custom project, tick **Paint this picture again** on a scene to get a fresh one. Delete the `ai/cache`
folder any time to clear the memory.

## Posting your video

Under each finished video is a **Post it** section: **Show video file** opens the folder with the video selected,
and **YouTube upload** and **TikTok upload** open those sites' upload pages. Drag the video onto the page, then use
**Copy title** and **Copy description** for the text. The app can't post for you automatically, because YouTube and
TikTok only allow public posting through their programs after the app has passed their review.

## Tips

- **Your keys are saved once per computer**, in a `.shorts-maker` folder inside your user folder
  (for example `C:\Users\YourName\.shorts-maker\settings.json`). New copies and updates of the app find them
  automatically, so you only paste a key once on each computer. Copy that file to another computer to bring them along.

- **"certificate verify failed" error?** Close the black window and double-click Start Shorts Maker.bat again (it installs a small add-on that fixes this). If it still happens, pause any antivirus/VPN web-scanning feature and try again.

- **Read the script before posting.** Free AI models make factual mistakes. The script is saved in
  the `.txt` file next to each video.
- **Pictures not matching?** Try different wording for your idea, or a bigger Ollama model
  (https://ollama.com/library), then set its name in Settings.
- **Different niches:** use the "Style or niche notes" box (for AI images it also sets the visual look),
  and give each niche its own YouTube channel.
- **Without any picture setup** the app still works, using colored backgrounds.

## YouTube notes
- YouTube asks if content is altered or synthetic. Answer honestly.
- Pixabay and Pexels content is free to use, but check https://pixabay.com/service/license-summary/ and https://www.pexels.com/license/ for current terms.
- Channels posting lots of near-identical automated videos can have trouble monetizing,
  so add your own angle to the ideas you choose.

## Command line (optional)

    python shorts_maker.py "3 weird facts about octopuses"
    python shorts_maker.py "idea" --visuals ai_images
    python shorts_maker.py --demo
    python shorts_maker.py "idea" --engine claude     (paid Claude API instead of Ollama; needs ANTHROPIC_API_KEY)

## Sharing it as open source
Create a free account at https://github.com, make a new public repository, and upload the files
(including `LICENSE`). Don't upload `settings.json` (it holds your key) or the `ai` folder (huge).
The included `.gitignore` already leaves them out if you use git.

If something breaks, copy the error message and ask Claude about it.
