# Blender tooling, Blender 5.x scripting notes and CC0 assets (Bharat-Bot street sim)

Everything below was checked on **Blender 5.2.2 LTS** (Python 3.13.13, installed at
`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`, not on PATH) unless marked *(docs only)*.
Scene convention: 1 unit = 1 m, Z up, road along +X. Files live under `assets/` (index: `assets/asset_index.json`,
licences: `assets/CREDITS.md`, contact sheets: `assets/_previews/sheet_*.png`).

Quick start:

```bash
BL="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
"$BL" -b --factory-startup --python-exit-code 1 --python sim/build_scene.py -- args   # run a script headless
"$BL" -b scene.blend -a                                                              # render the animation
"$BL" -b --factory-startup --python assets/tools/blender5_smoke_test.py -- OUT_DIR 48 960x540   # API + asset smoke test
python -I assets/tools/inspect_glb.py assets/polypizza                               # inspect GLBs without Blender
```

---

## 1. Claude ↔ Blender tooling

### 1.1 What was set up

| Item | State |
|---|---|
| `.mcp.json` (project scope only) | one server `blender`: `uvx blender-mcp`, env `DISABLE_TELEMETRY=true`. No global Claude config touched. |
| Package | `blender-mcp` on PyPI is now a 1 KB shim (v2.0.0, same author Siddharth Ahuja, MIT) that depends on `mcp-for-blender` (2.1.9) and hands off to it. The GitHub repo moved to `ahujasid/mcp-for-blender`. `uvx blender-mcp` still works; handshake verified (initialize + tools/list OK, server "MCP for Blender"). Tools: `execute_blender_code`, `get_scene_info`, `look` (viewport screenshot), `get_addon_status`, `search_assets`, `import_asset`, `generate_3d`, `disable_telemetry`, `record_trajectory_feedback`. |
| Add-on | `assets/tools/blender_mcp.py` (pinned commit `7a0373ec`, SHA-256 in `assets/tools/README.md`). Blender 5.2 was already installed, so it was copied to `%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\` and **enabled in the user preferences** (`addon_utils.enable(..., default_set=True)` + `save_userpref`). The MCP server log confirms it sees the on-disk add-on ("current, protocol 13"). |
| Not done | A live GUI session (Claude ↔ running Blender) was **not** exercised: it needs a Blender window; the add-on refuses to serve in `blender -b`. Claude Code will ask you to approve the project MCP server on first use. |

Use: open Blender normally → N panel → **MCP for Blender** → *Connect to MCP server* (auto-starts by default, port 9876).
Full enabling steps, hardening (`BLENDER_MCP_SAFE_MODE=1`), update and removal: `assets/tools/README.md`.

Cautions: the socket is unauthenticated localhost and `execute_blender_code` runs arbitrary Python as you; the add-on makes a read-only GitHub
version check at startup (`BLENDERMCP_NO_UPDATE_CHECK=1` disables it); a tool reply may carry a one-off advert for the paid "Premium" plan (ignore).
For batch rendering prefer plain headless scripts; use MCP for interactive poking and screenshots.

### 1.2 Other tooling worth knowing (not installed)

| Option | Notes |
|---|---|
| Official **Blender Lab MCP server** (blender.org/lab/mcp-server) | First-party, Blender **5.1+**, add-on zip `mcp-1.0.3.zip` + `.mcpb` bundle; same "runs LLM code unguarded" warning. No Claude Code recipe on its page; projects.blender.org returned 403 to the fetcher, so setup steps were not read. |
| `TMHSDigital/Blender-Developer-Tools` (Claude Code plugin) | 20 skills / 11 rules for correct bpy on 5.2 LTS + 4.5 LTS (`porting-to-blender-5`, `slotted-actions-animation`, `headless-batch-scripting`, `procedural-materials-and-shaders`, ...). Install: `/plugin marketplace add TMHSDigital/Blender-Developer-Tools@plugin-dist` then `/plugin install blender-developer-tools@blender-developer-tools`. **Licence CC BY-NC-ND 4.0** (code snippets MIT): fine for private use, but do not copy/modify its text into the repo; install it as a plugin instead. Not installed: `.claude/skills/` belongs to another session and plugins are a global setting. |
| `HKUDS/CLI-Anything` Blender harness | Apache-2.0, JSON scene descriptions → render from a CLI. Different workflow from raw bpy; skip unless wanted. |
| `Impertio-Studio/...Claude-Skill-Package` | MIT but BIM/IFC focused; irrelevant here. |

---

## 2. Blender 5.x API changes that break older bpy scripts

Sources: developer.blender.org release notes 5.0 / 5.1 / 5.2 "Python API" + live checks on 5.2.2 (marked ✔ = executed here).
5.1 and 5.2 add very little that breaks (5.1: VSE strip property renames, Python 3.13; 5.2: Geometry-Nodes modifier inputs moved to
`modifier.properties.inputs.<id>.value`, automasking props moved, `file_path_foreach` metadata).

| Area | Old (<= 4.5) | Blender 5.x |
|---|---|---|
| EEVEE id | `'BLENDER_EEVEE_NEXT'` (4.2-4.5) | `'BLENDER_EEVEE'` ✔. `BLENDER_EEVEE_NEXT` raises `TypeError`; valid: `BLENDER_EEVEE`, `BLENDER_WORKBENCH`, `CYCLES` |
| Action F-curves | `action.fcurves`, `action.groups`, `action.id_root`, `fcurves.new(action_group=)` | all removed ✔ (`hasattr` is False). Slots + layers + strips + channelbags; `group_name=` |
| Video output | `file_format = 'FFMPEG'` | set `image_settings.media_type = 'VIDEO'` **first** ✔ (else `TypeError`) |
| Compositor tree | `scene.use_nodes = True; scene.node_tree` | `scene.compositing_node_group` (starts `None`); `scene.node_tree` gone ✔; `use_nodes` deprecated (always True, removal in 6.0) |
| Composite node | `CompositorNodeComposite` | undefined ✔; use `NodeGroupOutput` + an `Image` interface socket |
| Glare node | `node.glare_type`, `node.threshold`, `.quality`, `.mix` ... | all settings are **input sockets** ✔ (`Type` menu takes the label: `'Bloom'`, not `'BLOOM'`) |
| Sky texture | `sky_type = 'NISHITA'`, `dust_density` | `'SINGLE_SCATTERING'` / `'MULTIPLE_SCATTERING'` (default) ✔; `aerosol_density` ✔; `'PREETHAM'`, `'HOSEK_WILKIE'` still exist |
| Material transparency | `blend_method`, `shadow_method` (4.1-) | `surface_render_method` `'DITHERED'|'BLENDED'`; `blend_method` still **exists as an alias** ✔ (`'BLEND'`→`BLENDED`, `'HASHED'`/`'CLIP'`→`DITHERED`); `shadow_method` removed ✔ → `use_transparent_shadow` |
| Material/World nodes | `mat.use_nodes = True` | node tree exists on creation; `use_nodes` deprecated (DeprecationWarning, removal 6.0) ✔ |
| Principled BSDF sockets (4.0) | `Specular`, `Transmission`, `Emission`, `Subsurface`, `Clearcoat`, `Sheen` | `Specular IOR Level`, `Transmission Weight`, `Emission Color` + `Emission Strength`, `Subsurface Weight`, `Coat Weight`, `Sheen Weight` ✔ (old names → `KeyError`) |
| EEVEE props | `use_gtao`, `use_bloom`, `use_ssr`, `use_soft_shadows`, `gtao_distance`, `eevee.use_motion_blur` | all gone ✔; AO distance is `view_layer.eevee.ambient_occlusion_distance`; motion blur is `scene.render.use_motion_blur` / `motion_blur_shutter`; bloom = compositor Glare |
| Render passes | `DiffCol`, `IndexMA`, `Z` | "Diffuse Color", "Material Index", "Depth" *(docs)* |
| Misc | `bgl`, `Image.bindcode` | removed; use `gpu` module *(docs)*. Dict-style `scene['cycles']` no longer reads `bpy.props` data *(docs)*. Python 3.13 |

### 2.1 EEVEE: engine, settings, performance

```python
scene.render.engine = "BLENDER_EEVEE"
ee = scene.eevee
ee.taa_render_samples = 32      # default 64 (viewport taa_samples 16)
ee.use_raytracing = False       # default False. True = screen-space reflections/refraction, 'ray_tracing_method' 'SCREEN'|'PROBE',
                                # ee.ray_tracing_options.resolution_scale ('2' default) / use_denoise / screen_trace_quality
