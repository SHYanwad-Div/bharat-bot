"""Build (and optionally render) one shot of the Bharat-Bot simulation in Blender.

  blender -b --python sim/build_scene.py -- --shot bharat_full --save blend/bharat_full.blend
  blender -b --python sim/build_scene.py -- --shot bharat_full --stills 60,400,900 --res 960x540 --samples 8
  blender -b --python sim/build_scene.py -- --shot bharat_full --render --res 1920x1080 --samples 24

Shots: bharat_full, baseline_pothole, baseline_dogs, baseline_theft (all simulated) and us_sidewalk (scripted).
"""
import argparse
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import bpy_utils as U  # noqa: E402
import characters as C  # noqa: E402
import environment as E  # noqa: E402
import simulate as S  # noqa: E402
import world as W  # noqa: E402

PI = math.pi
FPS = S.FPS

MODE_COLOURS = {
    "go": (0.1, 1.0, 0.55), "caution": (1.0, 0.5, 0.03), "alarm": (1.0, 0.03, 0.02), "deliver": (0.15, 0.55, 1.0),
    "done": (0.2, 1.0, 0.2),
}
MODE_GROUP = {"DOG HOTSPOT": "caution", "DOG FREEZE": "caution", "CREEP": "caution", "YIELD": "caution",
              "PERSON IN PATH": "caution", "BLOCKED": "caution", "TAMPER": "caution", "ALARM": "alarm",
              "STUCK": "alarm", "STOLEN": "alarm", "DELIVERING": "deliver", "DELIVERED": "done"}


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--shot", default="bharat_full")
    p.add_argument("--save", default=None)
    p.add_argument("--render", action="store_true")
    p.add_argument("--stills", default=None)
    p.add_argument("--frames", default=None)
    p.add_argument("--res", default="1920x1080")
    p.add_argument("--samples", type=int, default=24)
    p.add_argument("--out", default=None)
    p.add_argument("--raytrace", action="store_true")
    return p.parse_args(a)


# ----------------------------------------------------------------------------------------------- scene setup
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for d in (U.MATS, U.COLLS, U.FONTS, E.DETAIL):
        d.clear()
    U.Part._tmp = None
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.unit_settings.system = "METRIC"
    return sc


def lighting(sc, us=False):
    sun_rot = (math.radians(48), 0, math.radians(35))
    lt = bpy.data.lights.new("Sun", "SUN")
    lt.energy = 3.3
    lt.angle = math.radians(1.2)
    lt.color = (1.0, 0.96, 0.9)
    ob = bpy.data.objects.new("Sun", lt)
    U.coll("Lights").objects.link(ob)
    ob.rotation_euler = sun_rot
    w = bpy.data.worlds.new("Sky")
    sc.world = w
    nt = w.node_tree
    bg = nt.nodes.get("Background")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = False
    sky.sun_elevation = math.radians(42)
    sky.sun_rotation = math.radians(-55 + 90)
    sky.altitude = 900.0
    sky.aerosol_density = 3.0 if not us else 1.0
    sky.air_density = 1.0
    nt.links.new(sky.outputs[0], bg.inputs[0])
    bg.inputs["Strength"].default_value = 0.26


