# Remotion for the Bharat-Bot explainer videos

Everything below was run and checked on this machine (Windows 11, Node 24.16, npm 9.5, i7-1355U / Iris Xe / 16 GB) unless marked **untested**.

**Status:** Remotion **4.0.535** (latest on npm) is set up in `video/`, the 12 official Remotion Agent Skills are installed project-scoped in `.claude/skills/`, and `npx remotion render Main out/test.mp4` works (1920x1080, 30 fps, 150 frames, H.264, 1.4 MB).

```powershell
cd C:\Users\dshan\robot_simulation\video
npm run dev                              # Studio, http://localhost:3000
npx remotion render Main out/test.mp4    # placeholder title card
```

---

## 1. What was installed (exact commands)

### 1.1 Claude skills (official, project-scoped)

Sources: <https://www.remotion.dev/docs/ai/claude-code>, <https://www.remotion.dev/docs/ai/skills>, <https://github.com/remotion-dev/skills>. Remotion's own CLI (`npx remotion skills add`) just runs `npx skills@1.7.0 add remotion-dev/skills --yes`. I ran that underlying command from the **project root** so the skills land in the root `.claude/skills/` and not in `video/.claude`:

```powershell
cd C:\Users\dshan\robot_simulation
npx --yes --loglevel=error skills@1.7.0 add remotion-dev/skills --agent claude-code --skill '*' --copy --yes
```

