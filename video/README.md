# Bharat-Bot explainer videos (Remotion 4.0.535)

React-based, programmatic video. Takes the Blender simulation renders in
`public/clips/` plus a per-frame telemetry JSON in `src/data/` and composes the
final explainer (HUD overlays, captions, voiceover, transitions).

**Full guide with working snippets: [`../research/remotion.md`](../research/remotion.md)**

## Commands (run inside `video/`)

```powershell
npm run dev                                  # Remotion Studio -> http://localhost:3000
npx remotion render Main out/test.mp4        # placeholder title card, 1920x1080 @ 30 fps, 5 s
npx remotion still ClipHud out/f75.png --frame=75     # one PNG, handy for visual checks
npm run fixtures                             # re-render public/_fixtures/test-clip.mp4 (fake clip)
npm run lint                                 # eslint + tsc
```

## Layout

| Path | What |
| --- | --- |
| `src/Root.tsx` | Registers compositions. `Main` is the real entry; `Cookbook/*` are working references (safe to delete). |
| `src/Main.tsx` | Placeholder title card. |
| `src/components/` | `Hud` (telemetry overlay), `LowerThird`, `Subtitles`. |
| `src/lib/` | `telemetry.ts` (data contract + lookups), `media.ts` (Mediabunny duration/size), `voiceover.ts`, `audio.ts` (ducking). |
| `src/data/` | Telemetry JSON from the sim (`*.telemetry.json`) + `index.ts` typed loader. |
| `src/cookbook/` | Clip + HUD, split screen, Series / TransitionSeries, captions, audio mix, voiceover, robot-cam effects. |
| `src/fixtures/` | `FixtureClip`: a fake "Blender clip" with a burned-in frame counter for sync tests. |
| `public/clips/` | Drop rendered Blender MP4s here (reference with `staticFile("clips/name.mp4")`). |
| `public/_fixtures/` | Generated test media (clip, tones, SAPI voice lines). |
| `scripts/` | `make-sample-telemetry.mjs`, `telemetry_writer.py` (stdlib-only writer for the sim). |
| `out/` | Render output (git-ignored). |

Remotion needs every `@remotion/*` package on the exact same version (all pinned to 4.0.535).
Upgrade with `npx remotion upgrade`.