def render_settings(sc, res, samples, raytrace):
    sc.render.engine = "BLENDER_EEVEE"
    rx, ry = (int(v) for v in res.split("x"))
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = rx, ry, 100
    ee = sc.eevee
    ee.taa_render_samples = samples
    ee.use_raytracing = raytrace
    ee.shadow_ray_count = 1
    ee.shadow_step_count = 6
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.render.image_settings.media_type = "IMAGE"
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 93
    try:                                    # a gentle bloom so LEDs, rings and the alarm glow
        ng = bpy.data.node_groups.new("Comp", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        rl = ng.nodes.new("CompositorNodeRLayers")
        gl = ng.nodes.new("CompositorNodeGlare")
        go = ng.nodes.new("NodeGroupOutput")
        for k, v in (("Type", "Bloom"), ("Threshold", 1.2), ("Strength", 0.55), ("Size", 0.55), ("Quality", "Medium")):
            try:
                gl.inputs[k].default_value = v
            except Exception:
                pass
        ng.links.new(rl.outputs["Image"], gl.inputs["Image"])
        ng.links.new(gl.outputs[0], go.inputs[0])
        sc.compositing_node_group = ng
    except Exception as e:
        print("compositor skipped:", e)


# ----------------------------------------------------------------------------------------------- animation helpers
def ground(x, y):
    return W.terrain_height(np.asarray(x, float), np.asarray(y, float))


def key_tf(ob, loc=None, rot=None, scale=None, start=1):
    if loc is not None:
        U.key_vec(ob, "location", loc, start)
    if rot is not None:
        U.key_vec(ob, "rotation_euler", rot, start)
    if scale is not None:
        U.key_vec(ob, "scale", scale, start)


def key_colour(ob, rgba, start=1, interp="LINEAR"):
    rgba = np.asarray(rgba, float)
    for i in range(4):
        U.key(ob, "color", rgba[:, i], index=i, start=start, interp=interp)


def col_series(n, rgb, alpha):
    a = np.broadcast_to(np.asarray(alpha, float), (n,))
    c = np.broadcast_to(np.asarray(rgb, float), (n, 3))
    return np.c_[c, a]


def ring_series(t, on, period, k, n_rings, r0, r1, a0):
    """Expanding, fading rings while `on`: returns scale and alpha arrays for ring k."""
    ph = ((t / period) - k / n_rings) % 1.0
    r = r0 + (r1 - r0) * ph
    alpha = a0 * (1 - ph) ** 1.5 * on
    s = np.where(alpha > 0.003, r, 0.001)
    return np.c_[s, s, np.ones_like(s)], alpha


# ----------------------------------------------------------------------------------------------- robot
def animate_robot(R, rec, t, gone=None):
    n = len(t)
    x, y, z = (np.array(rec["r_" + k]) for k in ("x", "y", "z"))
    h, pitch, roll = (np.array(rec["r_" + k]) for k in ("h", "pitch", "roll"))
    vis = np.array(rec["r_vis"], float)
    key_tf(R["root"], loc=np.c_[x, y, z], rot=np.c_[roll, -pitch, h], scale=np.repeat(vis[:, None], 3, 1))
    lid = np.array(rec["r_lid"])
    lidj = np.array(rec["r_lidj"])
    U.key(R["hinge"], "rotation_euler", -lid * 1.75 - np.abs(lidj), index=1)
    spin = np.array(rec["r_spin"])
    dz = np.array(rec["r_dz"])
    for i, wob in enumerate(R["wheels"]):
        U.key(wob, "rotation_euler", spin[:, 0 if i < 3 else 1], index=1)
        U.key(wob, "location", dz[:, i], index=2)
    if R["arms"]:
        for side, nm, ob in R["arms"]:
            o = 0 if side > 0 else 3
            zf, zm, zb = dz[:, o], dz[:, o + 1], dz[:, o + 2]
            P = (np.full(n, 0.06), np.full(n, 0.10))
            B = (np.full(n, -0.19), (zm + zb) / 2 + 0.07)
            A, Cc = {"rf": (P, (np.full(n, 0.38), zf)), "rb": (P, B), "bf": (B, (np.zeros(n), zm)),
                     "bb": (B, (np.full(n, -0.38), zb))}[nm]
            mx, mz = (A[0] + Cc[0]) / 2, (A[1] + Cc[1]) / 2
            ln = np.hypot(Cc[0] - A[0], Cc[1] - A[1])
            ang = np.arctan2(-(Cc[1] - A[1]), Cc[0] - A[0])
            key_tf(ob, loc=np.c_[mx, np.full(n, side * 0.30), mz], rot=np.c_[np.zeros(n), ang, np.zeros(n)],
                   scale=np.c_[ln, np.ones(n), np.ones(n)])
    modes = rec["r_mode"]
    grp = [MODE_GROUP.get(m, "go") for m in modes]
    alarm = np.array(rec["r_alarm"], float)
    strobe = (np.floor(t * 8) % 2 == 0).astype(float)
    base = np.array([MODE_COLOURS[g] for g in grp])
    red = np.array(MODE_COLOURS["alarm"])
    stat = np.where(alarm[:, None] > 0, red * strobe[:, None] + np.array([0.1, 0.2, 1.0]) * (1 - strobe[:, None]), base)
    stat_a = np.where(alarm > 0, 0.9, 0.35)
    if "status" in R:
        key_colour(R["status"], np.c_[stat, stat_a])
    if "eyes" in R:
        eye = np.tile(np.array([0.1, 0.85, 1.0]), (n, 1))
        eye_a = np.full(n, 0.28)
        calm = np.array([m in ("DOG FREEZE", "CREEP") for m in modes])
        eye_a[calm] = 0.07                         # "face lights dim" around the dogs
        eye[alarm > 0] = red
        eye_a[alarm > 0] = 0.6 * strobe[alarm > 0] + 0.1
        done = np.array([m == "DELIVERED" for m in modes])
        eye[done] = MODE_COLOURS["done"]
        blink = (np.mod(t, 4.3) < 0.12) & ~done
        key_colour(R["eyes"], np.c_[eye, eye_a])
        U.key(R["eyes"], "scale", np.where(blink, 0.15, 1.0), index=2)
    v = np.array(rec["r_v"])
    braking = np.r_[0.0, np.diff(v)] < -0.012
    key_colour(R["taillight"], col_series(n, (1.0, 0.04, 0.02), np.where(braking | (alarm > 0), 0.7, 0.14)))
    key_colour(R["headlight"], col_series(n, (1.0, 0.95, 0.85), np.where(alarm > 0, 0.9 * strobe, 0.14)))
    if "lidar" in R:
        U.key(R["lidar"], "rotation_euler", t * 2 * PI * 0.9, index=2, decimate=False)
        R["sweep"].color = (0.1, 0.9, 1.0, 0.055)
        R["range"].color = (0.1, 0.9, 1.0, 0.09)
    U.key(R["flag"], "rotation_euler", 0.25 * np.sin(t * 7.0) + 0.6 * np.clip(v, 0, 2) / 2, index=2, decimate=False)
    deter = np.array(rec["r_deter"], float)
    deter = np.convolve(np.r_[np.zeros(8), deter, np.zeros(8)], np.ones(9) / 9, mode="same")[8:-8]
    for k, ob in enumerate(R["deter"]):              # "freeze / calm" pulse: a HUD marker, not an emission
        ob.color = (1.0, 0.62, 0.12, 0.0)
        sc, al = ring_series(t, deter, 1.7, k, 4, 0.55, 2.3, 0.42)
        key_tf(ob, scale=sc)
        U.key(ob, "color", al, index=3)
    for k, ob in enumerate(R["siren"]):
        sc, al = ring_series(t, alarm, 0.8, k, 4, 0.35, 2.4, 0.9)
        key_tf(ob, scale=sc)
        U.key(ob, "color", al, index=3)
    U.key(R["alarmlight"].data, "energy", 350.0 * alarm * strobe)
    a_on = np.nonzero(alarm)[0]
    fl = np.zeros(n)
    if len(a_on):
        fl[a_on[0]:a_on[0] + 3] = 4000.0
    U.key(R["flash"].data, "energy", fl, interp="CONSTANT")


def animate_bag(bag, rec, t):
    b = np.array(rec["bag"])
    h = np.array(rec["r_h"])
    key_tf(bag, loc=b, rot=np.c_[np.zeros(len(t)), np.zeros(len(t)), h])


# ----------------------------------------------------------------------------------------------- animals & people
def animate_dog(D, rows, t):
    n = len(t)
    x = np.array([r[0] for r in rows])
    y = np.array([r[1] for r in rows])
    h = np.array([r[2] for r in rows])
    lie = np.array([r[3] for r in rows])
    ph = np.array([r[4] for r in rows])
    bark = np.array([r[5] for r in rows])
    v = np.array([r[6] for r in rows])
    st = [r[7] for r in rows]
    key_tf(D["root"], loc=np.c_[x, y, ground(x, y)], rot=np.c_[np.zeros(n), np.zeros(n), h])
    vs = np.convolve(v, np.ones(7) / 7, mode="same")
    amp = np.where(vs > 0.05, np.minimum(0.62, 0.16 + 0.15 * vs), 0.0)
    key_tf(D["pelvis"], loc=np.c_[np.zeros(n), np.zeros(n), -0.30 * lie + (1 - lie) * 0.02 * np.abs(np.sin(ph))],
           rot=np.c_[np.zeros(n), 0.04 * np.sin(2 * ph) * (vs > 0.05), np.zeros(n)])
    for leg, off, lying in zip(D["legs"], (0, PI, PI, 0), (-1.45, -1.45, -1.25, -1.25)):
        U.key(leg, "rotation_euler", (1 - lie) * amp * np.sin(ph + off) + lie * lying, index=1)
    U.key(D["head"], "rotation_euler", -0.35 * bark + 0.35 * lie, index=1)
    agit = np.array([s in ("ALERT", "CHASE") for s in st], float)
    agit = np.convolve(agit, np.ones(9) / 9, mode="same")
    wag = (0.12 + 0.35 * agit) * np.sin(t * (4 + 12 * agit))
    key_tf(D["tail"], rot=np.c_[np.zeros(n), -0.6 * (1 - lie) + 1.0 * lie, wag])
    s = np.where(bark > 0.02, 0.25 + 0.9 * (1 - bark), 0.001)
    key_tf(D["bark"], scale=np.c_[s, s, s])
    U.key(D["bark"], "color", bark * 0.9, index=3)


def animate_glb_dog(D, rows, t, min_len=10, blend=4):
    """Drive an imported Quaternius dog: the root follows the sim, NLA strips pick the clip from the sim state and
    play it at a rate matched to ground speed (no foot sliding). Two tracks alternate so cuts can cross-fade."""
    n = len(t)
    x = np.array([r[0] for r in rows])
    y = np.array([r[1] for r in rows])
    h = np.array([r[2] for r in rows])
    bark = np.array([r[5] for r in rows])
    v = np.convolve(np.array([r[6] for r in rows]), np.ones(9) / 9, mode="same")
    st = [r[7] for r in rows]
    key_tf(D["root"], loc=np.c_[x, y, ground(x, y)], rot=np.c_[np.zeros(n), np.zeros(n), h])
    barking = np.convolve((bark > 0.2).astype(float), np.ones(15), mode="same") > 0
    clips = []
    for k in range(n):
        if st[k] == "REST":
            c = D["rest"]
        elif v[k] >= 0.9:
            c = "Gallop"
        elif v[k] >= 0.15:
            c = "Walk"
        elif barking[k]:
            c = "Attack"
        else:
            c = "Idle"
        clips.append(c if c in D["acts"] else "Idle")
    segs = []
    for k, c in enumerate(clips):
        if segs and segs[-1][0] == c:
            segs[-1][2] = k + 1
        else:
            segs.append([c, k, k + 1])
    merged = []
    for s in segs:                                   # absorb flickers shorter than min_len into the previous clip
        if merged and (s[2] - s[1] < min_len or merged[-1][0] == s[0]):
            merged[-1][2] = s[2]
        else:
            merged.append(s)
    if len(merged) > 1 and merged[0][2] - merged[0][1] < min_len:
        merged[1][1] = 0
        merged.pop(0)
    ad = D["arm"].animation_data or D["arm"].animation_data_create()
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    ad.action = None
    tracks = [ad.nla_tracks.new(), ad.nla_tracks.new()]
    for j, (c, f0, f1) in enumerate(merged):
        act = D["acts"][c]
        L = max(1.0, act.frame_range[1] - act.frame_range[0])
        vm = float(np.mean(v[f0:f1]))
        rate = (np.clip(vm / D["walk_v"], 0.6, 2.4) if c == "Walk" else
                np.clip(vm / D["run_v"], 0.7, 2.6) if c == "Gallop" else 1.0)
        upper = j % 2 == 1
        start = f0 + 1 - (blend if upper else 0)
        end = f1 + 1 + (blend if (j < len(merged) - 1 and not upper) else 0) + (blend if upper else 0)
        try:
            s = tracks[j % 2].strips.new(f"{c}_{j}", int(start), act)
        except Exception as e:
            print("NLA strip skipped:", c, f0, f1, e)
            continue
        if hasattr(s, "action_slot") and len(act.slots):
            s.action_slot = act.slots[0]
        s.scale = 1.0 / float(rate)
        s.repeat = max(0.05, (end - start) / (L * s.scale))
        s.extrapolation = "NOTHING"
        s.blend_type = "REPLACE"
        s.use_auto_blend = False
        s.blend_in = s.blend_out = blend if upper else 0
    sc = np.where(bark > 0.02, 0.25 + 0.9 * (1 - bark), 0.001)
    key_tf(D["bark"], scale=np.c_[sc, sc, sc])
    U.key(D["bark"], "color", bark * 0.9, index=3)
    return merged


def animate_person(P, rows, t, extra_lean=None):
    n = len(t)
    a = np.array([r[:10] for r in rows], float)
    x, y, h, ph, arm, grab, phone, wave, v, vis = a.T
    key_tf(P["root"], loc=np.c_[x, y, ground(x, y)], rot=np.c_[np.zeros(n), np.zeros(n), h],
           scale=np.repeat(vis[:, None], 3, 1))
    vs = np.convolve(v, np.ones(5) / 5, mode="same")
    A = np.clip(vs / 1.3, 0, 1) * np.where(vs > 3.0, 0.75, 0.48)
    lean = 0.25 * arm + 0.6 * grab + np.where(vs > 3.0, 0.25, 0.0)
    key_tf(P["hip"], loc=np.c_[np.zeros(n), np.zeros(n), 0.92 - 0.22 * grab - 0.05 * arm + 0.03 * np.abs(np.cos(ph)) * A],
           rot=np.c_[np.zeros(n), lean, np.zeros(n)])
    for leg, sgn in zip(P["legs"], (1, -1)):
        U.key(leg, "rotation_euler", sgn * A * np.sin(ph) - 0.35 * grab, index=1)
    for arm_ob, sgn in zip(P["arms"], (1, -1)):
        swing = -0.8 * sgn * A * np.sin(ph)
        ry = swing * (1 - np.clip(arm + grab, 0, 1)) - 1.15 * arm - 0.55 * grab
        rx = np.zeros(n)
        if sgn < 0:
            ry = ry * (1 - phone) - 1.25 * phone
            ry = ry * (1 - wave)
            rx = (-2.5 + 0.35 * np.sin(t * 13)) * wave
        key_tf(arm_ob, rot=np.c_[rx, ry, np.zeros(n)])
    key_tf(P["phone"], scale=np.repeat(np.maximum(phone, 0.001)[:, None], 3, 1))


def walker_rows(t, x0, y, speed, x_min, x_max, phase0=0.0):
    """Ambient pedestrian looping along the shoulder."""
    span = x_max - x_min
    d = (speed * t + phase0) % span
    x = x_min + d if speed > 0 else x_max - d
    h = 0.0 if speed > 0 else PI
    ph = np.abs(speed) * t / 1.25 * 2 * PI
    return [[xx, y, h, p, 0, 0, 0, 0, abs(speed), 1.0] for xx, p in zip(x, ph)]


# ----------------------------------------------------------------------------------------------- HUD effects (India-adapted robot only)
def path_ribbon(sim, rec, t):
    P = sim.path
    m = bpy.data.materials.new("PathRibbon")
    nt = m.node_tree
    for nd in list(nt.nodes):
        if nd.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(nd)
    out = next(nd for nd in nt.nodes if nd.type == "OUTPUT_MATERIAL")
    attr = U.nn(nt, "ShaderNodeAttribute", -1200, 0, attribute_name="pathS", attribute_type="GEOMETRY")
    s = attr.outputs["Fac"]
    vals = {}
    for i, nm in enumerate(("S0", "S1", "FLOW")):
        vn = U.nn(nt, "ShaderNodeValue", -1200, -200 - 120 * i)
        vn.name = nm
        vals[nm] = vn.outputs[0]
    head = U.math_node(nt, "SUBTRACT", s, vals["S0"], -1000, 0)
    fin = U.nn(nt, "ShaderNodeMapRange", -850, 0)
    nt.links.new(head, fin.inputs["Value"])
    fin.inputs["From Min"].default_value, fin.inputs["From Max"].default_value = 0.0, 0.5
    tail = U.math_node(nt, "SUBTRACT", vals["S1"], s, -1000, -250)
    fout = U.nn(nt, "ShaderNodeMapRange", -850, -250)
    nt.links.new(tail, fout.inputs["Value"])
    fout.inputs["From Min"].default_value, fout.inputs["From Max"].default_value = 0.0, 2.5
    win = U.math_node(nt, "MULTIPLY", fin.outputs["Result"], fout.outputs["Result"], -650, -100)
    flow = U.math_node(nt, "FRACT", U.math_node(nt, "MULTIPLY", U.math_node(nt, "SUBTRACT", s, vals["FLOW"], -1000, -500), 2.2, -850, -500), None, -700, -500)
    chev = U.math_node(nt, "ADD", U.math_node(nt, "MULTIPLY", U.math_node(nt, "LESS_THAN", flow, 0.45, -550, -500), 0.5, -420, -500), 0.5, -300, -500)
    alpha = U.math_node(nt, "MULTIPLY", U.math_node(nt, "MULTIPLY", win, chev, -250, -200), 0.85, -120, -200)
    em = U.nn(nt, "ShaderNodeEmission", -250, 150, Strength=3.0)
    em.inputs["Color"].default_value = (0.05, 0.85, 1.0, 1)
    tr = U.nn(nt, "ShaderNodeBsdfTransparent", -250, 300)
    mx = U.nn(nt, "ShaderNodeMixShader", 0, 150)
    nt.links.new(alpha, mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    m.surface_render_method = "BLENDED"
    # geometry: a 0.16 m ribbon hugging the ground (or water surface)
    k = 2
    xs, ys, ss = P.x[::k], P.y[::k], P.s[::k]
    zs = ground(xs, ys)
    wdep = W.water_depth(xs, ys)
    zs = zs + wdep + 0.025
    part = U.Part()
    part.strip(list(zip(xs, ys, zs)), 0.16, m)
    ob = U.no_shadow(part.to_object("PlannedPath", collection="FX"))
    me = ob.data
    att = me.attributes.new("pathS", "FLOAT", "POINT")
    n = len(xs)
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    # vertices were created left-row then right-row per sample; recover s by nearest sample along x,y
    idx = np.clip(np.searchsorted(ss, 0), 0, n - 1)
    d2 = (co[:, None, 0] - xs[None, :]) ** 2 + (co[:, None, 1] - ys[None, :]) ** 2
    att.data.foreach_set("value", ss[np.argmin(d2, axis=1)].astype(np.float32))
    rs = np.array(rec["r_s"])
    nt_anim = nt
    U.key(nt_anim, 'nodes["S0"].outputs[0].default_value', rs + 0.45)
    U.key(nt_anim, 'nodes["S1"].outputs[0].default_value', rs + 8.0)
    U.key(nt_anim, 'nodes["FLOW"].outputs[0].default_value', t * 1.6, decimate=False)
    return ob


def pothole_markers(sim, cam_proxy, t):
    n = len(t)
    for i, p in enumerate(W.POTHOLES):
        st = sim.ph_state[i]
        if st["detect_f"] is None:
            continue
        ring = []
        for kk in range(72):
            th = 2 * PI * kk / 72
            rr = p.rim_radius(th) + 0.06
            x, y = p.cx + rr * math.cos(th), p.cy + rr * math.sin(th)
            ring.append((x, y, float(ground(x, y)) + 0.03))
        part = U.Part()
        part.strip(ring, 0.05, U.mat_fx(), closed=True)
        wet = p.water > 0 and p.depth <= 0.06
        colr = (0.15, 1.0, 0.35) if wet else (1.0, 0.12, 0.05)
        ob = U.no_shadow(part.to_object(f"PotholeMark{i}", collection="FX", color=(*colr, 0.0)))
        f0, f1 = st["detect_f"], st["pass_f"] or n
        a = np.clip((np.arange(n) - f0) / 8.0, 0, 1) * np.clip(1 - (np.arange(n) - f1) / 15.0, 0, 1) * 0.95
        U.key(ob, "color", a, index=3)
        label = (f"WATER {p.water * 100:.1f} cm  OK" if wet else
                 f"-{p.depth * 100:.0f} cm" + (" + WATER" if p.water > 0 else ""))
        tx = U.text(label, 0.22, "bold", loc=(p.cx, p.cy, 0.55), color=(*colr, 0.0), collection="FX", mat=U.mat_fx(),
                    extrude=0.0)
        U.no_shadow(tx)
        con = tx.constraints.new("TRACK_TO")
        con.target, con.track_axis, con.up_axis = cam_proxy, "TRACK_Z", "UP_Y"
        U.key(tx, "color", a, index=3)


def detection_box(name, size, colour, label, cam_proxy):
    part = U.Part()
    part.box((1, 1, 1), (0, 0, 0), U.mat_fx())
    ob = part.to_object(name, collection="FX", color=(*colour, 0.0))
    mod = ob.modifiers.new("wire", "WIREFRAME")
    mod.thickness = 0.025
    mod.use_replace = True
    mod.use_even_offset = False
    U.no_shadow(ob)
    tx = U.text(label, 0.16, "bold", color=(*colour, 0.0), collection="FX", mat=U.mat_fx(), extrude=0.0)
    con = tx.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = cam_proxy, "TRACK_Z", "UP_Y"
    U.no_shadow(tx)
    return ob, tx, size


def animate_box(box, xs, ys, hs, vis, t):
    ob, tx, size = box
    n = len(t)
    vis = np.convolve(np.asarray(vis, float), np.ones(5) / 5, mode="same")
    z = ground(xs, ys) + size[2] / 2
    key_tf(ob, loc=np.c_[xs, ys, z], rot=np.c_[np.zeros(n), np.zeros(n), hs],
           scale=np.c_[np.full(n, size[0]), np.full(n, size[1]), np.full(n, size[2])])
    U.key(ob, "color", 0.85 * vis, index=3)
    key_tf(tx, loc=np.c_[xs, ys, z + size[2] / 2 + 0.18])
    U.key(tx, "color", 0.95 * vis, index=3)


# ----------------------------------------------------------------------------------------------- cameras
def smooth(a, sigma):
    a = np.asarray(a, float)
    if a.ndim == 1:
        return S.gaussian_smooth(a, sigma)
    return np.stack([S.gaussian_smooth(a[:, i], sigma) for i in range(a.shape[1])], 1)


def make_camera(name, lens):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start = 0.05
    cd.clip_end = 400
    ob = bpy.data.objects.new(name, cd)
    U.coll("Cameras").objects.link(ob)
    return ob


def camera_rig(segments, robot_xyz, robot_h, n):
    """segments: list of (start_frame, kind, params). Builds one camera per segment, binds timeline markers,
    and returns the active camera position per frame (for billboard labels)."""
    sc = bpy.context.scene
    rp = np.asarray(robot_xyz, float)
    hs = smooth(np.unwrap(robot_h), 18)
    active = np.zeros((n, 3))
    bounds = [s[0] for s in segments[1:]] + [n]
    for (f0, kind, prm), f1 in zip(segments, bounds):
        cam = make_camera(f"Cam_{f0:04d}_{kind}", prm.get("lens", 30))
        lo, hi = max(0, f0 - 2), min(n, f1 + 2)
        idx = np.arange(n)
        if kind == "static":
            pos = np.tile(prm["pos"], (n, 1)).astype(float)
            if "pos1" in prm:
                u = np.clip((idx - f0) / max(1, f1 - f0), 0, 1)
                u = u * u * (3 - 2 * u)
                pos = pos + (np.asarray(prm["pos1"]) - np.asarray(prm["pos"]))[None, :] * u[:, None]
            if "track" in prm:
                tgt = prm["track"]
            else:
                tgt = np.tile(prm["target"], (n, 1)).astype(float)
        elif kind == "follow":
            pos = rp + np.asarray(prm["offset"])[None, :]
            tgt = rp + np.asarray(prm["look"])[None, :]
            pos[:, 2] = np.maximum(pos[:, 2], rp[:, 2] + 0.2)
        elif kind == "chase":
            back, up, side, ahead = prm["back"], prm["up"], prm.get("side", 0.0), prm.get("ahead", 2.5)
            fwd = np.c_[np.cos(hs), np.sin(hs), np.zeros(n)]
            lft = np.c_[-np.sin(hs), np.cos(hs), np.zeros(n)]
            pos = rp - back * fwd + side * lft + np.c_[np.zeros(n), np.zeros(n), np.full(n, up)]
            tgt = rp + ahead * fwd + np.c_[np.zeros(n), np.zeros(n), np.full(n, 0.25)]
        pos = smooth(pos, prm.get("smooth", 10))
        tgt = smooth(tgt, prm.get("smooth_t", 8))
        rot = []
        prev = None
        for p, q in zip(pos[lo:hi], tgt[lo:hi]):
            e = U.look_euler(p, q, prev)
            rot.append(tuple(e))
            prev = e
        key_tf(cam, loc=pos[lo:hi], rot=np.array(rot), start=lo + 1)
        mk = sc.timeline_markers.new(f"{kind}_{f0}", frame=f0 + 1)
        mk.camera = cam
        active[f0:f1] = pos[f0:f1]
        if f0 == 0:
            sc.camera = cam
    return active


def ffirst(cond, default=0):
    i = np.nonzero(cond)[0]
    return int(i[0]) if len(i) else default


def event_f(sim, title, default=None):
    for e in sim.events:
        if e["title"].startswith(title):
            return e["f"]
    return default


def cut_list(sim, rec):
    """Camera plan for each shot, derived from where the action actually happens in this run."""
    n = len(rec["t"])
    x = np.array(rec["r_x"])
    y = np.array(rec["r_y"])
    name = sim.name
    rp = np.c_[x, y, np.array(rec["r_z"])]
    if name == "bharat_full":
        fd = event_f(sim, "3 street dogs")
        fdo = event_f(sim, "Back to cruise")
        fc = event_f(sim, "Cow standing", ffirst(x > 42))
        fco = event_f(sim, "Gap clear", fc + 120)
        ft = event_f(sim, "Person stepping")
        fa = event_f(sim, "THEFT ALARM")
        ff = event_f(sim, "Thief fled")
        fr = event_f(sim, "Arrived at the gate")
        xa = x[fa]
        dog_c = np.mean([[r[0], r[1]] for r in rec["d0"]], 0)
        mid_dogs = np.c_[(x + 36.5) / 2, (y + 4.9) / 2, np.full(n, 0.55)]
        mid_cow = np.c_[(x + W.COW[0]) / 2 + 1.0, (y + W.COW[1]) / 2, np.full(n, 0.6)]
        return [
            (0, "static", dict(pos=(-7.4, -0.9, 2.5), pos1=(-5.6, -0.4, 2.3), target=(0.4, 4.4, 0.8), lens=26)),
            (ffirst(x > 3.0), "follow", dict(offset=(-4.0, -2.8, 4.6), look=(2.8, -0.3, 0.0), lens=24, smooth=14)),
            (ffirst(x > 21.0), "follow", dict(offset=(0.9, -2.35, 0.55), look=(0.25, 0.0, 0.18), lens=30, smooth=8)),
            (ffirst(x > 30.4), "chase", dict(back=3.6, up=1.7, side=-0.5, lens=30)),
            (fd - 8, "static", dict(pos=(35.4, -1.0, 1.8), track=smooth(mid_dogs, 25), lens=25, smooth=2)),
            (fdo, "chase", dict(back=3.8, up=1.8, side=-0.6, lens=30)),
            (fc - 12, "static", dict(pos=(40.2, 0.30, 2.2), track=smooth(mid_cow, 25), lens=27, smooth=2)),
            (fco + 70, "chase", dict(back=3.8, up=1.8, side=-0.6, lens=30)),
            (ft, "static", dict(pos=(xa + 2.9, 0.75, 1.45), target=(xa - 0.1, 3.4, 0.7), lens=28)),
            (ff + 40, "chase", dict(back=3.8, up=1.9, side=-0.7, lens=30)),
            (fr - 75, "static", dict(pos=(61.3, 2.4, 1.65), pos1=(62.1, 3.2, 1.5), target=(64.6, 6.4, 0.9), lens=30)),
        ]
    if name == "baseline_pothole":
        return [(0, "follow", dict(offset=(2.3, -2.1, 0.85), look=(-0.1, 0.0, 0.05), lens=32, smooth=10))]
    if name == "baseline_dogs":
        mid = np.c_[(x + 36.5) / 2, (y + 4.6) / 2, np.full(n, 0.5)]
        return [(0, "static", dict(pos=(36.3, -1.4, 1.9), track=smooth(mid, 25), lens=26, smooth=2))]
    if name == "baseline_theft":
        trk = np.c_[x, y, np.full(n, 0.6)]
        return [(0, "static", dict(pos=(56.4, 0.4, 1.55), track=smooth(trk, 20), lens=27, smooth=2))]
    raise ValueError(name)


# ----------------------------------------------------------------------------------------------- shots
def build_sim_shot(name):
    sim = S.run(name)
    rec = sim.rec
    n = len(rec["t"])
    t = np.array(rec["t"])
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, n
    E.build_india_street()
    lighting(sc)
    R = C.build_robot(sim.sc["robot"], "Robot")
    animate_robot(R, rec, t)
    if name == "bharat_full":
        bag = C.build_bag()
        animate_bag(bag, rec, t)
    fur = [(0.55, 0.33, 0.15), (0.07, 0.055, 0.045), (0.82, 0.74, 0.6)]
    dogs = []
    use_glb = C.glb_dog_available()
    for i in range(3):
        if use_glb:
            D = C.build_glb_dog(i, f"Dog{i}")
            segs = animate_glb_dog(D, rec[f"d{i}"], t)
            print(f"Dog{i} clips:", " ".join(f"{c}@{f0}" for c, f0, f1 in segs), flush=True)
        else:
            D = C.build_dog(f"Dog{i}", fur[i])
            animate_dog(D, rec[f"d{i}"], t)
        dogs.append(D)
    cx, cy, chd = W.COW
    cow = C.build_glb_cow(n_frames=n) if use_glb else C.build_cow()
    cow["root"].location = (cx, cy, float(ground(cx, cy)))
    cow["root"].rotation_euler = (0, 0, chd)
    if not use_glb:
        U.key(cow["head"], "rotation_euler", 0.18 + 0.06 * np.sin(t * 2.3), index=1, decimate=False)
        U.key(cow["head"], "rotation_euler", 0.2 * np.sin(t * 0.37), index=2, decimate=False)
        U.key(cow["tail"], "rotation_euler", 0.35 * np.sin(t * 2.6) + 0.1 * np.sin(t * 7.1), index=0, decimate=False)
    thief = C.build_person("Thief", (0.07, 0.07, 0.085), (0.04, 0.045, 0.06), style="hoodie")
    animate_person(thief, rec["thief"], t)
    cust = C.build_person("Customer", (0.42, 0.62, 0.85), (0.72, 0.66, 0.52), skin=(0.46, 0.30, 0.19))
    animate_person(cust, rec["cust"], t)
    auto = C.build_auto()
    au = np.array([r for r in rec["auto"]], float)
    key_tf(auto["root"], loc=np.c_[au[:, 0], au[:, 1], ground(au[:, 0], au[:, 1])],
           rot=np.c_[np.zeros(n), np.zeros(n), au[:, 2]], scale=np.repeat(au[:, 4:5], 3, 1))
    for wob in auto["wheels"]:
        U.key(wob, "rotation_euler", au[:, 3], index=1)
    # ambient pedestrians on the far shoulder
    for i, (spec, y0, sp, ph0) in enumerate(((("Walker0", (0.85, 0.85, 0.82), (0.2, 0.2, 0.25), "man"), -5.0, -1.15, 10.0),
                                            (("Walker1", (0.75, 0.1, 0.4), (0.75, 0.1, 0.4), "saree"), -5.35, 0.95, 30.0))):
        nm, shirt, pants, style = spec
        P = C.build_person(nm, shirt, pants, skin=(0.36 + 0.06 * i, 0.23, 0.15), style=style)
        animate_person(P, walker_rows(t, 0, y0, sp, -10.0, 78.0, ph0), t)
    rp = np.c_[np.array(rec["r_x"]), np.array(rec["r_y"]), np.array(rec["r_z"])]
    active = camera_rig(cut_list(sim, rec), rp, np.array(rec["r_h"]), n)
    proxy = U.empty("CamProxy", collection="Cameras", size=0.1)
    key_tf(proxy, loc=active)
    if sim.cfg["sees_potholes"]:
        path_ribbon(sim, rec, t)
        pothole_markers(sim, proxy, t)
        boxes = []
        rx, ry = np.array(rec["r_x"]), np.array(rec["r_y"])
        for i in range(3):
            d = np.array([r[:3] for r in rec[f"d{i}"]], float)
            st = [r[7] for r in rec[f"d{i}"]]
            vis = np.array([s in ("ALERT", "CHASE", "RETREAT") for s in st]) & (np.hypot(d[:, 0] - rx, d[:, 1] - ry) < 8.5)
            b = detection_box(f"DetDog{i}", (0.9, 0.42, 0.78), (1.0, 0.6, 0.05), "DOG 0.9" + str(4 + i), proxy)
            animate_box(b, d[:, 0], d[:, 1], d[:, 2], vis, t)
        th = np.array([r[:3] for r in rec["thief"]], float)
        tst = [r[10] for r in rec["thief"]]
        vis = np.array([s not in ("WAIT", "GONE") for s in tst]) & (np.hypot(th[:, 0] - rx, th[:, 1] - ry) < 9)
        b = detection_box("DetPerson", (0.6, 0.6, 1.9), (1.0, 0.15, 0.6), "PERSON 0.97", proxy)
        animate_box(b, th[:, 0], th[:, 1], th[:, 2], vis, t)
        vis = (rx > W.COW[0] - 13) & (rx < W.COW[0] + 1.5)
        b = detection_box("DetCow", (2.6, 0.95, 1.55), (1.0, 0.85, 0.1), "COW 0.99", proxy)
        animate_box(b, np.full(n, W.COW[0]), np.full(n, W.COW[1]), np.full(n, W.COW[2]), vis, t)
        vis = (au[:, 4] > 0) & (np.hypot(au[:, 0] - rx, au[:, 1] - ry) < 30) & (au[:, 0] < rx + 6)
        b = detection_box("DetAuto", (2.9, 1.5, 1.95), (0.3, 0.6, 1.0), "AUTO-RICKSHAW 0.96", proxy)
        animate_box(b, au[:, 0], au[:, 1], au[:, 2], vis, t)
    return sim


def build_us_shot():
    sc = bpy.context.scene
    n = int(6.0 * FPS)
    t = np.arange(n) / FPS
    sc.frame_start, sc.frame_end = 1, n
    E.build_us_street()
    lighting(sc, us=True)
    R = C.build_robot("baseline", "Robot")
    v = np.minimum(1.6, 0.8 * t + 1.2)
    s = np.cumsum(v) / FPS
    x = -4.0 + s
    y = np.full(n, 6.1)
    z = np.full(n, 0.1 + R["r"])
    zero = np.zeros(n)
    rec = {"r_x": x, "r_y": y, "r_z": z, "r_h": zero, "r_pitch": zero, "r_roll": zero, "r_vis": np.ones(n),
           "r_lid": zero, "r_lidj": zero, "r_spin": np.c_[s / R["r"], s / R["r"]], "r_dz": np.zeros((n, 6)),
           "r_mode": ["CRUISE"] * n, "r_alarm": zero, "r_v": v, "r_deter": zero}
    animate_robot(R, rec, t)
    P = C.build_person("Jogger", (0.2, 0.35, 0.7), (0.15, 0.15, 0.18))
    animate_person(P, walker_rows(t, 0, -6.1, -1.3, -10, 30, 22.0), t)
    rp = np.c_[x, y, z]
    camera_rig([(0, "follow", dict(offset=(2.2, -6.4, 1.7), look=(0.9, 0.6, 0.35), lens=30, smooth=6))], rp, zero, n)
    return None


def main():
    a = args()
    t0 = time.time()
    sc = reset()
    sim = build_us_shot() if a.shot == "us_sidewalk" else build_sim_shot(a.shot)
    render_settings(sc, a.res, a.samples, a.raytrace)
    print(f"BUILD {a.shot}: {sc.frame_end} frames, {len(bpy.data.objects)} objects, {time.time() - t0:.1f} s", flush=True)
    if a.save:
        path = os.path.join(ROOT, a.save) if not os.path.isabs(a.save) else a.save
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            bpy.ops.file.pack_all()
        except Exception:
            pass
        bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
        print("SAVED", path, flush=True)
    out = a.out or os.path.join(ROOT, "renders", a.shot)
    if not os.path.isabs(out):
        out = os.path.join(ROOT, out)
    os.makedirs(out, exist_ok=True)
    stamp = {}

    def pre(scene, *_):
        stamp["t"] = time.time()

    def post(scene, *_):
        print(f"FRAME {scene.frame_current} {time.time() - stamp['t']:.2f}s", flush=True)

    bpy.app.handlers.render_pre.append(pre)
    bpy.app.handlers.render_post.append(post)
    if a.stills:
        for f in (int(v) for v in a.stills.split(",")):
            sc.frame_set(f)
            sc.render.filepath = os.path.join(out, f"still_{f:04d}.jpg")
            bpy.ops.render.render(write_still=True)
    if a.render:
        if a.frames:
            f0, f1 = (int(v) for v in a.frames.split("-"))
            sc.frame_start, sc.frame_end = f0, f1
        sc.render.filepath = os.path.join(out, "f_")
        bpy.ops.render.render(animation=True)
    print(f"DONE in {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