`--copy` writes real folders (no symlinks, which are fragile on Windows). Result: `.claude/skills/<name>/SKILL.md` for all 12 skills, plus `skills-lock.json` at the project root (the installer's own file, used by `npx remotion skills update` / `npx skills@1.7.0 update`):

| Skill | Use |
| --- | --- |
| `remotion-best-practices` | **Router, load this first.** Bundles reference copies of all the others (`remotion-*/REFERENCE.md`). |
| `remotion-markup` | Compositions, animation, media, audio, fonts, effects, transitions, `calculateMetadata`, zod params (the big one: ~30 reference .md files). |
| `remotion-create` / `remotion-studio` / `remotion-render` | Scaffold, open Studio, render (incl. transparent video). |
| `remotion-captions` | `Caption` type, SRT import, Whisper transcription, display. |
| `remotion-multimedia` | Mediabunny: duration / dimensions of media files. |
| `remotion-docs` | Search docs via Algolia, fetch any docs page as Markdown (`<url>.md`). |
| `remotion-upgrade`, `remotion-interactivity`, `remotion-maps`, `remotion-saas` | Upgrades, Studio-editable markup, map flyovers, Player/Lambda apps (mostly irrelevant here). |

Review notes: I read the router, markup, create, render, studio, docs and captions skills. Content is plain guidance; no scripts run on install. The installer's scan flagged only `remotion-docs` as Snyk "High Risk": it embeds Remotion's public, search-only Algolia key and tells the agent to fetch docs pages from remotion.dev. Treat fetched docs as data.

**Use in Claude Code:** skills are discovered at session start. `.claude/skills/` did not exist when the main session started, so **restart that session once** (or open a new one), then ask for `remotion-best-practices`. The skills are written for an interactive user ("open Studio first, don't render unless asked"). For this pipeline say explicitly when to render, and verify visually with stills (`npx remotion still`).

### 1.2 Remotion project

```powershell
cd C:\Users\dshan\robot_simulation
npx --yes create-video@latest --yes --blank --no-tailwind video
```

That copied the blank template and ran `git init` (see 7.1), but its `npm i` died with `ERR_SOCKET_TIMEOUT`. I then added the packages below to `video/package.json` (exact versions, no `^`: Remotion requires identical versions for `remotion` and every `@remotion/*`) and installed:

```powershell
cd video
npm install --no-audit --no-fund --progress=false --fetch-retries=5 --fetch-retry-mintimeout=20000 --fetch-retry-maxtimeout=120000 --fetch-timeout=600000
```

That install "succeeded" but the earlier failure had left **truncated packages** (`node_modules\remotion` had 3 files; `npx remotion versions` crashed with `Cannot find module ...\@remotion\renderer\dist\index.js`). Fix that worked: delete and reinstall.

```powershell
cmd /c "rmdir /s /q node_modules"; Remove-Item package-lock.json; npm install   # same flags as above, 361 packages, ~1 min
```

Installed (`npx remotion versions` reports "All packages have the correct version"):

| Package | Version | Why |
| --- | --- | --- |
| `remotion`, `@remotion/cli` | 4.0.535 | core + CLI/Studio (Rspack bundler enabled in `remotion.config.ts`) |
| `@remotion/media` | 4.0.535 | **recommended `<Video>` / `<Audio>`** (Mediabunny + WebCodecs) |
| `mediabunny` | 1.61.3 | pinned to the version `@remotion/media` depends on; used for durations/dimensions |
| `@remotion/transitions` | 4.0.535 | `TransitionSeries`, fade/slide/wipe/... |
| `@remotion/google-fonts`, `@remotion/fonts` | 4.0.535 | Google fonts (needs internet) / local .woff2/.ttf |
| `@remotion/media-utils` | 4.0.535 | `getAudioData`, `visualizeAudio`, `useWindowedAudioData` (installed as requested, **untested**; Mediabunny covers duration/size) |
| `@remotion/shapes`, `@remotion/paths` | 4.0.535 | used in `Main` (radar rings, animated underline) |
| `@remotion/captions` | 4.0.535 | `Caption` type, `parseSrt`, `createTikTokStyleCaptions` |
| `@remotion/effects` | 4.0.535 | WebGL effects for `<Video effects>` (vignette, scanlines, ...) |
| `@remotion/layout-utils` | 4.0.535 | `fitText`, `measureText` |
| react / react-dom / typescript | 19.2.3 / 19.2.3 / 5.9.3 | from the template |

First `remotion render` downloads **Chrome Headless Shell 157.0.8080.0** (120 MB, from storage.googleapis.com) to `video/node_modules/.remotion/` (283 MB on disk). Needs internet once.

Remotion is free for individuals / teams of up to 3; companies need a license (<https://www.remotion.pro/license>).

---

## 2. Project map (`video/`)

```
src/index.ts, Root.tsx         registerRoot + all <Composition>s ("Main" first, then Cookbook/ and Fixtures/ folders)
src/Main.tsx                   placeholder title card (Rajdhani font, radar rings, tricolour strip)
src/theme.ts                   fonts (Rajdhani, JetBrains Mono) + colours + state/severity colours
src/components/Hud.tsx         telemetry-driven HUD: speed ring, state chip, battery, event toasts, mini-map
src/components/LowerThird.tsx, Subtitles.tsx
src/lib/telemetry.ts           Telemetry types, parseTelemetry(), time->index lookup, event windows
src/lib/media.ts               getMediaDurationInSeconds / getVideoDimensions (Mediabunny)
src/lib/voiceover.ts, audio.ts script-driven voiceover plan + captions, music ducking
src/data/                      *.telemetry.json from the sim + index.ts (typed loader)
src/cookbook/                  ClipHud, HudOnly, SplitSideBySide, SplitWipe, SeriesDemo, TransitionDemo,
                               FreeSequenceDemo, CaptionsLowerThird, RobotCam, AudioMix, VoiceoverCaptions
src/fixtures/FixtureClip.tsx   fake "Blender clip" with a burned-in SRC FRAME counter
public/clips/                  EMPTY on purpose: drop rendered Blender MP4s here
public/_fixtures/              generated test clip + audio (safe to delete with src/cookbook + src/fixtures)
scripts/                       make-sample-telemetry.mjs, telemetry_writer.py
```

Commands (all from `video/`):

```powershell
npm run dev                                               # Studio (--port=3123 if 3000 is busy)
npx remotion render Main out/test.mp4                     # video (overwrites by default)
npx remotion render ClipHud out/x.mp4 --props=props.json  # props MUST be a file on Windows shells
npx remotion still ClipHud out/f75.png --frame=75         # ONE png (render --frames=75 makes a folder of element-075.png)
npx remotion render Main out/frames --frames=0,60,120 --image-format=png   # several pngs
npm run fixtures            # re-render public/_fixtures/test-clip.mp4
npm run lint                # eslint + tsc
npx remotion ffmpeg ... / npx remotion ffprobe ...        # bundled binaries (see 6.4)
```

---

## 3. Practical guide

### 3.1 Ground rules
- Everything is a function of the frame: `useCurrentFrame()` + `interpolate()` / `spring()`. No CSS transitions/animations (they don't render).
- Inside a `<Sequence>` / `TransitionSeries.Sequence`, `useCurrentFrame()` restarts at 0 and `useVideoConfig().durationInFrames` is the sequence length. Put overlays in the **same** sequence as the clip they belong to.
- Timing props (`from`, `trimBefore`, `durationInFrames`, `premountFor`) are in **composition frames**: `trimBefore={2 * fps}` = skip 2 s.
- `staticFile("clips/pothole.mp4")` = file in `public/`, forward slashes, no spaces, exact case.
- Give timed media `premountFor={fps}` (the skills ask for this).

### 3.2 Embedding Blender clips: `<Video>` (@remotion/media) vs `<OffthreadVideo>`
Use `<Video>` from `@remotion/media` by default (docs: recommended, fastest, frame-exact). Verified here: an H.264 MP4 decodes on the fast path in Chrome Headless Shell **and** in Studio.

```tsx
import { Video } from "@remotion/media";
import { staticFile, useVideoConfig } from "remotion";

const { fps } = useVideoConfig();
<Video
  src={staticFile("clips/pothole.mp4")}
  trimBefore={2 * fps}          // skip first 2 s of the clip
  durationInFrames={5 * fps}    // then show 5 s (omit = to the end)
  playbackRate={1}              // 2 = double speed (audio pitch changes), no reverse
  muted                         // Blender clips have no audio anyway
  objectFit="cover"             // use the prop, CSS object-fit is NOT supported here
  premountFor={fps}
  style={{ width: "100%", height: "100%" }}   // style goes to the <canvas>
/>
```

| | `<Video>` `@remotion/media` | `<OffthreadVideo>` `remotion` |
| --- | --- | --- |
| Engine | Mediabunny + WebCodecs | Rust + ffmpeg frame extraction |
| Speed (docs) | fastest | fast |
| Codecs | H.264, VP8/9, AAC, MP3, Opus, FLAC, Vorbis | also H.265, AV1, ProRes, AVI, FLV |
| `loop` | yes | no |
| Needs CORS for remote URLs | yes (not for `staticFile`) | no |

Verified behaviour with an H.265 file: `<Video>` logs `[@remotion/media] Cannot decode ..., falling back to <OffthreadVideo>` and still renders; with `disallowFallbackToOffthreadVideo` the render fails with `Cannot decode`. `src/cookbook/ClipHud.tsx` exposes both (`engine="offthread"`, `strict`) so a bad clip can be switched without rewriting anything. Simple swap: `<OffthreadVideo src={staticFile(..)} style={{width:"100%",height:"100%",objectFit:"cover"}} muted />`.

### 3.3 Sequence / Series / TransitionSeries
```tsx
// Free layout: items may overlap, `from` is the absolute start
<Sequence from={30} durationInFrames={60} premountFor={fps} name="Badge"><Badge /></Sequence>

// Back to back; offset shifts a scene (negative = overlap). 45 + 60 + 45 - 10 = 140 frames
<Series>
  <Series.Sequence durationInFrames={45} premountFor={fps}><Intro /></Series.Sequence>
  <Series.Sequence durationInFrames={60} offset={-10} premountFor={fps}><ClipScene /></Series.Sequence>
  <Series.Sequence durationInFrames={45} premountFor={fps}><Outro /></Series.Sequence>
</Series>

// Transitions (verified, incl. a <Video> scene mid-fade)
import { linearTiming, springTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";   // also wipe, flip, clock-wipe, iris, ...
const t1 = linearTiming({ durationInFrames: 15 });
const t2 = springTiming({ config: { damping: 200 }, durationInFrames: 20 });
<TransitionSeries>
  <TransitionSeries.Sequence durationInFrames={45} premountFor={fps}><Intro /></TransitionSeries.Sequence>
  <TransitionSeries.Transition presentation={fade()} timing={t1} />
  <TransitionSeries.Sequence durationInFrames={60} premountFor={fps}><ClipScene /></TransitionSeries.Sequence>
  <TransitionSeries.Transition presentation={slide({ direction: "from-right" })} timing={t2} />
  <TransitionSeries.Sequence durationInFrames={45} premountFor={fps}><Outro /></TransitionSeries.Sequence>
</TransitionSeries>
// Transitions OVERLAP their neighbours: total = 45+60+45 - 15 - 20 = 115 frames
// (use t1.getDurationInFrames({ fps }) to compute it; TransitionSeries.Overlay does not shorten the timeline)
```
Full working versions: `src/cookbook/Sequencing.tsx`.

### 3.4 Frame-synced, data-driven HUD from the sim's telemetry
**Contract** (`src/lib/telemetry.ts`): one JSON per rendered clip, `frames[i]` = i-th frame of the MP4 (0-based, same order). Sim fps is stored, so composition fps may differ.

```json
{ "version": 1, "scene": "pothole", "fps": 30, "frameCount": 150,
  "frames": [ { "f": 0, "t": 0, "speed": 0, "state": "IDLE", "x": 0, "y": 0, "heading": 0, "battery": 0.82 } ],
  "events": [ { "frame": 45, "durationFrames": 45, "type": "pothole_detected", "label": "Pothole 3 m ahead", "severity": "warn" } ] }
```
`x, y, heading, battery` are optional (the HUD hides what is missing). `state` is free text (colours for IDLE, CRUISE, SLOW, AVOID, STOP, WAIT, REROUTE, ALERT live in `theme.ts`); `severity` is `info | warn | alert`. A sample is in `src/data/sample-pothole.telemetry.json`.

**Writing it from the sim** (`scripts/telemetry_writer.py`, stdlib only, so it runs inside Blender's Python; unit-tested outside Blender):
```python
from telemetry_writer import TelemetryWriter
tw = TelemetryWriter(scene="pothole", fps=30)
for frame in rendered_frames:                       # once per RENDERED frame, in order (index is implicit)
    tw.log(speed=1.4, state="CRUISE", x=bot.x, y=bot.y, heading=0.0, battery=0.82)
tw.event("pothole_detected", "Pothole 3 m ahead", severity="warn", frame=45)
tw.save(r"C:\Users\dshan\robot_simulation\video\src\data\pothole.telemetry.json")
```
Then add it to `src/data/index.ts` (`parseTelemetry` throws a readable error on malformed files).

**Using it** (inside the same Sequence as the clip; mirror the clip's `trimBefore` / `playbackRate`):
```tsx
import { Hud } from "./components/Hud";
import { telemetry } from "./data";
<Sequence durationInFrames={150}>
  <Video src={staticFile("clips/pothole.mp4")} trimBefore={0} objectFit="cover" style={{ width: "100%", height: "100%" }} />
  <Hud telemetry={telemetry.samplePothole} trimBefore={0} playbackRate={1} />
</Sequence>
```
The lookup is time based: `seconds = (trimBefore + frame * playbackRate) / fps; index = round(seconds * telemetry.fps)`. **Sync verified**: `ClipHud` stills show the clip's burned-in `SRC FRAME 045` next to the HUD's `TELEMETRY f=045` (also at 75), with the HUD (`debug`) printing the index. `HudOnly` renders the HUD alone with transparency (VP9 + alpha, `ALPHA_MODE=1` verified) for other editors. The HUD scales itself to the composition width (designed at 1920x1080).

Size limits: a static `import` of the JSON bundles it (fine for tens of thousands of frames). For huge files `fetch(staticFile("telemetry/x.json"))` inside `calculateMetadata` and return it in `props`.

### 3.5 Lower thirds, subtitles, voiceover captions
```tsx
<Sequence from={Math.round(0.5 * fps)} durationInFrames={3 * fps} premountFor={fps}>
  <LowerThird title="Bharat-Bot" subtitle="Pothole avoidance" />   {/* springs in, fades out at the end */}
</Sequence>
<Sequence><Subtitles captions={captions} /></Sequence>          {/* cue times are ms from this Sequence's start */}
```
SRT -> captions (works, verified): `import { parseSrt } from "@remotion/captions"; const { captions } = parseSrt({ input: srtText });` Captions are whitespace sensitive.

**Script-driven narration (recommended, no speech recognition):** one audio file per sentence, measure each with Mediabunny, lay them out back to back; captions fall out of the same numbers (`src/lib/voiceover.ts`, `src/cookbook/VoiceoverCaptions.tsx`). Verified: 3 lines -> 452 frames, voices start at the planned frames, captions switch on time, clip loops, music ducks.
```tsx
export const calculateMetadata: CalculateMetadataFunction<Props> = async ({ props }) => {
  const plan = await planVoiceover(props.lines, 30);          // { lines[{startFrame,durationInFrames}], captions, totalFrames }
  return { durationInFrames: plan.totalFrames, props: { ...props, plan } };
};
// component: plan.lines.map(l => <Audio key={l.src} src={staticFile(l.src)} from={l.startFrame} premountFor={fps} />)
//            <Subtitles captions={plan.captions} />
```
**Free voices on this PC:** Windows SAPI works from *Windows PowerShell 5.1* (`powershell.exe`, not pwsh): installed voices are David, Hazel (en-GB), Zira (en-US) and Heami (ko-KR); no Indian-English voice. The fixtures were made with:
```powershell
Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice('Microsoft Zira Desktop'); $s.SetOutputToWaveFile("$PWD\vo-1.wav"); $s.Speak('Your sentence.'); $s.Dispose()
```
Better voices: ElevenLabs (see `remotion-markup/voiceover.md`, needs `ELEVENLABS_API_KEY`) or any TTS that writes a file. For word-level captions from existing audio: `remotion-captions/transcribe-captions.md` (Whisper, **untested**; needs a WebGPU-capable GPU).

### 3.6 Split screen
```tsx
// side by side: two 16:9 panels (888x500) with labels and a VS badge
<Video src={staticFile(leftClip)}  trimBefore={0}  objectFit="cover" muted style={{ width: "100%", height: "100%" }} />   // in a div with overflow:hidden, borderRadius
<Video src={staticFile(rightClip)} trimBefore={30} objectFit="cover" muted style={{ width: "100%", height: "100%" }} />

// A/B wipe: both full frame, reveal the left one with clip-path while the divider moves
<AbsoluteFill style={{ clipPath: `inset(0 ${width - split}px 0 0)` }}><Video src={staticFile(leftClip)} .../></AbsoluteFill>
```
Different `trimBefore` per panel lets you start both at the interesting moment (verified: panels show source frames 100 and 130). `src/cookbook/SplitScreen.tsx` has both.

### 3.7 Audio: music, SFX, voiceover
```tsx
import { Audio } from "@remotion/media";
<Audio src={staticFile("audio/music.mp3")} loop volume={duckingVolume(frame, voStart, voEnd)} premountFor={fps} />  // loops until the comp ends
<Audio src={staticFile("audio/vo/scene1.wav")} from={voStart} premountFor={fps} />                                 // `from` delays the start
<Audio src={staticFile("audio/sfx/ping.wav")} from={telemetryEventFrameInCompFrames} volume={0.8} />               // pin SFX to events
```
`duckingVolume` (`src/lib/audio.ts`) is a plain `interpolate` that dips the music under speech. Verified by rendering `--codec=wav` and measuring RMS: ping at 0.5 s, whoosh at 3.0 s, voice from 1.0 s, music loops past 8 s, MP4 output has AAC 48 kHz stereo. Per-frame numeric `volume` works; avoid the callback form. Mute everything with `--muted`; loudness: `npx remotion ffmpeg -i in.mp4 -af loudnorm out.mp4` (the filter is in the bundled build).

### 3.8 `calculateMetadata` (dynamic duration / props)
Runs in the browser before render; **no `fps` argument and no hooks**, so keep a shared `FPS` constant next to the registration. Returns any of `durationInFrames, width, height, fps, props, defaultOutName, defaultCodec, ...`.
```tsx
// duration = length of the MP4 (src/cookbook/ClipHud.tsx, verified: Studio showed 0:05.00)
export const calculateClipHudMetadata: CalculateMetadataFunction<ClipHudProps> = async ({ props }) => {
  const seconds = await getMediaDurationInSeconds(staticFile(props.clip));   // src/lib/media.ts, Mediabunny
  return { durationInFrames: Math.round(seconds * 30) };
};
// duration from telemetry + transparent export defaults (src/cookbook/ClipHud.tsx: HudOnly)
return { durationInFrames: telemetryDurationInFrames(props.telemetry, 30),
         defaultCodec: "vp9", defaultVideoImageFormat: "png", defaultPixelFormat: "yuva420p" };
```
`getVideoDimensions(src)` (same file) lets a composition match a clip's size. Studio shows "Can't save default props" for comps whose `defaultProps` reference imported data: harmless.

### 3.9 Look and feel
- **Fonts:** `@remotion/google-fonts/Rajdhani` etc. fetch from Google at every render (internet needed). Offline-proof, verified: `import { loadFont } from "@remotion/fonts"; loadFont({ family: "MyFont", url: staticFile("fonts/MyFont.woff2") });` at module scope (blocks rendering until loaded).
- **Robot-cam look:** `<Video effects={[vignette({ amount: 0.75 }), scanlines({ amount: 0.2, offset: frame * 0.5 })]} />` from `@remotion/effects/vignette|scanlines|...` (`src/cookbook/RobotCam.tsx`). WebGL2 effects rendered correctly with the default GL backend and with `--gl=angle`.
- `fitText` (`@remotion/layout-utils`) fits a label to a width: `fitText({ text, withinWidth: 560, fontFamily, fontWeight: 600 }).fontSize` (verified 36.7 px for a long toast label; load fonts first).

---

## 4. Rendering on this laptop (measured)
150-frame 1080p renders, pre-bundled, warm:

| Run | Time |
| --- | --- |
| `Main`, default concurrency (6) / 4 / 3 / 2 | 24.7 / 25.2 / 26.0 / 26.1 s |
| `Main --gl=angle` | 23.3 s |
| `ClipHud` `<Video>` (default / `--concurrency=3`) | 26.6 / 25.7 s |
| `ClipHud` `<OffthreadVideo>` | 27.6 s |

Cost model: about **12 s fixed start-up + ~0.1 s per frame** (about 10 fps). A 60 s video at 30 fps is roughly 3.5 min, 5 min is roughly 15 min. Concurrency barely matters here, so use `--concurrency=3` when Blender or a browser is open. First render ever: 104 s (includes the 120 MB browser download). Bundling takes about 10 s per render; `public/` is copied each time (a 300 MB file added only ~0.6 s).

Iterate with Studio or `npx remotion still`; render full MP4s only when needed. Do not render in parallel with a Blender render.

---

## 5. Windows pitfalls (all hit or verified here)
1. **Flaky `npm install` leaves broken packages** (section 1.2). Symptom: `Cannot find module ...dist\index.js`. Fix: `cmd /c "rmdir /s /q node_modules"`, delete `package-lock.json`, reinstall with the retry flags.
2. **`--props` must be a file** (`--props=out/props.json`); inline JSON quoting breaks in PowerShell/cmd.
3. **`--frames=75` writes an image-sequence folder** (`out/x/element-075.png`); use `npx remotion still ... --frame=75` for one PNG.
4. **Remotion's bundled ffmpeg is minimal** (`--disable-filters`): no `fps`, `crop`, `overlay`, `drawtext`, no `gdigrab` screen capture. It has libx264/x265, aac, prores_ks, vp8/9, scale, concat, volume, loudnorm, silencedetect. Use the winget ffmpeg for anything else. Constant-frame-rate fix that works in the bundled one: `npx remotion ffmpeg -i in.mp4 -r 30 -fps_mode cfr -c:v libx264 -pix_fmt yuv420p -crf 16 -g 30 -movflags +faststart out.mp4`.
5. **Port 3000 busy** -> `npx remotion studio --port=3123`. Kill a stray Studio with `taskkill /PID <pid> /T /F` (it is an npx + 2 node processes tree).
6. First render needs internet (Chrome Headless Shell). Behind a proxy use `--browser-executable`.
7. `staticFile()` is case-sensitive on Linux/Lambda although Windows is not; avoid spaces and non-ASCII in clip names.
8. Several Node versions are on PATH (nvm v16/v20 plus Program Files v24). `node --version` here is v24.16; Remotion 4 works with it. If `npx` behaves oddly, check `where.exe node`.
9. Studio and Chrome use the iGPU/CPU; close Blender renders first.
10. Output is full-range H.264 (`ffprobe` shows `yuvj420p`), normal for Remotion's JPEG frame pipeline.

---

## 6. Blender -> Remotion hand-off checklist
1. **Frame-exact beats screen capture.** Render frames (or Viewport Render Animation) so the telemetry has exactly one row per frame. Screen recordings drift and are often variable frame rate; if you must, normalise (item 4 above) and resample the telemetry to the recording's frames.
2. Render at the **composition fps** (30) so no frames are duplicated; a 24 fps clip in a 30 fps comp judders. Telemetry `fps` must match the clip.
3. Encode **H.264, yuv420p, constant frame rate**, short GOP (about 1 s), `+faststart`, no audio: `ffmpeg -framerate 30 -i frame_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 16 -g 30 -movflags +faststart clip.mp4` (PNG sequence -> MP4 is the safest path; **untested with real Blender output**). Keep H.264: HEVC/ProRes force the slower OffthreadVideo fallback.
4. Drop the file in `video/public/clips/`, the JSON in `video/src/data/`, register the telemetry in `src/data/index.ts`, then copy `ClipHud` (clip + HUD) as your scene component.
5. Check sync once with a burned-in frame number (`FixtureClip` + `ClipHud` with `debug`), then render stills at event frames before committing to a long render.
6. Keep `public/clips` lean (CRF 16-18 MP4s); render and bundle copy the whole `public/` folder.

## 7. Notes and loose ends
1. `video/.git` exists: `create-video` ran `git init` and made one commit ("Create new Remotion video"). The project root is not a repo; delete `video\.git` before running `git init` at the root, or you get an embedded-repo warning.
2. `skills-lock.json` at the project root is the skills installer's lockfile; keep it for `npx remotion skills update`.
3. `src/cookbook`, `src/fixtures` and `public/_fixtures` are reference material and test media. Delete them freely once the real scenes exist (also remove their `<Composition>`s in `Root.tsx`).
4. Not tested: real Blender clips, screen-recording sync, Whisper transcription, `@remotion/media-utils` audio visualisation, Lambda/distributed rendering.

## 8. Sources
- <https://www.remotion.dev/docs/ai/claude-code>, <https://www.remotion.dev/docs/ai/skills>, <https://www.remotion.dev/docs/cli/skills>, <https://www.remotion.dev/docs/cli/create-video>
- <https://github.com/remotion-dev/skills> (installed skill text is the primary reference: `.claude/skills/remotion-markup/*.md`)
- <https://www.remotion.dev/docs/media/video>, <https://www.remotion.dev/docs/video-tags>, <https://www.remotion.dev/docs/offthreadvideo>
- Any docs page as Markdown: append `.md` to the URL, e.g. <https://www.remotion.dev/docs/sequence.md>
