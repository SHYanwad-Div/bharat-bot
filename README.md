# Bharat-Bot: a delivery robot built for Indian streets (simulation + film)

US sidewalk robots (Starship, Serve, Kiwibot) work because sidewalks there are smooth. This project simulates what
happens on an Indian street — potholes, waterlogging, a 12 cm speed breaker, a pack of street dogs, a cow in the lane
with an auto-rickshaw behind it, a thief, and the delivery itself — first with a standard US-style robot (it fails three
ways), then with **Bharat-Bot**, an India-adapted design that handles all of it. Everything is rendered in Blender 5.2
and cut into an explainer film with Remotion.

**Project page:** <https://shyanwad-div.github.io/bharat-bot/> (source: [`docs/index.html`](docs/index.html)): the
problem, the three failures, the 200-street results, the safety rule, the cost and the limits on one page, with the film
embedded.

**3D digital twin:** <https://shyanwad-div.github.io/bharat-bot/twin/> (source: [`docs/twin/`](docs/twin/)): the same
street and the same runs in the browser. Pick the full delivery or one test (potholes, dogs, theft), switch between the
standard robot and Bharat-Bot, watch the control room log every SENSE → AI → SAFETY → ACT decision, scrub through time,
and click the robot to take it apart into labelled parts. With sound: motors, tyres, the auto-rickshaw, barking dogs,
the siren, the film's tanpura drone underneath, and a voice (the visitor's own text-to-speech) that reads each moment
in plain English. three.js, no build step, about 6 MB.

## Outputs

The videos and Blender files are too big for git. The MP4s go in the GitHub Release (tag `v1.0`) instead; `blend/`,
`renders/`, `recordings/` and the downloaded textures and models (`assets/`, sources in `assets/CREDITS.md`) stay
local and can be rebuilt with the commands under *Re-run everything*.