ee.use_shadows = True; ee.shadow_ray_count = 1; ee.shadow_step_count = 6; ee.light_threshold = 0.01
ee.use_fast_gi = True; ee.fast_gi_method = "GLOBAL_ILLUMINATION"   # or "AMBIENT_OCCLUSION_ONLY" (cheaper)
ee.fast_gi_ray_count = 2; ee.fast_gi_step_count = 8; ee.fast_gi_resolution = "2"; ee.gi_diffuse_bounces = 3
ee.shadow_pool_size = "512"     # '16'..'2048'; per light: light.use_shadow, shadow_jitter_overblur, shadow_filter_radius, shadow_maximum_resolution
ee.volumetric_samples = 64; ee.volumetric_tile_size = "8"; ee.use_volumetric_shadows = False
world.sun_threshold = 10.0; world.use_sun_shadow = True            # sky/HDRI sun is extracted as a shadow-casting sun automatically
```

Measured on this laptop (i7-1355U / Iris Xe, other sessions running, so +/-30 % noise), smoke-test scene (rigged man/dog/cow + props, 2K road texture, Glare):

| Setup | s / frame |
|---|---|
| 960x540, 32 spp | 1.2 - 1.5 |
| 1280x720, 32 / 64 spp | 2.4 - 2.8 (little spp sensitivity: overhead dominates) |
| 1280x720, 32 spp, ray tracing ON | ~2.0 per frame, but the **first frame took 61 s** (shader compile) |
| 1920x1080, 32 spp | ~2.5 |

So a 30 s clip at 24 fps (720 frames) is roughly 25-35 min at 720p-1080p. Keep ray tracing off except for hero shots.
A sky + sun with `Standard`/`AgX` and `use_fast_gi` gives acceptable lighting without it.

### 2.2 Materials, sky, HDRI, colour management

```python
mat = bpy.data.materials.new("M")                     # default Principled tree already exists
mat.surface_render_method = "DITHERED"                # opaque-ish, supports alpha cutout/hash; "BLENDED" = sorted blending (glass/water)
mat.use_transparent_shadow = True; mat.use_raytrace_refraction = True   # use_screen_refraction is an alias
bsdf = mat.node_tree.nodes["Principled BSDF"]; bsdf.inputs["Emission Color"].default_value = (1, .4, 0, 1)

