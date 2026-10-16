"""Render a saved shot to numbered JPEGs. Safe to run several copies at once on the same shot:
frames already on disk (or claimed by another process) are skipped, so a crash just means "run it again".

  blender -b blend/bharat_full.blend --python sim/render_shot.py -- --out renders/bharat_full --res 1280x720 --samples 16
"""
import argparse
import os
import sys
import time

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = argparse.ArgumentParser()
p.add_argument("--out", required=True)
p.add_argument("--res", default="1280x720")
p.add_argument("--samples", type=int, default=16)
a = p.parse_args(sys.argv[sys.argv.index("--") + 1:])

sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = (int(v) for v in a.res.split("x"))
sc.render.resolution_percentage = 100
sc.eevee.taa_render_samples = a.samples
sc.render.image_settings.media_type = "IMAGE"
sc.render.image_settings.file_format = "JPEG"
sc.render.image_settings.quality = 93
sc.render.use_overwrite = False
sc.render.use_placeholder = True
out = a.out if os.path.isabs(a.out) else os.path.join(ROOT, a.out)
os.makedirs(out, exist_ok=True)
sc.render.filepath = os.path.join(out, "f_")
stamp = {}
bpy.app.handlers.render_pre.append(lambda s, *_: stamp.__setitem__("t", time.time()))
bpy.app.handlers.render_post.append(
    lambda s, *_: print(f"FRAME {s.frame_current} {time.time() - stamp['t']:.2f}s", flush=True))
bpy.ops.render.render(animation=True)
print("SHOT DONE", out, flush=True)
