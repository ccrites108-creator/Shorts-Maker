"""
Shorts Maker - the web page (HTML, CSS and JavaScript in one string).

It lives in a .py file so the built-in updater can deliver it. License: MIT (see LICENSE)
"""

PAGE = r"""<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>Shorts Maker</title>
<style>
:root{--bg:#0a0c11;--bg2:#10131a;--card:#151a23;--card2:#1b212d;--line:#262e3d;--text:#e9edf5;--muted:#8d97ab;
--accent:#8b6cff;--accent2:#22d3ee;--ok:#34d399;--bad:#fb7185;--warn:#fbbf24;--r:16px;color-scheme:dark}
*{box-sizing:border-box}
html{background:var(--bg)}
body{margin:0;font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--text);
background:radial-gradient(900px 500px at 85% -10%,rgba(139,108,255,.16),transparent 60%),radial-gradient(700px 400px at -10% 0%,rgba(34,211,238,.09),transparent 60%),var(--bg);min-height:100vh}
a{color:var(--accent2)}
code{background:var(--card2);padding:1px 6px;border-radius:6px;font-size:.9em}
header.top{position:sticky;top:0;z-index:20;background:rgba(10,12,17,.82);backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
.top .in{max-width:1180px;margin:0 auto;padding:12px 20px;display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:18px;letter-spacing:-.01em}
.logo{width:30px;height:30px;border-radius:9px;background:linear-gradient(135deg,var(--accent),var(--accent2));display:grid;place-items:center;color:#06070a;font-weight:900}
.tabs{display:flex;gap:4px;flex:1;flex-wrap:nowrap;overflow-x:auto}
.tab{white-space:nowrap;background:none;border:0;color:var(--muted);font:inherit;font-weight:600;padding:8px 14px;border-radius:10px;cursor:pointer}
.tab:hover{color:var(--text);background:var(--card)}
.tab.on{color:var(--text);background:var(--card2);box-shadow:inset 0 -2px 0 var(--accent)}
.ver{color:var(--muted);font-size:13px}
main{max-width:1180px;margin:0 auto;padding:22px 20px 60px}
.grid{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:24px;align-items:start}
.side{position:sticky;top:82px}
@media(max-width:940px){.grid{grid-template-columns:1fr}.side{position:static;order:-1}.phone{max-width:240px}.side.empty{display:none}.top .in{gap:8px}.tabs{order:3;flex-basis:100%}}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:22px;margin-bottom:18px}
h1{font-size:30px;letter-spacing:-.02em;margin:0 0 4px}
h2{font-size:19px;margin:0 0 14px;letter-spacing:-.01em}
h3{font-size:15px;margin:0 0 8px}
.sub{color:var(--muted);margin:0 0 20px}
.field{margin-bottom:18px}
label,.lab{display:block;font-weight:600;font-size:14px;margin-bottom:6px}
.hint{color:var(--muted);font-size:13px;margin-top:6px}
input,textarea,select{width:100%;background:var(--bg2);color:var(--text);border:1px solid var(--line);border-radius:12px;padding:11px 13px;font:inherit}
textarea{resize:vertical;min-height:92px}
input:focus,textarea:focus,select:focus,button:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:1px;border-color:transparent}
::placeholder{color:#5f6a80}
select option{background:var(--bg2)}
button{font:inherit;cursor:pointer}
button:disabled{opacity:.45;cursor:not-allowed}
.primary{width:100%;border:0;border-radius:14px;padding:14px;font-weight:700;font-size:17px;color:#07080c;background:linear-gradient(135deg,var(--accent),var(--accent2));transition:transform .1s,filter .15s}
.primary:hover:not(:disabled){filter:brightness(1.1)}.primary:active:not(:disabled){transform:scale(.99)}
.ghost{background:var(--card2);color:var(--text);border:1px solid var(--line);border-radius:980px;padding:9px 16px;font-weight:600;font-size:14px;text-decoration:none;display:inline-block}
.ghost:hover:not(:disabled){border-color:var(--accent)}
.mini{background:var(--card2);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:4px 10px;font-size:13px}
.mini:hover:not(:disabled){border-color:var(--accent)}
.mini.danger{background:var(--bad);color:#16060a;border-color:var(--bad)}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.seg{display:flex;gap:6px;flex-wrap:wrap}
.seg button{flex:1;min-width:84px;overflow-wrap:anywhere;background:var(--bg2);color:var(--text);border:1px solid var(--line);border-radius:12px;padding:10px 12px;font-weight:600;text-align:left}
.seg button small{display:block;color:var(--muted);font-weight:400;font-size:12px;margin-top:1px}
.seg button:hover{border-color:#3a4560}
.seg button.on{border-color:var(--accent);background:rgba(139,108,255,.14);box-shadow:0 0 0 1px var(--accent) inset}
.formats{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px}
.fcard{text-align:left;background:var(--bg2);color:var(--text);border:1px solid var(--line);border-radius:14px;padding:12px}
.fcard b{display:block}.fcard span.t{color:var(--muted);font-size:13px}
.fcard.on{border-color:var(--accent);background:rgba(139,108,255,.14);box-shadow:0 0 0 1px var(--accent) inset}
.fcard:hover{border-color:#3a4560}
.beats{display:flex;gap:4px;flex-wrap:wrap;margin-top:8px}
.beat{font-size:11px;padding:2px 8px;border-radius:980px;background:var(--card2);color:var(--muted);border:1px solid var(--line)}
.beatbar{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px}
.beatbar .beat{font-size:12px;padding:4px 11px}
.beatbar .beat.hit{color:#07080c;background:linear-gradient(135deg,var(--accent),var(--accent2));border-color:transparent;font-weight:600}
input[type=range]{padding:0;height:6px;border-radius:6px;border:0;appearance:none;-webkit-appearance:none;background:var(--card2)}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:22px;height:22px;border-radius:50%;background:#fff;border:3px solid var(--accent);cursor:pointer}
input[type=range]::-moz-range-thumb{width:18px;height:18px;border-radius:50%;background:#fff;border:3px solid var(--accent);cursor:pointer}
.notice{background:rgba(251,191,36,.08);border:1px solid rgba(251,191,36,.3);border-radius:12px;padding:12px 14px;margin-bottom:16px;font-size:14px}
.err{color:var(--bad);white-space:pre-wrap;font-size:14px}
.err:not(:empty){background:rgba(251,113,133,.08);border:1px solid rgba(251,113,133,.3);border-radius:12px;padding:12px 14px;margin-bottom:16px}
#progressBox{position:sticky;top:64px;z-index:15}
.progress{background:var(--card);border:1px solid var(--accent);border-radius:var(--r);padding:16px 18px;margin-bottom:18px;box-shadow:0 8px 30px rgba(0,0,0,.4)}
.steps{list-style:none;margin:0 0 10px;padding:0;display:flex;flex-direction:column;gap:6px;font-size:14px}
.steps li{display:flex;gap:10px;align-items:center;color:var(--muted)}
.steps .dot{width:10px;height:10px;border-radius:50%;background:var(--line)}
.steps li.done{color:var(--text)}.steps li.done .dot{background:var(--ok)}
.steps li.active{color:var(--text);font-weight:600}.steps li.active .dot{background:var(--accent2);animation:pulse 1.2s infinite}
@keyframes pulse{50%{opacity:.3}}
.bar{height:8px;border-radius:8px;background:var(--card2);overflow:hidden}
.bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--accent),var(--accent2));transition:width .5s}
.msg{font-size:13px;color:var(--muted);margin-top:8px}
.phone{aspect-ratio:9/16;max-width:320px;margin:0 auto;border-radius:28px;background:#000;border:1px solid var(--line);box-shadow:0 20px 60px rgba(0,0,0,.55),0 0 0 6px var(--card);display:grid;place-items:center;text-align:center;color:var(--muted);font-size:14px;padding:20px;overflow:hidden}
.phone video{width:100%;height:100%;object-fit:cover}.phone.has{padding:0}
.meta{margin-top:20px}.meta b{display:block;font-size:16px}.meta p{color:var(--muted);font-size:14px;white-space:pre-wrap}
.post{margin-top:14px;padding-top:14px;border-top:1px solid var(--line)}
.scene{background:var(--bg2);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px}
.sh{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px}
.sh .tag{font-size:11px;padding:2px 9px;border-radius:980px;background:rgba(139,108,255,.18);color:#c4b5fd;margin-left:8px;font-weight:600}
.acts{display:flex;gap:4px}
.rw{background:var(--card);border:1px dashed var(--line);border-radius:12px;padding:10px;margin-top:6px}
.rw .row{margin-bottom:8px}
.chips{display:flex;flex-direction:column;gap:6px;margin-top:10px}
.chip{text-align:left;background:var(--card2);color:var(--text);border:1px solid var(--line);border-radius:12px;padding:9px 12px;font-size:14px}
.chip small{display:block;color:var(--accent2);font-size:11px;text-transform:uppercase;letter-spacing:.05em}
.chip:hover:not(:disabled){border-color:var(--accent)}
.check{display:flex;gap:8px;align-items:center;font-weight:400;font-size:13px;color:var(--muted)}
.check input{width:auto}
.ai-only,.stock-only{display:none}
#editor.ai .ai-only{display:block}#editor:not(.ai) .stock-only{display:block}
.vgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px}
.vcard{background:var(--bg2);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.vcard .th{aspect-ratio:9/16;background:#000;cursor:pointer;position:relative}
.vcard video{width:100%;height:100%;object-fit:cover;display:block;pointer-events:none}
.vcard .th:hover{outline:2px solid var(--accent);outline-offset:-2px}
.vcard .t{padding:10px 10px 4px;font-size:13px;font-weight:600;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.vcard .w{padding:0 10px;font-size:12px;color:var(--muted)}
.vcard .d{padding:8px 10px 10px;display:flex;gap:6px}
.series{border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:16px;background:var(--bg2)}
.part{display:grid;grid-template-columns:34px 1fr auto;gap:10px;padding:12px 0;border-top:1px solid var(--line);align-items:start}
.part .n{width:30px;height:30px;border-radius:50%;background:var(--card2);display:grid;place-items:center;font-weight:700;font-size:13px}
.part.made .n{background:var(--ok);color:#052e1f}
.part input{margin-bottom:6px;font-weight:600}.part textarea{min-height:60px;font-size:14px}
@media(max-width:560px){.part{grid-template-columns:30px 1fr}.part .pa{grid-column:1/-1;display:flex;gap:6px;flex-wrap:wrap}}
.pa{display:flex;flex-direction:column;gap:6px}
details>summary{cursor:pointer;font-weight:600}
.panel[hidden],[hidden]{display:none!important}
.about{display:grid;gap:10px;color:var(--muted);font-size:14px}
footer{color:var(--muted);font-size:13px;text-align:center;padding:10px 20px 40px}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
.grid.solo{grid-template-columns:minmax(0,760px)}
</style>
</head>
<body>
<header class="top"><div class="in">
  <div class="brand"><span class="logo">S</span>Shorts Maker</div>
  <nav class="tabs" role="tablist">
    <button class="tab on" data-tab="create" role="tab">Create</button>
    <button class="tab" data-tab="series" role="tab">Series</button>
    <button class="tab" data-tab="library" role="tab">Library</button>
    <button class="tab" data-tab="settings" role="tab">Settings</button>
  </nav>
  <span class="ver" id="ver"></span>
</div></header>

<main>
<div id="progressBox"><div class="progress" id="progress" hidden>
  <ul class="steps" id="steps"></ul>
  <div class="bar"><i id="fill"></i></div>
  <div class="msg" id="msg"></div>
</div></div>
<div id="error" class="err" role="alert"></div>

<div class="grid">
<div class="main">

<!-- ======================= CREATE ======================= -->
<section class="panel" id="tab-create">
  <h1>Tell a story in 60 seconds</h1>
  <p class="sub">Type an idea. Pick how it should be told. Get a finished vertical video with a voice, pictures and captions.</p>

  <div class="card">
    <div id="keyNotice" class="notice" hidden>
      Stock footage needs a free Pixabay key. Open <b>Settings</b> and paste it in. Or switch to AI pictures below.
    </div>
    <div class="field">
      <label for="idea">What is the video about?</label>
      <textarea id="idea" placeholder="e.g. The Antikythera mechanism: a 2,000-year-old computer found in a shipwreck"></textarea>
    </div>

    <div class="field">
      <span class="lab">Story format</span>
      <div class="formats" id="formats"></div>
      <select id="sformat" hidden></select>
    </div>
    <div class="field">
      <span class="lab">Narrator tone</span>
      <div class="seg" id="toneSeg" data-for="tone"></div>
      <select id="tone" hidden></select>
    </div>
    <div class="field">
      <span class="lab">How should it end?</span>
      <div class="seg" id="endSeg" data-for="ending"></div>
      <select id="ending" hidden></select>
    </div>
    <div class="field">
      <details id="bibleBox">
        <summary>Story world (optional): keep every picture looking like one story</summary>
        <textarea id="bible" style="margin-top:10px" maxlength="400" placeholder="e.g. Ancient Egypt at golden hour, warm sandstone, torchlight, dusty air, cinematic"></textarea>
        <div class="hint">Used for every picture, so the whole video (or series) feels like one world.</div>
      </details>
    </div>

    <div class="field">
      <label for="style">Extra direction (optional)</label>
      <input id="style" placeholder="e.g. keep it simple enough for a 10 year old">
    </div>
    <div class="field">
      <label for="length">Length <span id="lengthVal" style="font-weight:600">45 seconds</span></label>
      <input type="range" id="length" min="30" max="90" step="5" value="45">
      <div class="hint" id="lengthHint"></div>
      <div class="hint">TikTok pays creators on videos over 60 seconds.</div>
    </div>
    <div class="field">
      <span class="lab">Intro button</span>
      <div class="seg" data-for="intro">
        <button type="button" data-v="subscribe">Subscribe<small>YouTube style</small></button>
        <button type="button" data-v="follow">Follow<small>TikTok style</small></button>
        <button type="button" data-v="both">Both<small>One after the other</small></button>
      </div>
      <select id="intro" hidden><option value="subscribe">Subscribe</option><option value="follow">Follow</option><option value="both">Both</option></select>
    </div>
    <div class="field">
      <span class="lab">Pictures</span>
      <div class="seg" data-for="mode">
        <button type="button" data-v="stock">Stock footage<small>Real clips and photos</small></button>
        <button type="button" data-v="ai_images">AI pictures<small>Painted on your computer</small></button>
      </div>
      <select id="mode" hidden><option value="stock">Stock</option><option value="ai_images">AI</option></select>
      <div class="hint" id="modeHint"></div>
    </div>
    <div class="field" id="qualityField" hidden>
      <span class="lab">AI picture detail</span>
      <div class="seg" data-for="quality">
        <button type="button" data-v="fast">Fast<small>Quickest, a bit softer</small></button>
        <button type="button" data-v="standard">Standard<small>Balanced</small></button>
        <button type="button" data-v="high">High<small>Sharpest, slowest</small></button>
      </div>
      <select id="quality" hidden><option value="fast">Fast</option><option value="standard">Standard</option><option value="high">High</option></select>
    </div>
    <div id="aiSetup" class="notice" hidden>
      AI pictures need a one-time download (about 7 GB) of open-source software and models.
      Keep this window open while it downloads. If it stops, click the button again and it continues.
      <div style="margin-top:10px"><button class="ghost" id="setupBtn">Set up AI pictures</button></div>
    </div>
    <div class="field" id="styleField" hidden>
      <label for="imgstyle">Look of the AI pictures</label>
      <select id="imgstyle"></select>
      <div class="hint">Auto lets the script pick a look that fits the idea.</div>
    </div>
    <div class="field">
      <span class="lab">How do you want to make it?</span>
      <div class="seg" data-for="flow">
        <button type="button" data-v="quick">Quick create<small>Just a prompt</small></button>
        <button type="button" data-v="project">Custom project<small>Edit and rewrite scenes first</small></button>
      </div>
      <select id="flow" hidden><option value="quick">Quick</option><option value="project">Project</option></select>
      <div class="hint" id="flowHint"></div>
    </div>
    <button id="go" class="primary">Make my video</button>
    <div id="resumeBox" class="notice" hidden style="margin-top:16px"></div>
  </div>

  <div class="card" id="editor" hidden>
    <h2>Your project</h2>
    <div class="beatbar" id="beatbar"></div>
    <div class="field"><label for="ptitle">Title</label><input id="ptitle"></div>
    <div class="field"><label for="pdesc">Description</label><textarea id="pdesc" style="min-height:70px"></textarea></div>
    <span class="lab">Scenes</span>
    <div id="scenes"></div>
    <button class="ghost needs-idle" id="addScene">+ Add scene</button>
    <div class="hint" id="projLen" style="margin:14px 0"></div>
    <button id="makeProject" class="primary needs-idle">Make video from this project</button>
  </div>
</section>

<!-- ======================= SERIES ======================= -->
<section class="panel" id="tab-series" hidden>
  <h1>Multi-part series</h1>
  <p class="sub">Plan a story across several videos. Each part recaps the last one and teases the next, so people follow for the rest.</p>
  <div class="card">
    <div class="field"><label for="stopic">What is the series about?</label>
      <textarea id="stopic" placeholder="e.g. The greatest unsolved mysteries of ancient Egypt"></textarea></div>
    <div class="field"><span class="lab">Number of parts</span>
      <div class="seg" data-for="sparts">
        <button type="button" data-v="3">3</button><button type="button" data-v="4">4</button>
        <button type="button" data-v="5">5</button><button type="button" data-v="6">6</button>
      </div>
      <select id="sparts" hidden><option>3</option><option selected>4</option><option>5</option><option>6</option></select></div>
    <div class="field"><label for="sformat2">Story format</label><select id="sformat2"></select></div>
    <div class="field"><label for="stone">Narrator tone</label><select id="stone"></select></div>
    <div class="field"><label for="sbible">Story world (optional)</label>
      <textarea id="sbible" style="min-height:70px" maxlength="400" placeholder="A look that stays the same in every part"></textarea></div>
    <button class="primary needs-idle" id="planSeries">Plan my series</button>
    <div class="hint">Needs Ollama running, like the script writer. Parts are made one at a time, using the picture and length choices on the Create tab.</div>
  </div>
  <div id="seriesList"></div>
</section>

<!-- ======================= LIBRARY ======================= -->
<section class="panel" id="tab-library" hidden>
  <h1>Your videos</h1>
  <p class="sub">Click a video to watch it and get it ready to post.</p>
  <div class="card"><div class="vgrid" id="videos"><div class="hint">Nothing yet.</div></div></div>
</section>

<!-- ======================= SETTINGS ======================= -->
<section class="panel" id="tab-settings" hidden>
  <h1>Settings</h1>
  <p class="sub">Everything runs on your own computer.</p>
  <div class="card">
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
    <div class="field"><label for="voice">Voice</label><select id="voice"></select></div>
    <div class="field">
      <label for="model">Script model (Ollama)</label>
      <input id="model" placeholder="llama3.2">
      <div class="hint">Any model you've downloaded with <code>ollama pull</code>. Bigger models write better scripts.</div>
    </div>
    <button class="ghost" id="save">Save settings</button>
    <span class="hint" id="saved" style="margin-left:10px"></span>
  </div>
  <div class="card">
    <h2>About</h2>
    <div class="about">
      <div>Shorts Maker is free and open source (MIT license). It updates itself when you open it.</div>
      <div><a href="https://github.com/ccrites108-creator/Shorts-Maker" target="_blank" rel="noopener">Source code, issues and ideas on GitHub</a></div>
      <div>AI can get facts wrong. Read every script before you post.</div>
    </div>
  </div>
</section>

</div>

<aside class="side empty" id="side">
  <div class="phone" id="phone">Your video will appear here</div>
  <div class="meta" id="meta" hidden>
    <b id="mtitle"></b>
    <p id="mdesc"></p>
    <div class="row">
      <button class="ghost" id="copyTitle">Copy title</button>
      <button class="ghost" id="copyDesc">Copy description</button>
      <a id="dl" class="ghost">Download</a>
    </div>
    <div class="post">
      <b>Post it</b>
      <p>Show the file, open the upload page, then drag the video onto it.</p>
      <div class="row">
        <button class="ghost" id="reveal">Show video file</button>
        <a class="ghost" href="https://www.youtube.com/upload" target="_blank" rel="noopener">YouTube</a>
        <a class="ghost" href="https://www.tiktok.com/upload" target="_blank" rel="noopener">TikTok</a>
      </div>
    </div>
    <p class="hint" style="margin-top:12px">Read the script text before posting. AI can get facts wrong.</p>
  </div>
</aside>
</div>
</main>
<footer>Shorts Maker · open source · MIT</footer>

<script>
const $ = id => document.getElementById(id);
let timer = null, current = null, cfg = {has_key: false, ai_ready: false}, opts = null;
let project = null, hooks = [], projectStory = null, seriesItems = [];

async function api(path, body) {
  const o = body ? {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)} : {};
  try { const r = await fetch(path, o); return await r.json(); }
  catch (e) { return {error: "Can't reach Shorts Maker. Is the black window still open?"}; }
}
function el(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v; else if (k.startsWith('on')) e[k] = v; else e.setAttribute(k, v);
  }
  kids.flat().forEach(c => e.append(c));
  return e;
}
const field = (label, input, cls = '') => el('div', {class: 'field ' + cls}, el('label', {}, label), input);
const miniBtn = (text, fn, disabled, label) => { const b = el('button', {class: 'mini', type: 'button', 'aria-label': label || text}, text); b.onclick = fn; b.disabled = !!disabled; return b; };
const setError = t => { $('error').textContent = t || ''; };

// ------------------------------------------------------------ tabs
function openTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.dataset.tab === name));
  document.querySelectorAll('.panel').forEach(p => p.hidden = p.id !== 'tab-' + name);
  $('side').hidden = name === 'settings';
  document.querySelector('.grid').classList.toggle('solo', name === 'settings');
  if (name === 'library') loadVideos();
  if (name === 'series') loadSeries();
  try { location.hash = name; } catch (e) {}
}
document.querySelectorAll('.tab').forEach(t => t.onclick = () => openTab(t.dataset.tab));

// ------------------------------------------------------------ segmented controls
function syncSegs() {
  document.querySelectorAll('.seg').forEach(seg => [...seg.children].forEach(
    b => b.classList.toggle('on', b.dataset.v === $(seg.dataset.for).value)));
  document.querySelectorAll('.fcard').forEach(c => c.classList.toggle('on', c.dataset.v === $('sformat').value));
}
document.addEventListener('click', e => {
  const b = e.target.closest('.seg button');
  if (b) {
    const sel = $(b.parentElement.dataset.for);
    sel.value = b.dataset.v;
    if (sel.onchange) sel.onchange();
    syncSegs();
  }
});

// ------------------------------------------------------------ settings & options
async function loadOptions() {
  opts = await api('/api/story-options');
  if (!opts.formats) return;
  const fill = (id, items) => $(id).innerHTML = items.map(x => `<option value="${x.key}">${x.name}</option>`).join('');
  fill('sformat', opts.formats); fill('tone', opts.tones); fill('ending', opts.endings);
  fill('sformat2', opts.formats); fill('stone', opts.tones);
  $('formats').innerHTML = '';
  opts.formats.forEach(f => {
    const c = el('button', {class: 'fcard', type: 'button', 'data-v': f.key},
      el('b', {}, f.name), el('span', {class: 't'}, f.tagline),
      el('div', {class: 'beats'}, f.beats.map(x => el('span', {class: 'beat'}, x))));
    c.onclick = () => { $('sformat').value = f.key; syncSegs(); };
    $('formats').append(c);
  });
  [['toneSeg', 'tone', opts.tones], ['endSeg', 'ending', opts.endings]].forEach(([box, , items]) => {
    $(box).innerHTML = '';
    items.forEach(x => $(box).append(el('button', {type: 'button', 'data-v': x.key}, x.name)));
  });
}

async function loadSettings() {
  const s = await api('/api/settings');
  if (s.error) { setError(s.error); return; }
  cfg = s;
  $('ver').textContent = s.version ? 'v' + s.version : '';
  $('pexels').placeholder = s.has_key ? 'Key saved. Paste a new one to replace it.' : 'Paste your key here';
  $('pixabay').placeholder = s.has_pixabay_key ? 'Key saved. Paste a new one to replace it.' : 'Paste your key here';
  $('model').value = s.ollama_model;
  $('voice').innerHTML = s.voices.map(v => `<option value="${v[0]}">${v[1]}</option>`).join('');
  $('voice').value = s.voice;
  $('mode').value = (!s.has_key && !s.has_pixabay_key && s.ai_ready) ? 'ai_images' : s.visual_mode;
  $('quality').value = s.ai_image_quality;
  $('intro').value = s.intro_button || 'subscribe';
  $('length').value = s.video_seconds || 45;
  $('imgstyle').innerHTML = '<option value="auto">Auto</option>' + (s.image_styles || []).map(x => `<option value="${x[0]}">${x[1]}</option>`).join('');
  $('imgstyle').value = s.image_style || 'auto';
  if (opts && opts.formats) {
    $('sformat').value = s.story_format; $('tone').value = s.story_tone; $('ending').value = s.story_ending;
    $('sformat2').value = s.story_format === 'explainer' ? 'mystery' : s.story_format; $('stone').value = s.story_tone;
  }
  updateFlow(); updateMode();
}

function updateMode() {
  const ai = $('mode').value === 'ai_images';
  $('qualityField').hidden = !ai;
  $('styleField').hidden = !ai;
  $('editor').classList.toggle('ai', ai);
  $('keyNotice').hidden = ai || cfg.has_key || cfg.has_pixabay_key;
  $('aiSetup').hidden = !(ai && !cfg.ai_ready);
  syncSegs(); updateLength();
  $('modeHint').textContent = ai
    ? 'Pictures are painted by an open-source AI on your own computer. On built-in graphics each picture can take several minutes, so a video may take 15 to 30+ minutes.'
    : 'Real video clips and photos matched to each scene.';
}
$('mode').onchange = updateMode;

function updateLength() {
  const sec = +$('length').value, scenes = Math.max(4, Math.min(12, Math.round(sec / 7.5)));
  $('lengthVal').textContent = sec + ' seconds';
  const pct = (sec - 30) / 60 * 100;
  $('length').style.background = `linear-gradient(to right, var(--accent) ${pct}%, var(--card2) ${pct}%)`;
  $('lengthHint').textContent = 'About ' + scenes + ' scenes.' +
    ($('mode').value === 'ai_images' ? ' With AI pictures, every scene is painted one by one, so longer videos take much longer.' : '');
}
$('length').oninput = updateLength;

$('save').onclick = async () => {
  await api('/api/settings', {pexels_key: $('pexels').value, pixabay_key: $('pixabay').value,
                              ollama_model: $('model').value, voice: $('voice').value});
  $('pexels').value = ''; $('pixabay').value = '';
  $('saved').textContent = 'Saved.'; setTimeout(() => $('saved').textContent = '', 2500);
  loadSettings();
};

function goLabel() { return $('flow').value === 'project' ? 'Write the script' : 'Make my video'; }
function updateFlow() {
  $('go').textContent = goLabel();
  $('flowHint').textContent = $('flow').value === 'project'
    ? 'Writes the script first, so you can edit and rewrite scenes, pictures and the hook before the video is made.'
    : 'One click: type an idea and get a finished video.';
  syncSegs();
}
$('flow').onchange = updateFlow;

// ------------------------------------------------------------ jobs
function storyBody() {
  return {story_format: $('sformat').value, tone: $('tone').value, ending: $('ending').value, bible: $('bible').value.trim()};
}
function lookBody() {
  return {mode: $('mode').value, quality: $('quality').value, seconds: +$('length').value,
          image_style: $('imgstyle').value, intro: $('intro').value};
}
function renderSteps(items) {
  $('steps').innerHTML = '';
  items.forEach(i => $('steps').append(el('li', {class: i.state}, el('span', {class: 'dot'}), el('span', {}, i.label))));
}
function setBusy(b, label) {
  document.querySelectorAll('.needs-idle, #go, #planSeries').forEach(x => x.disabled = b);
  document.querySelectorAll('.partbtn').forEach(x => x.disabled = b);
  if (label !== undefined) $('go').textContent = label;
}
function watch(id, first, steps) {
  setError(''); setBusy(true);
  $('progress').hidden = false; $('fill').style.width = '4%'; $('msg').textContent = first || '';
  renderSteps(steps || []);
  clearInterval(timer);
  timer = setInterval(() => poll(id), 1500);
}
function finish() {
  clearInterval(timer); loadUnfinished();
  setBusy(false, goLabel()); $('setupBtn').disabled = false; $('progress').hidden = true;
}
function waitingPhone() { $('side').classList.remove('empty'); $('phone').classList.remove('has'); $('phone').textContent = 'Working on it. This takes a while.'; $('meta').hidden = true; }

async function poll(id) {
  const s = await api('/api/status?id=' + id);
  if (s.error && !s.state) { finish(); setError(s.error); return; }
  $('fill').style.width = (s.pct || 0) + '%';
  $('msg').textContent = s.message || '';
  renderSteps(s.steps || []);
  if (s.state === 'done') {
    finish();
    const r = s.result || {};
    if (s.kind === 'setup') { await loadSettings(); $('modeHint').textContent = 'AI pictures are ready to use.'; return; }
    if (s.kind === 'draft') {
      project = r.script; hooks = []; renderEditor(); $('editor').hidden = false;
      $('editor').scrollIntoView({behavior: 'smooth'}); return;
    }
    if (s.kind === 'hooks') { hooks = r.hooks; renderEditor(); return; }
    if (s.kind === 'rewrite') {
      if (project && project.scenes[r.index]) project.scenes[r.index] = Object.assign({}, project.scenes[r.index], r.scene);
      renderEditor(); return;
    }
    if (s.kind === 'series') {
      await loadSeries();
      setError(r.note ? 'Heads up: ' + r.note : '');
      return;
    }
    show(r.name, r.title, r.description);
    setError((r.warnings || []).join('\n\n'));
    loadVideos(); loadSeries();
  } else if (s.state === 'error') {
    finish();
    if (s.kind === 'video') { $('phone').classList.remove('has'); $('phone').textContent = 'Your video will appear here'; }
    setError(s.message);
  }
}

// ------------------------------------------------------------ creating
$('go').onclick = async () => {
  const idea = $('idea').value.trim();
  setError('');
  if (!idea) { setError('Type an idea first.'); return; }
  if ($('flow').value === 'project') {
    projectStory = storyBody();
    const res = await api('/api/draft', Object.assign({idea, style: $('style').value, seconds: +$('length').value}, projectStory));
    if (res.error) { setError(res.error); return; }
    watch(res.id, 'Writing the script...'); $('go').textContent = 'Writing the script...';
    return;
  }
  const res = await api('/api/generate', Object.assign({idea, style: $('style').value}, lookBody(), storyBody()));
  if (res.error) { setError(res.error); return; }
  watch(res.id, 'Making your video...', [{label: 'Write the script', state: 'active'}]);
  $('go').textContent = 'Making your video...'; waitingPhone();
};

$('makeProject').onclick = async () => {
  const res = await api('/api/generate', Object.assign({idea: $('idea').value.trim(), script: project},
    lookBody(), projectStory || storyBody()));
  if (res.error) { setError(res.error); return; }
  watch(res.id, 'Making your video...'); $('go').textContent = 'Making your video...'; waitingPhone();
  window.scrollTo({top: 0, behavior: 'smooth'});
};

$('setupBtn').onclick = async () => {
  setError('');
  const res = await api('/api/setup-ai', {});
  if (res.error) { setError(res.error); return; }
  $('setupBtn').disabled = true; watch(res.id, 'Starting the download...');
};

async function loadUnfinished() {
  const items = ((await api('/api/unfinished')).items) || [];
  const box = $('resumeBox');
  box.hidden = !items.length; box.innerHTML = '';
  items.forEach(it => box.append(el('div', {style: 'margin:4px 0'},
    el('b', {}, (it.idea || 'Unfinished video').slice(0, 60)), ' · ' + it.done + ' of ' + it.total + ' scenes finished  ',
    el('button', {class: 'ghost', onclick: () => resumeVideo(it.key)}, 'Continue'), ' ',
    el('button', {class: 'ghost', onclick: async () => { await api('/api/discard', {key: it.key}); loadUnfinished(); }}, 'Discard'))));
}
async function resumeVideo(key) {
  const res = await api('/api/resume', {key});
  if (res.error) { setError(res.error); return; }
  watch(res.id, 'Picking up where it left off...', [{label: 'Picking up where it left off', state: 'active'}]);
  waitingPhone();
}

// ------------------------------------------------------------ project editor
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
const PRESETS = [['Punchier', 'Make it shorter and punchier.'], ['More dramatic', 'Make it more dramatic and vivid.'],
  ['Add a surprising fact', 'Add one surprising, true detail.'], ['Simpler words', 'Use simpler words a 10 year old understands.'],
  ['New picture idea', 'Keep the narration but give it a completely different, more striking picture.']];

function renderBeatBar() {
  const fmt = opts && opts.formats ? opts.formats.find(f => f.key === (projectStory || storyBody()).story_format) : null;
  const bar = $('beatbar'); bar.innerHTML = '';
  if (!fmt) return;
  const hit = new Set(project.scenes.map(s => (s.beat || '').toLowerCase()));
  fmt.beats.forEach(b => bar.append(el('span', {class: 'beat' + (hit.has(b.toLowerCase()) ? ' hit' : '')}, b)));
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
    const q = el('input', {placeholder: 'e.g. desert ruins'}); q.value = sc.visual_query;
    q.oninput = () => { sc.visual_query = q.value; };
    const head = el('div', {class: 'sh'},
      el('span', {}, el('b', {}, i === 0 ? 'Scene 1 · Hook' : 'Scene ' + (i + 1)), sc.beat ? el('span', {class: 'tag'}, sc.beat) : ''),
      el('span', {class: 'acts'},
        miniBtn('↑', () => moveScene(i, -1), i === 0, 'Move up'), miniBtn('↓', () => moveScene(i, 1), i === last, 'Move down'),
        miniBtn('✕', () => removeScene(i), project.scenes.length <= 2, 'Remove scene')));
    const card = el('div', {class: 'scene'}, head,
      field(i === 0 ? 'Hook: the first thing people hear' : 'What the voice says', nar));

    // rewrite tools
    const inst = el('input', {placeholder: 'Or tell it what to change, e.g. "mention the year"', maxlength: '300'});
    const run = text => rewriteScene(i, text || inst.value);
    const go = el('button', {class: 'ghost needs-idle', type: 'button'}, 'Rewrite');
    go.onclick = () => run();
    card.append(el('details', {}, el('summary', {}, 'Rewrite this scene'),
      el('div', {class: 'rw'},
        el('div', {class: 'row'}, PRESETS.map(([n, t]) => { const b = el('button', {class: 'mini needs-idle', type: 'button'}, n); b.onclick = () => run(t); return b; })),
        el('div', {class: 'row'}, el('div', {style: 'flex:1;min-width:180px'}, inst), go))));

    if (i === 0) {
      const hb = el('button', {class: 'ghost needs-idle', type: 'button', style: 'margin-top:12px'}, 'Suggest new hooks');
      hb.onclick = suggestHooks;
      card.append(el('div', {}, hb, el('div', {class: 'chips'}, hooks.map(h => {
        const c = el('button', {class: 'chip needs-idle', type: 'button'}, el('small', {}, h.type), h.text);
        c.onclick = () => { project.scenes[0].narration = h.text; renderEditor(); };
        return c;
      }))));
    }
    const fresh = el('input', {type: 'checkbox'}); fresh.checked = !!sc.fresh;
    fresh.onchange = () => { sc.fresh = fresh.checked; };
    card.append(el('div', {class: 'ai-only', style: 'margin-top:12px'}, field('Picture', img), field('Look of this picture', look),
                  el('label', {class: 'check'}, fresh, ' Paint this picture again (otherwise the last one is reused)')),
                el('div', {class: 'stock-only', style: 'margin-top:12px'}, field('Stock footage search words', q)));
    box.append(card);
  });
  updateProjLen(); renderBeatBar();
  $('editor').classList.toggle('ai', $('mode').value === 'ai_images');
}
function moveScene(i, d) { const j = i + d, s = project.scenes; if (j < 0 || j >= s.length) return; [s[i], s[j]] = [s[j], s[i]]; renderEditor(); }
function removeScene(i) { project.scenes.splice(i, 1); renderEditor(); }
$('addScene').onclick = () => { project.scenes.push({narration: '', image_prompt: '', visual_query: '', style: ''}); renderEditor(); };
$('ptitle').oninput = () => { if (project) project.title = $('ptitle').value; };
$('pdesc').oninput = () => { if (project) project.description = $('pdesc').value; };

async function suggestHooks() {
  const res = await api('/api/hooks', {idea: $('idea').value, script: project});
  if (res.error) { setError(res.error); return; }
  watch(res.id, 'Thinking up new hooks...');
}
async function rewriteScene(index, instruction) {
  if (!String(instruction || '').trim()) { setError('Pick a quick option or type what to change.'); return; }
  const res = await api('/api/rewrite', Object.assign({script: project, index, instruction}, projectStory || storyBody()));
  if (res.error) { setError(res.error); return; }
  watch(res.id, 'Rewriting scene ' + (index + 1) + '...');
}

// ------------------------------------------------------------ preview & library
function show(name, title, desc) {
  current = {name, title, desc};
  const ph = $('phone'); ph.innerHTML = ''; ph.classList.add('has');
  const v = el('video', {controls: '', autoplay: '', playsinline: ''});
  v.src = '/video/' + encodeURIComponent(name) + '?t=' + Date.now();
  ph.append(v);
  $('mtitle').textContent = title; $('mdesc').textContent = desc || '';
  $('dl').href = '/video/' + encodeURIComponent(name) + '?download=1';
  $('meta').hidden = false; $('side').classList.remove('empty');
  if (window.innerWidth < 940) window.scrollTo({top: 0, behavior: 'smooth'});
}
async function removeVideo(name) {
  if (current && current.name === name) { // Windows won't delete a file that is open
    $('phone').classList.remove('has'); $('phone').innerHTML = 'Your video will appear here'; $('meta').hidden = true; current = null;
  }
  await new Promise(r => setTimeout(r, 300));
  const res = await api('/api/delete', {name});
  if (res.error) setError(res.error);
  loadVideos();
}
async function loadVideos() {
  const items = await api('/api/videos');
  const box = $('videos'); box.innerHTML = '';
  if (!Array.isArray(items) || !items.length) { box.append(el('div', {class: 'hint'}, 'Nothing yet.')); return; }
  items.forEach(it => {
    const v = el('video', {muted: '', preload: 'metadata', playsinline: '', tabindex: '-1'});
    v.muted = true; v.src = '/video/' + encodeURIComponent(it.name) + '#t=0.6';
    const th = el('div', {class: 'th', role: 'button', tabindex: '0', 'aria-label': 'Play ' + it.title}, v);
    th.onclick = () => show(it.name, it.title, it.desc || '');
    th.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); th.onclick(); } };
    const del = el('div', {class: 'd'});
    const idle = () => { del.innerHTML = ''; del.append(miniBtn('Delete…', ask, false, 'Delete video')); };
    const ask = () => { del.innerHTML = ''; del.append(miniBtn('Delete', () => removeVideo(it.name)), miniBtn('Keep', idle)); del.firstChild.classList.add('danger'); };
    idle();
    box.append(el('div', {class: 'vcard'}, th, el('div', {class: 't'}, it.title), el('div', {class: 'w'}, it.when || ''), del));
  });
}
$('reveal').onclick = async () => {
  if (!current) return;
  const res = await api('/api/reveal', {name: current.name});
  if (res.error) setError(res.error);
};
$('copyTitle').onclick = () => navigator.clipboard.writeText(current.title);
$('copyDesc').onclick = () => navigator.clipboard.writeText(current.desc);

// ------------------------------------------------------------ series
$('planSeries').onclick = async () => {
  const topic = $('stopic').value.trim();
  if (!topic) { setError('Type what the series is about first.'); return; }
  const res = await api('/api/series/plan', {topic, parts: +$('sparts').value, story_format: $('sformat2').value,
    tone: $('stone').value, bible: $('sbible').value.trim()});
  if (res.error) { setError(res.error); return; }
  watch(res.id, 'Planning the series...');
};

async function loadSeries() {
  seriesItems = ((await api('/api/series')).items) || [];
  const box = $('seriesList'); box.innerHTML = '';
  if (!seriesItems.length) { box.append(el('div', {class: 'hint'}, 'No series yet. Plan one above.')); return; }
  seriesItems.forEach(s => {
    const made = s.parts.filter(p => p.video).length;
    const fmt = opts && opts.formats ? (opts.formats.find(f => f.key === s.format) || {}).name : s.format;
    const card = el('div', {class: 'series'},
      el('div', {class: 'sh'}, el('div', {}, el('h3', {style: 'margin:0'}, s.title),
        el('div', {class: 'hint', style: 'margin:0'}, `${fmt || ''} · ${made} of ${s.parts.length} made`)),
        el('span', {class: 'acts'}, miniBtn('Save changes', () => saveSeries(s)), askDelete(s))));
    s.parts.forEach((p, i) => {
      const t = el('input', {'aria-label': 'Part ' + (i + 1) + ' title'}); t.value = p.title; t.oninput = () => p.title = t.value;
      const d = el('textarea', {'aria-label': 'Part ' + (i + 1) + ' idea'}); d.value = p.idea; d.oninput = () => p.idea = d.value;
      const mk = el('button', {class: 'ghost partbtn', type: 'button'}, p.video ? 'Remake' : 'Make part');
      mk.onclick = () => makePart(s, i);
      const acts = el('div', {class: 'pa'}, mk);
      if (p.video) {
        const w = el('button', {class: 'ghost', type: 'button'}, 'Watch');
        w.onclick = () => show(p.video, p.title, p.idea);
        acts.append(w);
      }
      card.append(el('div', {class: 'part' + (p.video ? ' made' : '')}, el('div', {class: 'n'}, p.video ? '✓' : String(i + 1)),
        el('div', {}, t, d, p.teaser ? el('div', {class: 'hint'}, 'Teaser: ' + p.teaser) : ''), acts));
    });
    box.append(card);
  });
}
function askDelete(s) {
  const wrap = el('span', {class: 'acts'});
  const idle = () => { wrap.innerHTML = ''; wrap.append(miniBtn('Delete…', ask, false, 'Delete series')); };
  const ask = () => { wrap.innerHTML = ''; const y = miniBtn('Delete', async () => { await api('/api/series/delete', {id: s.id}); loadSeries(); });
    y.classList.add('danger'); wrap.append(y, miniBtn('Keep', idle)); };
  idle(); return wrap;
}
async function saveSeries(s) {
  const res = await api('/api/series/save', {series: s});
  setError(res.error || '');
  if (!res.error) loadSeries();
}
async function makePart(s, i) {
  await api('/api/series/save', {series: s}); // keep any edits to this part's idea
  const res = await api('/api/generate', Object.assign({idea: s.parts[i].idea, series_id: s.id, part_index: i}, lookBody()));
  if (res.error) { setError(res.error); return; }
  watch(res.id, 'Making part ' + (i + 1) + ' of ' + s.parts.length + '...', [{label: 'Write the script', state: 'active'}]);
  waitingPhone();
  window.scrollTo({top: 0, behavior: 'smooth'});
}

// ------------------------------------------------------------ start
(async () => {
  await loadOptions();
  await loadSettings();
  loadUnfinished(); loadVideos();
  const h = (location.hash || '').slice(1);
  openTab(['create', 'series', 'library', 'settings'].includes(h) ? h : 'create');
})();
</script>
</body>
</html>
"""