world = bpy.data.worlds.new("Sky"); scene.world = world         # Background + Output nodes exist already
sky = world.node_tree.nodes.new("ShaderNodeTexSky")
sky.sky_type = "MULTIPLE_SCATTERING"; sky.sun_elevation = radians(48); sky.sun_rotation = radians(215)
sky.altitude = 50; sky.air_density = 1.0; sky.aerosol_density = 1.6; sky.ozone_density = 1.0   # aerosol up = hazier
world.node_tree.links.new(sky.outputs["Color"], world.node_tree.nodes["Background"].inputs["Color"])
# HDRI instead: ShaderNodeTexEnvironment(image=bpy.data.images.load(".../hdri/wide_street_01_2k.hdr")) -> Background
```

View transforms accepted ✔: `Standard`, `Filmic`, `AgX` (default), `Khronos PBR Neutral`, `ACES 1.3`, `ACES 2.0`, `Raw`, `False Color`.
AgX looks carry the prefix (`"AgX - Punchy"`, `"AgX - High Contrast"`, ...; bare names raise). AgX desaturates bright brand colours:
use `Standard` or `Khronos PBR Neutral` for the Bharat-Bot livery. `scene.view_settings.exposure` is useful with the bright Sky texture (-0.8 used in the smoke test).

### 2.3 Slotted / layered actions: F-curves from Python

An Action is now `slots` (which ID it animates) x `layers` -> `strips` (type `KEYFRAME`) -> `channelbags` (one per slot) -> `fcurves`.

```python
# (a) simplest: let Blender build layer/strip/channelbag. The action MUST be assigned first, or RuntimeError.
ad = obj.animation_data or obj.animation_data_create()
act = bpy.data.actions.new("Move")
ad.action = act
ad.action_slot = act.slots.new(id_type="OBJECT", name=obj.name)     # (assigning a keyframed action auto-picks a single slot)
fc = act.fcurve_ensure_for_datablock(obj, "location", index=0)       # creates Layer + KEYFRAME strip + channelbag
fc.keyframe_points.insert(1, 0.0).interpolation = "LINEAR"
fc.keyframe_points.insert(48, 5.0).interpolation = "LINEAR"