| File | What |
|---|---|
| `videos/bharat_bot_film.mp4` | the explainer film, 2:53, 1080p (title → US vs India → 3 baseline failures → Bharat-Bot's full run with the control-room HUD → results → safety design → cost in ₹ → honest limits) |
| `videos/bharat_bot_highlights.mp4` | 57-second cut for sharing: the problem, Bharat-Bot's five big moments, the scorecard |
| `videos/bharat_full.mp4` | Bharat-Bot's full 89 s run, raw render (1280×720, 30 fps) |
| `videos/baseline_pothole.mp4`, `baseline_dogs.mp4`, `baseline_theft.mp4` | the standard robot failing: stuck, blocked, stolen |
| `videos/us_sidewalk.mp4` | the standard robot on a smooth US sidewalk (for contrast) |
| `blend/*.blend` | the five Blender scenes, fully animated — open them and press play |
| `research/india-delivery-robots.md` | sourced research (66 sources): Indian street data, real robots, what works, numbers, top-10 priorities |
| `research/evaluation.md` | batch evaluation: success rates with 95 % confidence intervals over 200 random streets per scenario, a steel-manned baseline, an ablation of each Bharat-Bot feature, and where it still fails (`video/src/data/evaluation.json` has the same numbers for a results chart) |

## How it works

```
sim/world.py         street layout + terrain height function (potholes, water, speed breaker) — shared by sim and Blender
sim/simulate.py      the simulation: lattice path planner (dynamic programming), rocker-bogie vs rigid-chassis
                     terrain kinematics, dogs (pack alert, chase, agitation, retreat), thief, cow, auto-rickshaw,
                     customer; every decision logged as SENSE → AI → SAFETY → ACT (GH-01's "AI suggests, safety
                     decides, hardware protects" rule)
sim/build_scene.py   builds one shot in Blender from a simulation run: street, characters, HUD effects, cameras
sim/characters.py    procedural Bharat-Bot / baseline robot / people / auto-rickshaw + animated Quaternius dogs and cow
sim/environment.py   Indian street (Poly Haven textures, shops, poles and wires, tea stall, gate) and a US suburb
sim/render_shot.py   resumable frame renderer; sim/render_queue.ps1 renders every shot and encodes MP4s
sim/export_telemetry.py   per-frame telemetry JSON for the film's HUD (video/src/data/*.telemetry.json)
sim/evaluate.py      batch evaluation: 200 seeded random streets per scenario (simulate.Sim(name, seed=n)), both robots
                     plus a steel-manned baseline, 95 % CIs and a one-feature-at-a-time ablation → research/evaluation.md
                     and video/src/data/evaluation.json; sim/test_seeded.py checks the film's runs stay byte-identical
sim/screen_record.py records Blender's own window playing the sim (needs an unlocked screen for --mode desktop)
sim/export_twin.py   every agent's pose on every frame of the 4 film runs (+ the standard robot on the full route), the
                     same event log as the film HUD, the street's potholes → docs/twin/data; web-size textures
sim/export_twin_models.py   Blender script: the film's street, robots (Bharat-Bot split into labelled parts), people
                     and auto-rickshaw as Draco GLBs, the Quaternius animals trimmed to the clips used, the sky → docs/twin/models
sim/export_twin_audio.py    the twin's sounds, synthesised with numpy (barks, motors, engine, street, chimes; the film's
                     tanpura drone and siren from video/scripts/make_audio.py) → docs/twin/audio
video/               Remotion project: src/bharat/* is the film (HUD, failure overlays, scenes); scripts/make_audio.py
                     synthesises the tanpura-drone music and sound effects
docs/twin/           the digital twin: js/terrain.js rebuilds the road surface with world.py's own arithmetic (checked
                     against Python on load), js/actors.js poses everything the way build_scene.py keys it in Blender
```

## Re-run everything

```powershell
python sim/simulate.py all                                   # run the 4 simulations, print event logs (≈25 s)
$B = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
& $B -b --python sim/build_scene.py -- --shot bharat_full --save blend/bharat_full.blend   # build a shot (≈20 s)
pwsh -File sim/render_queue.ps1                              # render all 5 shots at 720p and encode MP4s (≈2.5 h)
python sim/export_telemetry.py                               # HUD data for the film
python sim/evaluate.py                                       # 200 random streets per scenario and robot (≈5 min)
python video/scripts/make_audio.py                           # music + sound effects -> video/public/audio
cd video; npm install; npx remotion render BharatBotFilm ../videos/bharat_bot_film.mp4   # the film (≈10 min)
python sim/export_twin.py                                    # 3D twin: poses, events, street, textures (≈20 s)
& $B -b --factory-startup --python sim/export_twin_models.py # 3D twin: models and sky (≈20 s)
python sim/export_twin_audio.py                              # 3D twin: sounds (≈15 s, needs ffmpeg)
python -m http.server 8765 --directory docs                  # then open http://localhost:8765/twin/
```

The film reads the five clips from `video/public/clips/`: `render_queue.ps1` copies them there, or download them from
the Release. Preview and tweak the film interactively with `cd video; npm run dev` (Remotion Studio).

Screen recording of Blender playing the simulation (the screen must be unlocked and visible):

```powershell
& $B blend/bharat_full.blend --python sim/screen_record.py -- --mode desktop --out recordings/blender_screen.mp4
```

## Honest limits

The film shows one fixed run per scenario; `research/evaluation.md` scores 200 random streets per scenario with
confidence intervals and an ablation, but it is all simulation, not field data. Dog behaviour follows expert guidance
(freeze, don't flee) but has never been tested with a robot; ultrasonic repellers show no proven effect, so Bharat-Bot
doesn't use them. No sidewalk robot publishes a wading depth. Costs are paper estimates. See
`research/india-delivery-robots.md` §4 for what is still missing (above all, calibration on a real street).

## Credits

Textures and sky: Poly Haven (CC0). Dogs and cow: Quaternius via Poly Pizza (CC0). Everything else is procedural. Authors
and licences of every asset used: `assets/CREDITS.md`; the twin ships web-size copies of the CC0 files in
`docs/twin/models/` and loads [three.js](https://threejs.org) (MIT) from jsDelivr.
Inspired by [GH-01](https://github.com/sumithshridhar/gh01-twin), Sumith Shridhar's greenhouse digital twin.

## Licence

The code and documents in this repository are MIT-licensed (see `LICENSE`). The downloaded assets keep their own
licences; everything used on screen is CC0 (`assets/CREDITS.md`).
