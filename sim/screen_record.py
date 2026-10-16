"""Screen-record the simulation playing in Blender's own window.

  blender blend/bharat_full.blend --python sim/screen_record.py -- --out recordings/blender_screen.mp4

Blender goes fullscreen and looks through the scene cameras in Rendered shading. Two capture modes:
  --mode self     (default) Blender screenshots its whole window (viewport, timeline, outliner) frame by frame
                  and ffmpeg stitches them, so it works even when the PC is locked or another window is on top.
  --mode desktop  live playback + an ffmpeg desktop capture (needs the screen unlocked and visible).
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = argparse.ArgumentParser()
p.add_argument("--out", default="recordings/blender_screen.mp4")
p.add_argument("--seconds", type=float, default=None)
p.add_argument("--warmup", type=float, default=30.0)
p.add_argument("--shading", default="RENDERED")
p.add_argument("--pixel", default="2")
p.add_argument("--mode", default="self", choices=["self", "desktop"])
p.add_argument("--step", type=int, default=2, help="self mode: capture every Nth frame (2 = 15 fps)")
p.add_argument("--samples", type=int, default=4, help="self mode: viewport redraws per frame")
p.add_argument("--frames", default=None, help="self mode: e.g. 1000-1010")
OPT = p.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
STATE = {}


def ffmpeg_exe():
    found = shutil.which("ffmpeg")
    if found:
        return found
    pattern = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe")
    hits = glob.glob(pattern)
    return hits[0] if hits else "ffmpeg"


def attempt(label, fn):
    try:
        fn()
    except Exception as e:                       # one failed UI tweak must not stop the recording
        print("SETUP WARNING", label, e, flush=True)


def setup():
    win = bpy.context.window_manager.windows[0]

    def fullscreen():
        with bpy.context.temp_override(window=win):
            bpy.ops.wm.window_fullscreen_toggle()

    if OPT.mode == "desktop":        # self-capture reads Blender's own window, so leave the user's screen free
        attempt("fullscreen", fullscreen)
    for area in win.screen.areas:
        if area.type != "VIEW_3D":
            continue
        sp = area.spaces.active

        def shading(sp=sp):
            sp.shading.type = OPT.shading
            sp.shading.use_scene_lights = sp.shading.use_scene_world = True

        def overlays(sp=sp):
            sp.overlay.show_overlays = False
            sp.show_gizmo = False

        def camera_view(sp=sp, area=area):
            sp.region_3d.view_perspective = "CAMERA"
            region = next(r for r in area.regions if r.type == "WINDOW")
            with bpy.context.temp_override(window=win, area=area, region=region):
                bpy.ops.view3d.view_center_camera()

        for label, fn in (("shading", shading), ("overlays", overlays), ("camera", camera_view)):
            attempt(label, fn)
    sc = bpy.context.scene
    attempt("pixel size", lambda: setattr(sc.render, "preview_pixel_size", OPT.pixel))
    attempt("sync", lambda: setattr(sc, "sync_mode", "FRAME_DROP"))
    sc.frame_set(sc.frame_start)
    return None


def failsafe():
    print("FAILSAFE QUIT", flush=True)
    bpy.ops.wm.quit_blender()


def start():
    sc = bpy.context.scene
    secs = OPT.seconds or (sc.frame_end - sc.frame_start + 1) / sc.render.fps + 1.0
    out = os.path.join(ROOT, OPT.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = [ffmpeg_exe(), "-y", "-f", "gdigrab", "-framerate", "30", "-draw_mouse", "0", "-i", "desktop",
           "-t", f"{secs:.1f}", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", out]
    STATE["log"] = open(out + ".log", "w")
    STATE["proc"] = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=STATE["log"])
    win = bpy.context.window_manager.windows[0]
    with bpy.context.temp_override(window=win, screen=win.screen):
        bpy.ops.screen.animation_play()
    bpy.app.timers.register(stop, first_interval=secs + 2.0)
    print("RECORDING", out, f"{secs:.1f}s", flush=True)
    return None


def stop():
    try:
        STATE["proc"].wait(timeout=30)
    except Exception:
        STATE["proc"].kill()
    STATE["log"].close()
    print("RECORDED", flush=True)
    bpy.ops.wm.quit_blender()
    return None


def self_start():
    sc = bpy.context.scene
    f0, f1 = (int(v) for v in OPT.frames.split("-")) if OPT.frames else (sc.frame_start, sc.frame_end)
    out = os.path.join(ROOT, OPT.out)
    shots = out + "_shots"
    os.makedirs(shots, exist_ok=True)
    STATE.update(f=f0, end=f1, i=0, out=out, shots=shots)
    print("SELF-CAPTURE", f0, f1, "step", OPT.step, flush=True)
    return 0.0 if False else None


def self_tick():
    sc = bpy.context.scene
    if "f" not in STATE:
        return 0.5
    if STATE["f"] > STATE["end"]:
        self_finish()
        return None
    sc.frame_set(STATE["f"])
    win = bpy.context.window_manager.windows[0]
    path = os.path.join(STATE["shots"], f"s_{STATE['i']:05d}.png")
    with bpy.context.temp_override(window=win, screen=win.screen):
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=OPT.samples)
        bpy.ops.screen.screenshot(filepath=path, check_existing=False)
    if STATE["i"] % 50 == 0:
        print("SHOT", STATE["f"], flush=True)
    STATE["f"] += OPT.step
    STATE["i"] += 1
    return 0.0


def self_finish():
    fps = bpy.context.scene.render.fps / OPT.step
    cmd = [ffmpeg_exe(), "-y", "-framerate", f"{fps:g}", "-i", os.path.join(STATE["shots"], "s_%05d.png"),
           "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", STATE["out"]]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("RECORDED", STATE["out"], STATE["i"], "shots", flush=True)
    bpy.ops.wm.quit_blender()


bpy.app.timers.register(setup, first_interval=3.0)
if OPT.mode == "desktop":
    bpy.app.timers.register(start, first_interval=3.0 + OPT.warmup)
    bpy.app.timers.register(failsafe, first_interval=3.0 + OPT.warmup + (OPT.seconds or 120.0) + 90.0)
else:
    bpy.app.timers.register(self_start, first_interval=3.0 + OPT.warmup)
    bpy.app.timers.register(self_tick, first_interval=4.0 + OPT.warmup)