# (b) explicit
slot = act.slots.new("OBJECT", "Cube"); layer = act.layers.new("Layer"); strip = layer.strips.new(type="KEYFRAME")
cb = strip.channelbag(slot, ensure=True)
fc = cb.fcurves.new("rotation_euler", index=2)          # also cb.fcurves.ensure(path, index=), .find(), .remove(); group_name= not action_group=
strip.key_insert(slot, "location", 1, 3.0, 10.0)        # (slot, data_path, array_index, value, time)
from bpy_extras import anim_utils
cb = anim_utils.action_ensure_channelbag_for_slot(act, slot)   # also action_get_channelbag_for_slot, action_get_first_suitable_slot

# (c) obj.keyframe_insert("location", frame=5) still works (creates action + slot); iterate: for l in act.layers: for s in l.strips: for cb in s.channelbags: cb.fcurves
for fcu in cb.fcurves: fcu.modifiers.new("CYCLES")     # loop a clip forever without NLA
```

Other API: `AnimData.action_slot`, `.action_suitable_slots`, `Action.slots[i].target_id_type` (replaces `id_root`), `Action.is_action_layered`.
Assigning `ad.action = act` auto-assigns the slot when the action has a single slot ✔.
NLA: `track = ad.nla_tracks.new(); st = track.strips.new("name", start_frame, action)` auto-assigns the slot (`st.action_slot`) ✔;
`st.repeat = 3`, `st.scale = 2` lengthen the strip; `st.extrapolation` defaults to `HOLD`.

### 2.4 Video / image output

```python
r = scene.render; ims = r.image_settings
ims.media_type = "VIDEO"            # BEFORE file_format. Choices: IMAGE | MULTI_LAYER_IMAGE | VIDEO
ims.file_format = "FFMPEG"
r.ffmpeg.format = "MPEG4"           # default is "MKV"! others: WEBM, QUICKTIME, AVI...
r.ffmpeg.codec = "H264"             # H265, AV1, WEBM(VP9), PRORES, FFV1, PNG ...
r.ffmpeg.constant_rate_factor = "HIGH"   # LOSSLESS, PERC_LOSSLESS, HIGH, MEDIUM(default), LOW, VERYLOW, LOWEST, CUSTOM
r.ffmpeg.ffmpeg_preset = "GOOD"     # BEST | GOOD | REALTIME;  r.ffmpeg.audio_codec = "NONE"
r.filepath = "//out/clip_"          # Blender appends the frame range: clip_0001-0240.mp4
ims.color_mode = "RGB"
# PNG sequence (frame-exact, good for Remotion): media_type = "IMAGE"; file_format = "PNG"; filepath = "//out/f_"; bpy.ops.render.render(animation=True)
```

Blender ships its own FFmpeg, so no system ffmpeg is needed for MP4 output (ffmpeg was not on PATH at the time of testing).

### 2.5 Compositor node groups (bloom)

```python
tree = bpy.data.node_groups.new("comp", "CompositorNodeTree")
scene.compositing_node_group = tree; scene.render.use_compositing = True
tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
rl = tree.nodes.new("CompositorNodeRLayers"); gl = tree.nodes.new("CompositorNodeGlare"); out = tree.nodes.new("NodeGroupOutput")
gl.inputs["Type"].default_value = "Bloom"      # Bloom, Ghosts, Streaks, Fog Glow, Simple Star, Sun Beams, Kernel
gl.inputs["Threshold"].default_value = 1.2     # identifier 'Highlights Threshold'; also Smoothness, Clamp, Maximum, Strength, Saturation, Tint, Size, Quality
gl.inputs["Strength"].default_value = 0.35; gl.inputs["Size"].default_value = 0.55
tree.links.new(rl.outputs["Image"], gl.inputs["Image"]); tree.links.new(gl.outputs["Image"], out.inputs["Image"])
```

Glare outputs: `Image`, `Glare`, `Highlights`. Available in compositor trees ✔: Blur (`Size`,`Type`), Lensdist, ColorBalance, AlphaOver, BokehBlur, Defocus,
Tonemap, OutputFile (`directory`, `file_name`, `file_output_items` replace `base_path`/`file_slots`), plus shader-type `ShaderNodeMix` / `Math` / `Gamma` / `ValToRGB` / `RGBCurve`
(`CompositorNodeMixRGB`/`MixNode` and `ShaderNodeHueSaturation` do not exist there).

### 2.6 Importing glTF/GLB (what the FBX2glTF assets do)

`bpy.ops.import_scene.gltf(filepath=...)` options in 5.2: `import_pack_images`, `merge_vertices`, `import_shading` (NORMALS|FLAT|SMOOTH),
`bone_heuristic` (BLENDER|TEMPERANCE|FORTUNE), `disable_bone_shape`, `bone_shape_scale_factor`, `guess_original_bind_pose`, `import_webp_texture`,
`import_unused_materials`, `import_select_created_objects`, `import_scene_extras`, `import_scene_as_collection` (default True: a collection per file),
`import_merge_material_slots`, `import_point_as_pointcloud`, `export_import_convert_lighting_mode`, `loglevel`. There are no animation options.

What an import leaves behind (Shiba Inu, verified; the same for all Quaternius rigs):

* **Y-up glTF → Z-up Blender**: `(x, y, z)_gltf → (x, -z, y)_blender`. Assets face **-Y** after import (verified numerically via bone pairs).
  To face the road direction rotate Z: **+90° → faces +X, -90° → -X, 180° → +Y**.
* Rigged GLBs come in at an odd scale (armature object scale 100 and a -90° X rotation under a `RootNode` empty). Measure with `matrix_world`, not `obj.dimensions`.
* Junk to delete after import: a stray 2 m mesh **`Icosphere`** and 12-18 leaf-bone empties named **`*_end`** per rig.
* Animations: every glTF clip becomes an **Action**, the first one is left **active** on the armature and *all* clips also get an **NLA track, all muted**.
  Quaternius dog/cow files contain every clip twice (`AnimalArmature|Walk` and a plain `Walk`): 24 actions for 12 clips. Humans have one set.
  Actions have a single slot named after the armature; `ad.action = bpy.data.actions["AnimalArmature|Walk"]` picks it up.
  Frame rate 24 fps (Blender default) matches; clips start at frame 0. Unreferenced actions are dropped on save unless `use_fake_user`.
* All clips are **in place** (no root motion), 0.5 - 1.7 s long, not marked cyclic: loop with `fcurve.modifiers.new("CYCLES")` or an NLA strip with `repeat`.

```python
def play(arm, name):                      # drop NLA clutter, assign one clip, loop it
    ad = arm.animation_data
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    ad.action = act = bpy.data.actions[name]
    for l in act.layers:
        for s in l.strips:
            for cb in s.channelbags:
                for fc in cb.fcurves: fc.modifiers.new("CYCLES")
```

`assets/tools/blender5_smoke_test.py` contains a tested `import_glb()` (wraps the import in an empty, deletes junk, applies scale/yaw, drops the model
to a ground height) plus `pbr_material()` for the Poly Haven maps (colour space `sRGB` for `_diff`, `Non-Color` for `_rough`/`_nor_gl`, Normal Map node). It asserts the facing convention, renders a PNG + MP4 and prints timings.

---

## 3. Assets

Layout: `assets/polyhaven/{hdri,textures,models}`, `assets/polypizza/{animals,humans,vehicles,trees,props}` (+ `manifest.json` with SHA-256, page, licence),
`assets/tools`, `assets/_previews` (front/side contact sheets, 9 files; sizes before/after are annotated in each tile title). Total: polyhaven 72 MB, polypizza 17 MB.
"Scale" below is the uniform scale that gives a believable real size in a 1 unit = 1 m scene. Every model faces **-Y** on import unless noted.

### 3.1 Animated: animals and people (Quaternius, CC0, GLB, rigged)

Clip lists: dogs `Attack, Death, Eating, Gallop (=run), Gallop_Jump, Idle, Idle_2, Idle_2_HeadLow, Idle_HitReact_Left/Right, Jump_ToIdle, Walk`;
cow/bull/donkey/horse `Attack_Headbutt, Attack_Kick, Death, Eating, Gallop, Gallop_Jump, Idle, Idle_2, Idle_Headlow, Idle_HitReact_Left/Right, Jump_toIdle, Walk` (no "Run": use Gallop).
Action name = `<armature>|<clip>`: dogs/cow `AnimalArmature|Walk`; man `HumanArmature|Man_Walk`; women `HumanArmature|Female_Walk`; worker/casual/animated_woman `CharacterArmature|Walk`.
Human clips: `HumanArmature` rigs `Idle, Walk, Run, Jump, RunningJump, Sitting, Standing, Clapping, Punch, SwordSlash, Death`; `CharacterArmature` rigs 24 clips incl. `Idle, Idle_Neutral, Walk, Run, Run_Back, Run_Left, Run_Right, Wave, Interact, Roll, Kick_*, Punch_*, HitRecieve, Death`.

| File (`assets/polypizza/...`) | Tris | KB | Imports as X x Y x Z (m) | Scale → real size | Notes |
|---|---|---|---|---|---|
| `animals/quaternius_shiba_inu.glb` | 1950 | 831 | 1.07 x 4.18 x 3.04 | **0.181** → 0.55 m tall | tan/white curly tail: the street-dog stand-in |
| `animals/quaternius_husky.glb` | 1920 | 906 | 0.99 x 3.92 x 3.13 | **0.198** → 0.62 m | grey/black |
| `animals/quaternius_cow.glb` | 2450 | 1004 | 2.31 x 8.03 x 4.59 | **0.294** → 1.35 m, 2.4 m long | brown, horns |
| `animals/quaternius_bull.glb` | 2418 | 1014 | 2.51 x 8.03 x 4.59 | **0.348** → 1.6 m | black |
| `animals/quaternius_donkey.glb` / `horse.glb` | 2000 / 2182 | ~1050 | 1.16 x 4.71 x 3.85 / 1.41 x 5.71 x 4.76 | **0.312** → 1.2 m / **0.357** → 1.7 m | extras |
| `humans/quaternius_man.glb` | 1852 | 482 | 1.81 x 1.43 x 4.81 | **0.353** → 1.70 m | grey T-shirt, shorts |
| `humans/quaternius_woman_casual.glb` | 2776 | 572 | 1.80 x 1.39 x 4.63 | **0.341** → 1.58 m | green top |
| `humans/quaternius_woman_in_dress.glb` | 1786 | 470 | 1.81 x 1.56 x 4.65 | **0.34** → 1.58 m | red dress (recolour) |
| `humans/quaternius_worker.glb` | 5240 | 1313 | 0.59 x 0.63 x 1.82 | **0.945** → 1.72 m | hard hat + hi-vis |
| `humans/quaternius_casual_character.glb` | 5776 | 1397 | 0.59 x 0.64 x 1.81 | **0.939** → 1.70 m | jeans + T-shirt |
| `humans/quaternius_animated_woman.glb` | 6424 | 1495 | 0.52 x 0.62 x 1.81 | **0.886** → 1.60 m | orange trousers |

Foot-sliding-free travel speed (measured from planted-foot velocity in the in-place clips; value x scale; to move faster, play the clip faster):

| Asset | Walk cycle | Walk m/s (at scale) | Run/Gallop cycle | Run m/s (at scale) |
|---|---|---|---|---|
| shiba (0.181) / husky (0.198) | 1.08 s | 0.42 / 0.46 | 0.58 s | 1.4 / 1.6 |
| cow (0.294) / bull (0.348) | 1.21 s | 0.78 / 0.92 | 0.63 s | 3.1 / 3.7 |
| man (0.353) | 1.08 s | 1.50 | 0.92 s | 3.2 |
| woman_casual (0.341) / in_dress (0.34) | 1.08 s | 1.45 | 0.92 s | 3.1 |
| worker (0.945) / casual (0.939) | 1.38 s | 1.28 | 0.83 s | 2.8 |
| animated_woman (0.886) | 1.71 s | 0.95 | 1.04 s | 2.2 |

(The smoke test uses these numbers, e.g. man walks at 4.255 x 0.354 = 1.5 m/s.)

### 3.2 Vehicles

| File | Licence | Tris | Imports as (m) | Scale → size | Forward | Lift |
|---|---|---|---|---|---|---|
| `vehicles/quaternius_taxi.glb` | CC0 | 3278 | 1.81 x 4.22 x 1.31 | 1.0 (4.2 m) | -Y | 0 |
| `vehicles/quaternius_suv.glb` | CC0 | 3294 | 2.11 x 4.21 x 1.53 | 1.045 → 4.4 m | -Y | 0 |
| `vehicles/quaternius_pickup_truck.glb` | CC0 | 6432 | 2.31 x 5.18 x 1.85 | 1.0 | -Y | 0 |
| `vehicles/quaternius_truck.glb` | CC0 | 7474 | 2.71 x 5.26 x 2.88 | 1.33 → 7 m | -Y | 0 |
| `vehicles/kaylousberg_car_hatchback.glb` | CC0 | 1194 | 0.42 x 0.81 x 0.37 | **4.71** → 3.8 m | -Y | 0.061 x scale |
| `vehicles/kaylousberg_stationwagon.glb` | CC0 | 1234 | 0.42 x 0.94 x 0.37 | **4.58** → 4.3 m | -Y | 0.061 x scale |
| `vehicles/vespa_scooter_jasmine_roberts.glb` | **CC BY** | 1665 | 1.65 x 4.38 x 3.19 | **0.411** → 1.8 m | -Y | **1.053 x scale** (origin mid-height) |
| `vehicles/motorcycle_jeremy.glb` | **CC BY** | 2092 | 15.79 x 5.68 x 9.94 | **0.127** → 2.0 m | **+X** | 0 |
| `vehicles/bicycle_jeremy.glb` | **CC BY** | 2466 | 5.46 x 19.58 x 9.96 | **0.089** → 1.74 m | **+Y** | 0 |
| `vehicles/bus_jeremy.glb` | **CC BY** | 2142 | 9.16 x 23.75 x 9.68 | **0.442** → 10.5 m | -Y | 0 |

### 3.3 Trees and props (all CC0 unless noted; all static)

| File | Tris | Imports as (m) | Scale → size | Notes |
|---|---|---|---|---|
| `trees/quaternius_palm_tree_a.glb` / `_b.glb` | 3134 / 2924 | 2.86 x 2.75 x 2.69 | **2.6** → 7 m | coconut/banana-style palms |
| `trees/quaternius_tree.glb` | 6265 | 4.31 x 4.58 x 7.26 | 0.96 → 7 m | broadleaf, 2.4 MB (textures); lift 0.243 x scale |
| `trees/quaternius_bush.glb` | 360 | 2.07 x 2.06 x 1.19 | 0.84 → 1 m | lift 0.289 x scale |
| `props/quaternius_trashcan_large.glb` | 646 | 1.22 x 1.22 x 1.85 | 0.54 → 1 m | dustbin |
| `props/quaternius_dumpster.glb` | 302 | 2.44 x 1.30 x 2.03 | 0.82 → 2 m | green municipal bin |
| `props/quaternius_trash_bags.glb` | 2088 | 0.91 x 0.52 x 0.53 | 1.0 | pile several: garbage heap |
| `props/quaternius_street_light_a.glb` | 324 | 0.42 x 2.09 x 5.65 | 1.15 → 6.5 m | arm toward -Y |
| `props/quaternius_street_light_b.glb` | 664 | 1.35 x 1.19 x 2.65 | 1.32 → 3.5 m | twin arms along X |
| `props/quaternius_cart.glb` | 2659 | 0.46 x 0.93 x 0.80 | **1.94** → 1.8 m long | handcart with awning, handles at -X |
| `props/quaternius_broken_cart.glb` | 1432 | 4.11 x 3.87 x 3.43 | 0.58 → 2.4 m | lift 1.404 x scale |
| `props/quaternius_market_stand.glb` | 1548 | 0.95 x 1.19 x 1.05 | **1.85** → 2.2 m | awning faces +X |
| `props/quaternius_traffic_cone.glb` | 168 | 0.68 x 0.68 x 0.64 | 1.1 → 0.7 m | |
| `props/quaternius_traffic_barrier.glb` | 364 | 1.55 x 0.78 x 0.80 | 0.96 | striped barricade |
| `props/quaternius_barrier_large.glb` | 624 | 3.81 x 0.67 x 3.18 | 0.79 → 3 m | chain-link construction panel |
| `props/quaternius_bench.glb` | 376 | 0.67 x 0.24 x 0.32 | **2.4** → 1.6 m | |
| `props/street_vendor_cart_alan_zimmerman.glb` | 8098 | 4.41 x 3.21 x 4.05 | 0.5 → 2.2 m | **CC BY**; motorbike + food cart three-wheeler, forward +X, lift 1.496 x scale. Not an auto-rickshaw |

### 3.4 Poly Haven (CC0)

* HDRI (2K `.hdr`): `hdri/wide_street_01_2k.hdr` (sunlit city avenue, strong sun, street reflections) and `hdri/kloofendal_43d_clear_puresky_2k.hdr` (clear sky, no buildings).
* Textures (JPG: `_diff`, `_nor_gl` OpenGL normals, `_rough`, `_disp` for the first five), `assets/polyhaven/textures/<id>/`:
  `road_damaged_2` (2K, dusty brown pothole asphalt), `road_damaged`, `asphalt_02` (grey, long cracks), `red_laterite_soil_stones`, `red_dirt_mud_01`,
  `concrete_pavement_02`, `checkered_pavement_tiles`, `painted_plaster_wall` (off-white, tint it), `blue_plaster_weathered`, `red_brick`, `damaged_plaster` (flaking to brick).
  All 1K except `road_damaged_2`. Colour check sheet: `assets/_previews/sheet_textures.png` (order as listed). Displacement works with `mat.displacement_method = "BOTH"`.
* Models (glTF + 1K textures, true metric scale, load with the same importer): `models/modular_electricity_poles` (a **kit**: 3 assembled poles named `preset_01_*`, `preset_02_*`, `preset_03_*`, loose parts, 3 bare poles; **200 K tris**: keep one preset),
  `metal_trash_can` (clean + `_rust` variants, 14 K tris), `trashbag` (4.5 K), `utility_box_02` (6 K), `water_manhole_cover` (6 K, 0.69 m; open-manhole hazard), `old_tyre` (2.9 K, origin at centre), `plastic_crate_01` (18 K).

### 3.5 Import checklist

1. Import, delete `Icosphere` and `*_end` empties, parent everything to your own empty; set that empty's scale/yaw/location (never the armature).
2. Apply the "Scale" and "Lift" columns; the smoke test's `import_glb(..., ground_z=...)` computes the lift automatically from the deformed bounding box.
3. Pick one action, delete the muted NLA tracks, add a `CYCLES` modifier, move at the speed in the foot-speed table.
4. Re-tint materials for variety (Quaternius uses simple flat materials, e.g. recolour shirts to kurta colours; Poly Haven plaster takes a Multiply tint).
5. Budget: whole street with ~10 characters/animals + vehicles stays under ~150 K triangles (excluding the 200 K electricity-pole kit).

### 3.6 Could not get / caveats

* **No CC0 auto-rickshaw** exists in the sources searched (Poly Haven, poly.pizza, Quaternius, Kenney, OpenGameArt); all rickshaw models found were paid/marketplace licences. Build one procedurally or use the CC BY three-wheeler above.
* **No CC0 motor scooter/motorbike** on poly.pizza; the five CC BY models need the credit line in `assets/CREDITS.md`.
* Previews of the two humans/animals are single default frames (T/A-poses); the animals are low-poly "game" style, not photoreal.
* Quaternius humans are generic (no Indian clothing); recolour or add simple kurta/dupatta geometry procedurally.
* Not done within this session: live MCP session test, installing the Claude skills/plugins, and the final 1080p/64 spp benchmark row.

## 4. References

Blender Python API: <https://docs.blender.org/api/current/> · Release notes: <https://developer.blender.org/docs/release_notes/5.0/python_api/>, `.../5.1/python_api/`, `.../5.2/python_api/` ·
MCP for Blender: <https://github.com/ahujasid/mcp-for-blender> · Blender Lab MCP: <https://www.blender.org/lab/mcp-server/> ·
Poly Haven API: <https://api.polyhaven.com> · poly.pizza: <https://poly.pizza> · Quaternius: <https://quaternius.com>
