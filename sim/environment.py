"""Street environments: a broken Indian street (the real test) and a smooth US suburban sidewalk (the contrast).

The Indian street's road surface is built from world.terrain_height, the same function the simulator drives on,
so the robot's wheels touch exactly the potholes you see.
"""
import math
import random

import bpy
import numpy as np
from mathutils import Vector

import world as W
from bpy_utils import (Part, coll, curve_line, empty, find_tex, grid_object, mat_flat, mat_obj, mat_wall, mat_water,
                       math_node, mix, nn, no_shadow, tex, text)
from characters import M, build_car, build_scooter

PI = math.pi


# ----------------------------------------------------------------------------------------------- road surface
def mat_terrain():
    m = bpy.data.materials.new("StreetSurface")
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    L = nt.links.new
    tc = nn(nt, "ShaderNodeTexCoord", -2200, 0)
    obj = tc.outputs["Object"]
    zone = nn(nt, "ShaderNodeAttribute", -2200, 500, attribute_name="zone", attribute_type="GEOMETRY")
    sep = nn(nt, "ShaderNodeSeparateColor", -2000, 500)
    L(zone.outputs["Color"], sep.inputs[0])
    pot, wet, dirt = sep.outputs[0], sep.outputs[1], sep.outputs[2]

    def noise(scale, detail, x, y, rough=0.55):
        n = nn(nt, "ShaderNodeTexNoise", x, y, Scale=scale, Detail=detail, Roughness=rough)
        L(obj, n.inputs["Vector"])
        return n.outputs["Fac"]

    def ramp(fac, c0, c1, x, y, p0=0.3, p1=0.7):
        r = nn(nt, "ShaderNodeValToRGB", x, y)
        r.color_ramp.elements[0].position, r.color_ramp.elements[0].color = p0, (*c0, 1)
        r.color_ramp.elements[1].position, r.color_ramp.elements[1].color = p1, (*c1, 1)
        L(fac, r.inputs["Fac"])
        return r.outputs["Color"]

    big = noise(0.22, 3, -1900, 200)
    mid = noise(3.2, 7, -1900, -100)
    asphalt = ramp(big, (0.032, 0.031, 0.030), (0.085, 0.079, 0.072), -1650, 200)
    vor = nn(nt, "ShaderNodeTexVoronoi", -1900, -400, Scale=48.0)
    L(obj, vor.inputs["Vector"])
    speck = nn(nt, "ShaderNodeMapRange", -1650, -400)
    L(vor.outputs["Distance"], speck.inputs["Value"])
    speck.inputs["From Min"].default_value, speck.inputs["From Max"].default_value = 0.0, 0.18
    speck.inputs["To Min"].default_value, speck.inputs["To Max"].default_value = 0.5, 0.0
    asphalt = mix(nt, speck.outputs["Result"], asphalt, (0.21, 0.19, 0.17), "MIX", -1400, 150)
    patchn = noise(0.11, 2, -1900, 500)
    patch = nn(nt, "ShaderNodeMapRange", -1650, 500)
    L(patchn, patch.inputs["Value"])
    patch.inputs["From Min"].default_value, patch.inputs["From Max"].default_value = 0.58, 0.60
    asphalt = mix(nt, math_node(nt, "MULTIPLY", patch.outputs["Result"], 0.85, -1400, 500), asphalt,
                  (0.03, 0.03, 0.032), "MIX", -1200, 300)
    crk = nn(nt, "ShaderNodeTexVoronoi", -1900, -700, Scale=1.9, feature="DISTANCE_TO_EDGE")
    L(obj, crk.inputs["Vector"])
    crack = nn(nt, "ShaderNodeMapRange", -1650, -700)
    L(crk.outputs["Distance"], crack.inputs["Value"])
    crack.inputs["From Min"].default_value, crack.inputs["From Max"].default_value = 0.0, 0.014
    crack.inputs["To Min"].default_value, crack.inputs["To Max"].default_value = 1.0, 0.0
    cmask = nn(nt, "ShaderNodeMapRange", -1650, -950)
    L(noise(0.35, 2, -1900, -950), cmask.inputs["Value"])
    cmask.inputs["From Min"].default_value, cmask.inputs["From Max"].default_value = 0.5, 0.62
    crack_f = math_node(nt, "MULTIPLY", crack.outputs["Result"], cmask.outputs["Result"], -1400, -800)
    asphalt = mix(nt, crack_f, asphalt, (0.012, 0.012, 0.012), "MIX", -1000, 150)
    # speed breaker: lighter, older concrete-like asphalt
    sepx = nn(nt, "ShaderNodeSeparateXYZ", -1900, 800)
    L(obj, sepx.inputs[0])
    dx = math_node(nt, "ABSOLUTE", math_node(nt, "SUBTRACT", sepx.outputs["X"], W.SPEED_BREAKER_X, -1700, 800), None, -1550, 800)
    sbm = nn(nt, "ShaderNodeMapRange", -1400, 800)
    L(dx, sbm.inputs["Value"])
    sbm.inputs["From Min"].default_value, sbm.inputs["From Max"].default_value = 0.38, 0.47
    sbm.inputs["To Min"].default_value, sbm.inputs["To Max"].default_value = 0.85, 0.0
    asphalt = mix(nt, sbm.outputs["Result"], asphalt, (0.21, 0.20, 0.19), "MIX", -850, 300)
    # dirt shoulder (laterite) and pothole mud
    dirt_col = ramp(mid, (0.17, 0.095, 0.05), (0.34, 0.19, 0.10), -1650, -200)
    dirt_col = mix(nt, speck.outputs["Result"], dirt_col, (0.42, 0.33, 0.26), "MIX", -1400, -200)
    mud = ramp(mid, (0.075, 0.058, 0.04), (0.19, 0.14, 0.095), -1650, -1150)
    col = mix(nt, dirt, asphalt, dirt_col, "MIX", -700, 100)
    col = mix(nt, math_node(nt, "MULTIPLY", pot, 0.92, -900, -300), col, mud, "MIX", -500, 100)
    darker = mix(nt, 1.0, col, (0.42, 0.42, 0.42), "MULTIPLY", -500, -150)
    col = mix(nt, math_node(nt, "MULTIPLY", wet, 0.8, -700, -300), col, darker, "MIX", -300, 100)
    L(col, p.inputs["Base Color"])
    rough = nn(nt, "ShaderNodeMapRange", -500, -500)
    L(wet, rough.inputs["Value"])
    rough.inputs["To Min"].default_value, rough.inputs["To Max"].default_value = 0.9, 0.22
    L(rough.outputs["Result"], p.inputs["Roughness"])
    h = math_node(nt, "ADD", math_node(nt, "MULTIPLY", mid, 0.6, -900, -600), speck.outputs["Result"], -700, -600)
    h = math_node(nt, "SUBTRACT", h, crack_f, -550, -650)
    bump = nn(nt, "ShaderNodeBump", -300, -500, Strength=0.32, Distance=0.02)
    L(h, bump.inputs["Height"])
    L(bump.outputs["Normal"], p.inputs["Normal"])
    return m


def mat_terrain_textured():
    """Poly Haven maps: asphalt_02 (grey, cracked) with road_damaged_2 dust/patches, red laterite shoulders and
    gravelly mud in potholes, all blended by the same 'zone' masks the simulator's terrain produced."""
    m = bpy.data.materials.new("StreetSurface")
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    L = nt.links.new
    tc = nn(nt, "ShaderNodeTexCoord", -2600, 0)
    obj = tc.outputs["Object"]
    zone = nn(nt, "ShaderNodeAttribute", -2600, 600, attribute_name="zone", attribute_type="GEOMETRY")
    sep = nn(nt, "ShaderNodeSeparateColor", -2400, 600)
    L(zone.outputs["Color"], sep.inputs[0])
    pot, wet, dirt = sep.outputs[0], sep.outputs[1], sep.outputs[2]

    def mapping(size, rot, y):
        mp = nn(nt, "ShaderNodeMapping", -2400, y)
        mp.inputs["Scale"].default_value = (1 / size, 1 / size, 1 / size)
        mp.inputs["Rotation"].default_value = (0, 0, rot)
        L(obj, mp.inputs["Vector"])
        return mp.outputs[0]

    va, vd, vm, vr = mapping(3.0, 0.0, 300), mapping(2.0, 0.4, -300), mapping(1.5, 0.9, -800), mapping(2.2, 1.3, 800)
    a_d = tex(nt, "asphalt_02", "diff", va, -2100, 400)
    a_r = tex(nt, "asphalt_02", "rough", va, -2100, 150, noncolor=True)
    a_h = tex(nt, "asphalt_02", "disp", va, -2100, -50, noncolor=True)
    r_d = tex(nt, "road_damaged_2", "diff", vr, -2100, 800)
    d_d = tex(nt, "red_laterite_soil_stones", "diff", vd, -2100, -300)
    d_r = tex(nt, "red_laterite_soil_stones", "rough", vd, -2100, -500, noncolor=True)
    d_h = tex(nt, "red_laterite_soil_stones", "disp", vd, -2100, -700, noncolor=True)
    m_d = tex(nt, "red_dirt_mud_01", "diff", vm, -2100, -950)
    m_h = tex(nt, "red_dirt_mud_01", "disp", vm, -2100, -1150, noncolor=True)
    # dusty, broken patches: noise + more of it toward the road edges
    dn = nn(nt, "ShaderNodeTexNoise", -2100, 1100, Scale=0.16, Detail=3.0)
    L(obj, dn.inputs["Vector"])
    dmask = nn(nt, "ShaderNodeMapRange", -1850, 1100)
    L(dn.outputs["Fac"], dmask.inputs["Value"])
    dmask.inputs["From Min"].default_value, dmask.inputs["From Max"].default_value = 0.48, 0.66
    sxyz = nn(nt, "ShaderNodeSeparateXYZ", -2100, 1350)
    L(obj, sxyz.inputs[0])
    edge = nn(nt, "ShaderNodeMapRange", -1850, 1350)
    L(math_node(nt, "ABSOLUTE", sxyz.outputs["Y"], None, -1950, 1350), edge.inputs["Value"])
    edge.inputs["From Min"].default_value, edge.inputs["From Max"].default_value = 2.4, 3.5
    dust = math_node(nt, "ADD", math_node(nt, "MULTIPLY", dmask.outputs["Result"], 0.65, -1650, 1100),
                     math_node(nt, "MULTIPLY", edge.outputs["Result"], 0.45, -1650, 1350), -1500, 1200, clamp=True)
    asphalt = mix(nt, dust, a_d.outputs["Color"], r_d.outputs["Color"], "MIX", -1350, 600)
    asphalt = mix(nt, 1.0, asphalt, (0.78, 0.78, 0.78), "MULTIPLY", -1200, 600)
    # speed breaker: lighter, older surface
    dx = math_node(nt, "ABSOLUTE", math_node(nt, "SUBTRACT", sxyz.outputs["X"], W.SPEED_BREAKER_X, -1850, 1600), None, -1700, 1600)
    sbm = nn(nt, "ShaderNodeMapRange", -1550, 1600)
    L(dx, sbm.inputs["Value"])
    sbm.inputs["From Min"].default_value, sbm.inputs["From Max"].default_value = 0.42, 0.52
    sbm.inputs["To Min"].default_value, sbm.inputs["To Max"].default_value = 0.7, 0.0
    asphalt = mix(nt, sbm.outputs["Result"], asphalt, (0.24, 0.22, 0.2), "MIX", -1050, 600)
    col = mix(nt, dirt, asphalt, d_d.outputs["Color"], "MIX", -850, 200)
    col = mix(nt, math_node(nt, "MULTIPLY", pot, 0.95, -1000, -200), col, m_d.outputs["Color"], "MIX", -650, 200)
    darker = mix(nt, 1.0, col, (0.45, 0.45, 0.45), "MULTIPLY", -650, -50)
    col = mix(nt, math_node(nt, "MULTIPLY", wet, 0.85, -800, -250), col, darker, "MIX", -450, 200)
    L(col, p.inputs["Base Color"])
    rough = mix(nt, dirt, a_r.outputs["Color"], d_r.outputs["Color"], "MIX", -850, -400)
    rough = mix(nt, wet, rough, (0.12, 0.12, 0.12), "MIX", -650, -400)
    L(rough, p.inputs["Roughness"])
    hgt = mix(nt, dirt, a_h.outputs["Color"], d_h.outputs["Color"], "MIX", -850, -700)
    hgt = mix(nt, pot, hgt, m_h.outputs["Color"], "MIX", -650, -700)
    bump = nn(nt, "ShaderNodeBump", -400, -600, Strength=0.55, Distance=0.025)
    L(hgt, bump.inputs["Height"])
    L(bump.outputs["Normal"], p.inputs["Normal"])
    return m


def build_terrain():
    xs = np.r_[np.arange(W.X0, -4.0, 0.2), np.arange(-4.0, 74.0, 0.05), np.arange(74.0, W.X1 + 1e-6, 0.2)]
    ys = np.r_[np.arange(-W.BUILD_Y, -3.8, 0.15), np.arange(-3.8, 4.0, 0.05), np.arange(4.0, W.BUILD_Y + 1e-6, 0.12)]
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    Z = W.terrain_height(X, Y)
    pot = np.clip(W.pothole_depth(X, Y) / 0.05, 0, 1)
    wd = W.water_depth(X, Y)
    wet = np.clip(wd / 0.004, 0, 1)
    for p in W.POTHOLES:                      # damp ring just above the water line
        if p.water > 0:
            near = (np.abs(X - p.cx) < p.reach + 0.3) & (np.abs(Y - p.cy) < p.reach + 0.3)
            wl = W.water_level(p)
            wet = np.where(near, np.maximum(wet, np.clip(1 - (Z - wl) / 0.03, 0, 1) * 0.8), wet)
    dirt = 1.0 - W.road_mask(X, Y)
    col = np.stack([pot, wet, dirt, np.ones_like(pot)], -1).reshape(-1, 4)
    textured = all(find_tex(t) for t in ("asphalt_02", "road_damaged_2", "red_laterite_soil_stones", "red_dirt_mud_01"))
    ob = grid_object("StreetSurface", xs, ys, Z, collection="Street", attrs={"zone": col},
                     mat=mat_terrain_textured() if textured else mat_terrain())
    return ob


def build_water():
    """Muddy water surfaces in the potholes that hold water (outline traced where terrain meets the water level)."""
    mw = mat_water()
    p = Part()
    for ph in W.POTHOLES:
        if ph.water <= 0:
            continue
        wl = W.water_level(ph)
        ring = []
        for k in range(64):
            th = 2 * PI * k / 64
            rr = np.linspace(0.0, ph.reach, 220)
            xs, ys = ph.cx + rr * math.cos(th), ph.cy + rr * math.sin(th)
            z = W.terrain_height(xs, ys)
            above = np.nonzero(z > wl)[0]
            r = rr[above[0]] if len(above) else rr[-1]
            ring.append((ph.cx + (r + 0.01) * math.cos(th), ph.cy + (r + 0.01) * math.sin(th), wl))
        p.poly(ring, mw)
    return p.to_object("Puddles", collection="Street")


def build_road_marks():
    paint = mat_flat("RoadPaint", (0.62, 0.62, 0.58), 0.75)
    p = Part()
    for x0 in np.arange(-12.0, 82.0, 4.5):
        xs = np.linspace(x0, x0 + 1.6, 7)
        if (W.pothole_depth(xs, np.zeros_like(xs)) > 0.005).any() or abs(x0 + 0.8 - W.SPEED_BREAKER_X) < 1.5:
            continue
        pts = [(x, 0.0, float(W.terrain_height(x, 0.0)) + 0.004) for x in xs]
        p.strip(pts, 0.12, paint)
    return p.to_object("CentreLine", collection="Street")


def build_debris(seed=3):
    """Gravel in potholes, broken asphalt chunks, litter on the shoulder."""
    rng = np.random.default_rng(seed)
    stone = mat_flat("Gravel", (0.20, 0.18, 0.16), 0.9)
    chunk = mat_flat("AsphaltChunk", (0.06, 0.06, 0.065), 0.85)
    litter = [mat_flat("LitterW", (0.75, 0.75, 0.72), 0.6), mat_flat("LitterB", (0.08, 0.2, 0.55), 0.5),
              mat_flat("LitterR", (0.6, 0.1, 0.08), 0.5)]
    p = Part()
    for ph in W.POTHOLES:
        for _ in range(int(14 * ph.rx * ph.ry / 0.3)):
            a, rr = rng.uniform(0, 2 * PI), rng.uniform(0, 0.75) * ph.rim_radius(0)
            x, y = ph.cx + rr * math.cos(a) * ph.rx / max(ph.rx, ph.ry), ph.cy + rr * math.sin(a) * ph.ry / max(ph.rx, ph.ry)
            z = float(W.terrain_height(x, y))
            s = rng.uniform(0.012, 0.03)
            p.ico(s, (x, y, z + s * 0.4), stone, scale=(1, rng.uniform(0.6, 1), rng.uniform(0.5, 0.8)), rot=tuple(rng.uniform(0, 3, 3)))
        for _ in range(6):
            th = rng.uniform(0, 2 * PI)
            rr = ph.rim_radius(th) * rng.uniform(1.02, 1.25)
            x, y = ph.cx + rr * math.cos(th), ph.cy + rr * math.sin(th)
            z = float(W.terrain_height(x, y))
            s = rng.uniform(0.04, 0.09)
            p.box((s, s * rng.uniform(0.5, 1), 0.025), (x, y, z + 0.008), chunk, rot=(rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15), rng.uniform(0, 3)))
    for _ in range(140):
        side = rng.choice([1, -1])
        x, y = rng.uniform(-12, 82), side * rng.uniform(3.7, 6.1)
        z = float(W.terrain_height(x, y))
        if rng.random() < 0.6:
            s = rng.uniform(0.02, 0.05)
            p.ico(s, (x, y, z + s * 0.3), stone, scale=(1, 0.8, 0.6))
        else:
            p.box((rng.uniform(0.05, 0.15), rng.uniform(0.04, 0.1), 0.004), (x, y, z + 0.01), litter[rng.integers(3)],
                  rot=(0, 0, rng.uniform(0, 3)))
    return p.to_object("Debris", collection="Street")


# ----------------------------------------------------------------------------------------------- buildings
DETAIL = {}


def dmat(key):
    table = {"glass": ((0.03, 0.045, 0.06), 0.08), "frame": ((0.08, 0.07, 0.065), 0.6), "shutter": ((0.36, 0.37, 0.38), 0.45),
             "interior": ((0.035, 0.03, 0.028), 0.9), "concrete": ((0.36, 0.35, 0.33), 0.9), "tank": ((0.03, 0.03, 0.03), 0.5),
             "wood": ((0.22, 0.12, 0.06), 0.6), "rail": ((0.10, 0.10, 0.11), 0.4), "ac": ((0.78, 0.78, 0.76), 0.5),
             "gR": ((0.62, 0.08, 0.06), 0.6), "gY": ((0.85, 0.62, 0.05), 0.6), "gB": ((0.06, 0.22, 0.6), 0.6),
             "gG": ((0.08, 0.45, 0.12), 0.6), "gW": ((0.85, 0.85, 0.82), 0.6), "tarp": ((0.05, 0.28, 0.7), 0.7),
             "chair": ((0.75, 0.06, 0.05), 0.45), "plant": ((0.08, 0.28, 0.06), 0.8), "pot": ((0.45, 0.18, 0.08), 0.8)}
    if key not in DETAIL:
        c, r = table[key]
        DETAIL[key] = mat_flat("D_" + key, c, r)
    return DETAIL[key]


def building(x0, x1, side, floors, wall_color, sign=None, sign_color=(0.7, 0.1, 0.05), text_color=(1, 0.95, 0.85),
             kind="shop", depth=7.0, seed=0, small=None, extra=None):
    """side=+1: left of the robot (front face at y=+BUILD_Y, facing -y); side=-1: right side."""
    rng = random.Random(seed)
    fy = side * W.BUILD_Y
    out = -side                    # direction the facade faces
    H0, Hf = 3.3, 3.0
    H = H0 + Hf * (floors - 1)
    wx, cx = x1 - x0, (x0 + x1) / 2
    walls = Part()
    walls.box((wx, depth, H), (cx, fy + side * depth / 2, H / 2), mat_wall())
    walls.box((wx + 0.1, 0.25, 0.25), (cx, fy + side * 0.1, H + 0.12), mat_wall())             # parapet front
    for f in range(1, floors):
        walls.box((wx + 0.06, 0.18, 0.12), (cx, fy + out * 0.06, H0 + Hf * (f - 1) - 0.05), mat_wall())   # floor bands
    wall_ob = walls.to_object(f"Bldg_{x0:.0f}_{side}", collection="Buildings", color=wall_color)
    d = Part()
    fz = fy + out * 0.012          # just in front of the facade
    d.box((wx, 0.5, 0.22), (cx, fy + out * 0.25, 0.11), dmat("concrete"))                  # plinth / shop step
    if kind == "shop":
        d.box((wx - 0.6, 0.03, 2.45), (cx, fz, 1.47), dmat("interior"))
        d.box((wx - 0.5, 0.12, 0.55), (cx, fy + out * 0.05, 2.45), dmat("shutter"))
        for row in range(3):
            for k in range(int((wx - 1.0) / 0.45)):
                if rng.random() < 0.8:
                    d.box((0.32, 0.05, 0.28), (x0 + 0.75 + k * 0.45, fy + out * 0.04, 0.75 + row * 0.5),
                          dmat(rng.choice(["gR", "gY", "gB", "gG", "gW"])))
        d.box((wx * 0.6, 0.55, 0.9), (cx, fy + out * 0.45, 0.67), dmat("wood"))
    else:
        d.box((1.1, 0.06, 2.2), (cx - wx * 0.22, fz, 1.32), dmat("wood"))
        d.box((1.3, 0.05, 1.2), (cx + wx * 0.18, fz, 1.6), dmat("glass"))
        d.box((1.4, 0.06, 0.08), (cx + wx * 0.18, fz, 2.24), dmat("frame"))
    for f in range(1, floors):
        z = H0 + Hf * (f - 1) + 1.4
        n = max(1, int(wx / 2.6))
        for k in range(n):
            x = x0 + (k + 0.5) * wx / n
            d.box((1.2, 0.05, 1.3), (x, fz, z), dmat("glass"))
            d.box((1.32, 0.08, 0.08), (x, fz, z + 0.69), dmat("frame"))
            d.box((1.32, 0.12, 0.06), (x, fy + out * 0.06, z - 0.69), dmat("frame"))
            if rng.random() < 0.3:
                d.box((0.7, 0.45, 0.4), (x + 0.9, fy + out * 0.25, z - 0.4), dmat("ac"))
        if rng.random() < 0.6:
            bz = H0 + Hf * (f - 1) + 0.05
            d.box((wx * 0.7, 0.9, 0.12), (cx, fy + out * 0.45, bz), dmat("concrete"))
            for k in range(int(wx * 0.7 / 0.18)):
                d.box((0.02, 0.02, 0.9), (cx - wx * 0.35 + k * 0.18, fy + out * 0.88, bz + 0.5), dmat("rail"))
            d.box((wx * 0.7, 0.04, 0.05), (cx, fy + out * 0.88, bz + 0.95), dmat("rail"))
            if rng.random() < 0.6:
                for k in range(3):
                    px = cx - wx * 0.25 + k * 0.5
                    d.cyl(0.12, 0.2, loc=(px, fy + out * 0.6, bz + 0.16), mat=dmat("pot"))
                    d.ico(0.2, (px, fy + out * 0.6, bz + 0.4), dmat("plant"), scale=(1, 1, 1.2))
    tx, ty = cx + rng.uniform(-wx * 0.25, wx * 0.25), fy + side * rng.uniform(2.0, depth - 1.5)
    d.cyl(0.55, 1.1, loc=(tx, ty, H + 0.55), mat=dmat("tank"), seg=20)
    d.box((0.8, 0.8, 0.25), (tx, ty, H + 0.12), dmat("concrete"))
    det = d.to_object(f"BldgDetail_{x0:.0f}_{side}", collection="Buildings")
    if sign:
        board = Part()
        board.box((wx - 0.5, 0.1, 0.78), (0, 0, 0), mat_obj("Paint"), bevel=0.02)
        sb = board.to_object(f"Sign_{x0:.0f}_{side}", collection="Buildings", loc=(cx, fy + out * 0.12, H0 - 0.15),
                             color=sign_color)
        rot = (PI / 2, 0, 0) if side > 0 else (PI / 2, 0, PI)
        t = text(sign, small or min(0.5, (wx - 0.9) / max(4, len(sign)) * 1.55), "impact",
                 loc=(cx, fy + out * 0.175, H0 - 0.15), rot=rot, color=text_color, collection="Buildings", extrude=0.01)
        if extra:
            text(extra, 0.2, "bold", loc=(cx, fy + out * 0.175, H0 - 0.45), rot=rot, color=text_color,
                 collection="Buildings", extrude=0.006)
    return wall_ob, det


def build_poles_and_wires(seed=5):
    rng = np.random.default_rng(seed)
    conc = mat_flat("PoleConcrete", (0.48, 0.47, 0.45), 0.9)
    wire_m = mat_flat("Wire", (0.02, 0.02, 0.02), 0.6)
    p = Part()
    tops = {1: [], -1: []}
    for side, xs in ((1, np.arange(-7.0, 82.0, 14.5)), (-1, np.arange(0.0, 82.0, 14.0))):
        for x in xs:
            y = side * 5.95
            p.box((0.2, 0.2, 9.0), (x, y, 4.5), conc)
            p.box((0.12, 1.5, 0.12), (x, y, 8.4), conc)
            for oy in (-0.6, -0.2, 0.2, 0.6):
                p.cyl(0.035, 0.12, loc=(x, y + oy, 8.52), mat=wire_m)
                tops[side].append((x, y + oy, 8.55))
            if rng.random() < 0.3:
                p.box((0.6, 0.5, 0.9), (x, y + side * 0.4, 6.5), dmat("shutter"))
    pole = p.to_object("Poles", collection="Street")
    wires = []
    for side, pts in tops.items():
        pts = sorted(pts)
        by_off = {}
        for q in pts:
            by_off.setdefault(round(q[1], 2), []).append(q)
        for off, qs in by_off.items():
            for a, b in zip(qs[:-1], qs[1:]):
                seg = []
                for t in np.linspace(0, 1, 16):
                    seg.append((a[0] + (b[0] - a[0]) * t, a[1], a[2] - 0.55 * 4 * t * (1 - t) - 0.05 * rng.random()))
                wires.append(seg)
    # cable-TV / internet bundles crossing the road
    for x in (7.0, 21.5, 37.0, 50.5, 66.0):
        for k in range(rng.integers(2, 5)):
            a = (x + rng.uniform(-0.3, 0.3), 5.95, 7.6 - k * 0.15)
            b = (x + rng.uniform(-2, 2), -5.95, 7.3 - k * 0.2)
            wires.append([(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t - 1.2 * 4 * t * (1 - t))
                          for t in np.linspace(0, 1, 20)])
    cu = bpy.data.curves.new("Wires", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.008
    cu.bevel_resolution = 0
    for seg in wires:
        sp = cu.splines.new("POLY")
        sp.points.add(len(seg) - 1)
        for pt, q in zip(sp.points, seg):
            pt.co = (*q, 1)
    cu.materials.append(wire_m)
    ob = bpy.data.objects.new("Wires", cu)
    coll("Street").objects.link(ob)
    return pole, ob


def build_tree(name, x, y, seed, scale=1.0):
    rng = np.random.default_rng(seed)
    bark = mat_flat("Bark", (0.16, 0.11, 0.08), 0.9)
    p = Part()
    p.cyl(0.16 * scale, 3.2 * scale, loc=(x, y, 1.6 * scale), r2=0.1 * scale, mat=bark, rot=(rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), 0))
    leaf = mat_obj("Leaves", 0.8, spec=0.3)
    for _ in range(9):
        p.ico(rng.uniform(0.9, 1.5) * scale, (x + rng.uniform(-1.1, 1.1) * scale, y + rng.uniform(-1.1, 1.1) * scale,
                                                (3.6 + rng.uniform(0, 1.6)) * scale), leaf, sub=2,
              scale=(1, 1, rng.uniform(0.7, 0.95)))
    return p.to_object(name, collection="Street", color=(0.07 + rng.uniform(0, 0.04), 0.22 + rng.uniform(0, 0.08), 0.05))


def build_garbage(cx, cy, seed=7):
    rng = np.random.default_rng(seed)
    bags = [mat_flat("BagBlack", (0.015, 0.015, 0.017), 0.35), mat_flat("BagWhite", (0.7, 0.7, 0.68), 0.5),
            mat_flat("BagBlue", (0.05, 0.15, 0.5), 0.4), mat_flat("BagGreen", (0.12, 0.35, 0.1), 0.6)]
    card = mat_flat("Cardboard", (0.45, 0.32, 0.18), 0.85)
    p = Part()
    for _ in range(26):
        x, y = cx + rng.normal(0, 0.55), cy + rng.normal(0, 0.3)
        z = float(W.terrain_height(x, y))
        r = rng.uniform(0.12, 0.26)
        p.sphere(r, (x, y, z + r * 0.5), bags[rng.integers(4)], scale=(1, rng.uniform(0.7, 1), rng.uniform(0.6, 0.85)),
                 rot=(0, 0, rng.uniform(0, 3)), seg=10, rings=6)
    for _ in range(6):
        x, y = cx + rng.normal(0, 0.6), cy + rng.normal(0, 0.35)
        z = float(W.terrain_height(x, y))
        s = rng.uniform(0.2, 0.4)
        p.box((s, s * 0.8, s * 0.6), (x, y, z + s * 0.28), card, rot=(rng.uniform(-0.3, 0.3), 0, rng.uniform(0, 3)))
    return p.to_object("GarbageHeap", collection="Street")


def build_tea_stall(x0, x1):
    m = M()
    p = Part()
    y = W.BUILD_Y - 0.05
    cx = (x0 + x1) / 2
    p.box((x1 - x0 - 0.4, 0.7, 1.0), (cx, y - 0.5, 0.5), dmat("wood"))
    for xx in (x0 + 0.3, x1 - 0.3):
        p.box((0.06, 0.06, 2.6), (xx, y - 1.6, 1.3), dmat("rail"))
    p.box((x1 - x0, 1.9, 0.04), (cx, y - 0.95, 2.55), dmat("tarp"), rot=(-0.12, 0, 0))
    p.cyl(0.11, 0.22, loc=(cx - 0.5, y - 0.45, 1.12), mat=m["steel"])
    p.cyl(0.03, 0.1, loc=(cx - 0.33, y - 0.45, 1.17), rot=(0, 1.2, 0), mat=m["steel"])
    for k in range(5):
        p.cyl(0.03, 0.08, loc=(cx + 0.1 + k * 0.1, y - 0.55, 1.04), mat=dmat("glass"))
    for k, xx in enumerate((cx - 0.9, cx + 0.6)):
        p.box((0.45, 0.45, 0.05), (xx, y - 1.75, 0.45), dmat("chair"))
        p.box((0.45, 0.05, 0.45), (xx, y - 1.53, 0.7), dmat("chair"))
        for ox in (-0.2, 0.2):
            for oy in (-0.2, 0.2):
                p.box((0.03, 0.03, 0.45), (xx + ox, y - 1.75 + oy, 0.22), dmat("chair"))
    p.box((1.6, 0.35, 0.06), (cx + 1.4, y - 0.9, 0.45), dmat("wood"))
    ob = p.to_object("TeaStall", collection="Buildings")
    text("SRI GANESH TEA STALL", 0.28, "impact", loc=(cx, y - 1.98, 2.25), rot=(PI / 2 - 0.12, 0, 0),
         color=(1.0, 0.85, 0.1), collection="Buildings", extrude=0.006)
    text("चाय", 0.5, "indic", loc=(cx + 1.6, y - 0.86, 1.25), rot=(PI / 2, 0, 0), color=(0.9, 0.12, 0.05),
         collection="Buildings", extrude=0.01)
    return ob


def build_apartment_gate():
    gx0, gx1 = 63.6, 65.4
    walls = Part()
    for a, b in ((61.6, gx0), (gx1, 80.0)):
        walls.box((b - a, 0.22, 1.55), ((a + b) / 2, W.BUILD_Y + 0.1, 0.78), mat_wall())
    walls.box((0.2, 3.0, 1.55), (61.6, W.BUILD_Y + 1.5, 0.78), mat_wall())
    for x in (gx0 - 0.25, gx1 + 0.25):
        walls.box((0.5, 0.5, 2.1), (x, W.BUILD_Y + 0.1, 1.05), mat_wall())
    w = walls.to_object("CompoundWall", collection="Buildings", color=(0.86, 0.80, 0.66))
    d = Part()
    m = M()
    for x in (gx0 - 0.25, gx1 + 0.25):
        d.sphere(0.16, (x, W.BUILD_Y + 0.1, 2.32), dmat("gW"))
    for s, hx in ((1, gx0), (-1, gx1)):
        ang = s * 1.25
        for k in range(9):
            t = 0.05 + k * 0.1
            d.box((0.025, 0.025, 1.4), (hx + s * t * math.cos(ang), W.BUILD_Y + 0.1 + t * math.sin(abs(ang)), 0.8), dmat("rail"))
        d.box((0.9, 0.04, 0.05), (hx + s * 0.45 * math.cos(ang), W.BUILD_Y + 0.1 + 0.45 * math.sin(abs(ang)), 1.48),
              dmat("rail"), rot=(0, 0, s * ang))
    d.box((18.4, 3.0, 0.05), (70.8, W.BUILD_Y + 1.6, 0.025), dmat("concrete"))
    gd = d.to_object("GateDetail", collection="Buildings")
    text("SAI KRUPA APARTMENTS", 0.2, "impact", loc=(gx0 - 1.6, W.BUILD_Y - 0.02, 1.2), rot=(PI / 2, 0, 0),
         color=(0.85, 0.65, 0.15), collection="Buildings", extrude=0.004)
    text("No. 14  ·  4th Cross", 0.12, "bold", loc=(gx0 - 1.6, W.BUILD_Y - 0.02, 0.95), rot=(PI / 2, 0, 0),
         color=(0.15, 0.12, 0.1), collection="Buildings", extrude=0.003)
    # the block behind the courtyard
    blk = building(62.4, 78.6, 1, 4, (0.90, 0.85, 0.72), kind="house", depth=7.0, seed=31)
    for ob in blk:
        ob.location.y += 3.0
    door = Part()
    door.box((1.4, 0.08, 2.3), (64.5, W.BUILD_Y + 2.98, 1.15), dmat("glass"))
    door.box((1.6, 0.1, 0.12), (64.5, W.BUILD_Y + 2.97, 2.36), dmat("frame"))
    door.to_object("ApartmentDoor", collection="Buildings")
    return w, gd


def build_banner(x):
    m = M()
    p = Part()
    p.box((0.04, 7.0, 1.1), (x, 0, 5.4), mat_obj("Paint"))
    b = p.to_object("Banner", collection="Street", color=(0.85, 0.12, 0.35))
    for side, rz in ((1, PI / 2), (-1, -PI / 2)):
        text("HAPPY DEEPAVALI", 0.62, "impact", loc=(x + side * 0.025, 0, 5.45), rot=(PI / 2, 0, rz), color=(1.0, 0.85, 0.15),
             collection="Street", extrude=0.004)
    curve_line("BannerRope1", [(x, 5.95, 7.4), (x, 3.5, 5.95)], 0.01)
    curve_line("BannerRope2", [(x, -5.95, 7.3), (x, -3.5, 5.95)], 0.01)
    return b


def build_india_street():
    m = M()
    build_terrain()
    build_water()
    build_road_marks()
    build_debris()
    L, R = 1, -1
    specs = [
        (-14.0, -6.4, L, 2, (0.58, 0.72, 0.85), None, None, "house"),
        (-6.0, 3.2, L, 2, (0.92, 0.86, 0.7), "BIRYANI HOUSE", (0.65, 0.05, 0.04), "shop"),
        (3.6, 11.0, L, 3, (0.95, 0.82, 0.35), "SHARMA GENERAL STORES", (0.05, 0.42, 0.15), "shop"),
        (11.4, 19.5, L, 2, (0.9, 0.62, 0.62), None, None, "house"),
        (19.9, 26.8, L, 2, (0.6, 0.82, 0.55), "MOBILE REPAIR & RECHARGE", (0.05, 0.25, 0.65), "shop"),
        (27.2, 32.2, L, 3, (0.92, 0.92, 0.88), None, None, "house"),
        (32.4, 38.6, L, 1, (0.95, 0.7, 0.5), None, None, "house"),
        (39.0, 45.6, L, 3, (0.75, 0.66, 0.88), "SRI SAI MEDICALS", (0.04, 0.45, 0.2), "shop"),
        (46.0, 51.5, L, 2, (0.95, 0.65, 0.35), None, None, "house"),
        (53.5, 61.2, L, 2, (0.95, 0.9, 0.55), "XEROX · TAILORING", (0.7, 0.07, 0.05), "shop"),
        (80.4, 90.0, L, 3, (0.7, 0.85, 0.82), None, None, "house"),
        (-14.0, -4.0, R, 3, (0.55, 0.78, 0.5), "HOTEL ANNAPOORNA", (0.08, 0.35, 0.1), "shop"),
        (-3.6, 6.0, R, 2, (0.55, 0.75, 0.92), None, None, "house"),
        (6.4, 14.0, R, 2, (0.62, 0.66, 0.72), "AUTO SPARES", (0.9, 0.72, 0.05), "shop"),
        (14.4, 22.0, R, 3, (0.95, 0.75, 0.6), None, None, "house"),
        (22.4, 29.0, R, 2, (0.93, 0.88, 0.72), "IYENGAR BAKERY", (0.85, 0.4, 0.05), "shop"),
        (29.4, 36.0, R, 4, (0.92, 0.93, 0.95), None, None, "house"),
        (36.4, 44.0, R, 3, (0.85, 0.55, 0.72), "SRI LAKSHMI SILKS", (0.45, 0.04, 0.12), "shop"),
        (44.4, 52.0, R, 2, (0.95, 0.88, 0.45), None, None, "house"),
        (52.4, 60.0, R, 1, (0.85, 0.85, 0.8), "FRESH VEGETABLES", (0.1, 0.5, 0.1), "shop"),
        (60.4, 68.0, R, 3, (0.65, 0.88, 0.78), None, None, "house"),
        (68.4, 76.0, R, 2, (0.92, 0.82, 0.68), "GANESH HARDWARE", (0.05, 0.2, 0.6), "shop"),
        (76.4, 90.0, R, 3, (0.85, 0.7, 0.55), None, None, "house"),
    ]
    tc = {(0.95, 0.82, 0.35): (1, 1, 1)}
    for i, (x0, x1, side, fl, col, sign, scol, kind) in enumerate(specs):
        extra = {"BIRYANI HOUSE": "Since 1987  ·  Home Delivery", "SRI SAI MEDICALS": "24 x 7"}.get(sign)
        building(x0, x1, side, fl, col, sign, scol or (0.5, 0.1, 0.1), (1.0, 0.95, 0.8) if scol != (0.9, 0.72, 0.05) else (0.1, 0.1, 0.12),
                 kind, seed=i + 1, extra=extra)
    for x0, x1 in ((51.5, 53.5),):           # side walls of the alley the thief escapes into
        pass
    building(-24.0, -16.0, L, 3, (0.8, 0.8, 0.75), kind="house", seed=60)
    blk = Part()
    blk.box((6.0, 30.0, 11.0), (93.0, 0.0, 5.5), mat_wall())
    blk.box((6.0, 30.0, 9.0), (-21.0, 0.0, 4.5), mat_wall())
    blk.to_object("EndBlocks", collection="Buildings", color=(0.82, 0.76, 0.62))
    sky = Part()
    rng = np.random.default_rng(9)
    for k in range(40):
        side = 1 if k % 2 else -1
        x = rng.uniform(-30, 100)
        h = rng.uniform(8, 18)
        sky.box((rng.uniform(5, 12), 8, h), (x, side * rng.uniform(17, 24), h / 2), mat_wall())
    sky.to_object("Skyline", collection="Buildings", color=(0.75, 0.72, 0.66))
    build_tea_stall(32.6, 35.8)
    build_garbage(37.1, 4.5)
    build_apartment_gate()
    build_poles_and_wires()
    build_banner(43.0)
    for i, (x, y, s) in enumerate(((5.5, -5.3, 1.0), (27.3, -5.4, 1.15), (49.0, -5.3, 0.95), (-9.0, 5.4, 1.0), (71.0, -5.4, 1.05))):
        build_tree(f"Tree{i}", x, y, 20 + i, s)
    for i, (x, y, hdg, col) in enumerate(((12.8, 4.75, 0.2, (0.6, 0.05, 0.04)), (18.5, 5.0, -0.15, (0.05, 0.1, 0.35)),
                                          (55.9, 4.35, 0.05, (0.08, 0.08, 0.09)), (2.5, -5.0, PI + 0.1, (0.85, 0.85, 0.85)),
                                          (16.0, -4.9, PI - 0.2, (0.7, 0.55, 0.05)), (40.0, -5.1, PI, (0.1, 0.3, 0.15)),
                                          (63.0, -4.8, PI + 0.15, (0.5, 0.05, 0.05)), (30.5, 5.3, 0.1, (0.9, 0.9, 0.92)))):
        z = float(W.terrain_height(x, y))
        build_scooter(f"Scooter{i}", col, (x, y, z), hdg)
    build_car("ParkedCar", (0.88, 0.88, 0.9), (33.0, -4.75, float(W.terrain_height(33.0, -4.75))), PI)


# ----------------------------------------------------------------------------------------------- US suburb
def build_us_street():
    m = M()
    grass = mat_flat("Lawn", (0.11, 0.30, 0.06), 0.85)
    asph = mat_flat("SmoothAsphalt", (0.055, 0.055, 0.06), 0.75)
    conc = mat_flat("SidewalkConcrete", (0.55, 0.54, 0.51), 0.8)
    joint = mat_flat("Joint", (0.25, 0.25, 0.24), 0.9)
    yel = mat_flat("YellowLine", (0.85, 0.62, 0.05), 0.6)
    wht = mat_flat("WhiteLine", (0.85, 0.85, 0.82), 0.6)
    p = Part()
    p.box((140, 80, 0.2), (20, 0, -0.1), grass)
    p.box((140, 8.0, 0.02), (20, 0, 0.01), asph)
    p.box((140, 0.12, 0.004), (20, 0.1, 0.022), yel)
    p.box((140, 0.12, 0.004), (20, -0.1, 0.022), yel)
    for s in (1, -1):
        p.box((140, 0.12, 0.004), (20, s * 3.75, 0.022), wht)
        p.box((140, 0.15, 0.15), (20, s * 4.08, 0.075), conc)
        p.box((140, 1.8, 0.1), (20, s * 6.1, 0.05), conc)
        for x in np.arange(-50, 90, 1.5):
            p.box((0.02, 1.8, 0.004), (x, s * 6.1, 0.101), joint)
    for x in (-8.0, 14.0, 34.0):
        p.box((3.2, 6.0, 0.1), (x, 7.4, 0.052), conc)
    us = p.to_object("USGround", collection="Street")
    rng = np.random.default_rng(4)
    cols = [(0.92, 0.9, 0.85), (0.72, 0.8, 0.9), (0.85, 0.78, 0.62), (0.9, 0.92, 0.95)]
    for k, x in enumerate(np.arange(-30, 70, 16)):
        for s in (1, -1):
            h = Part()
            cx, cy = x + rng.uniform(-1, 1), s * 17.0
            h.box((10, 8, 3.2), (cx, cy, 1.6), mat_wall())
            hb = h.to_object(f"House{k}{s}", collection="Buildings", color=cols[(k + (s > 0)) % 4])
            r = Part()
            roof = mat_flat("Shingle", (0.18, 0.16, 0.15), 0.8)
            r.poly([(cx - 5.4, cy - s * 4.4, 3.2), (cx + 5.4, cy - s * 4.4, 3.2), (cx + 5.4, cy, 5.6), (cx - 5.4, cy, 5.6)], roof)
            r.poly([(cx - 5.4, cy + s * 4.4, 3.2), (cx - 5.4, cy, 5.6), (cx + 5.4, cy, 5.6), (cx + 5.4, cy + s * 4.4, 3.2)], roof)
            r.poly([(cx - 5.0, cy - 4.0, 3.2), (cx - 5.0, cy + 4.0, 3.2), (cx - 5.0, cy, 5.4)], mat_wall())
            r.poly([(cx + 5.0, cy - 4.0, 3.2), (cx + 5.0, cy, 5.4), (cx + 5.0, cy + 4.0, 3.2)], mat_wall())
            for wx in (-3, 0, 3):
                r.box((1.2, 0.05, 1.3), (cx + wx, cy - s * 4.02, 1.8), dmat("glass"))
                r.box((1.35, 0.08, 1.45), (cx + wx, cy - s * 4.0, 1.8), dmat("gW"))
            r.box((1.0, 0.06, 2.1), (cx + 4.0, cy - s * 4.03, 1.05), dmat("wood"))
            r.to_object(f"HouseRoof{k}{s}", collection="Buildings")
    for i, x in enumerate(np.arange(-26, 70, 9.0)):
        build_tree(f"USTree{i}", x, 4.65 if i % 2 else -4.65, 50 + i, 0.85)
    hyd = Part()
    hyd.cyl(0.12, 0.6, loc=(9.0, 7.35, 0.4), mat=m["red"])
    hyd.sphere(0.12, (9.0, 7.35, 0.72), m["red"])
    hyd.to_object("Hydrant", collection="Street")
    mb = Part()
    mb.box((0.08, 0.08, 1.1), (18.0, 7.2, 0.55), dmat("wood"))
    mb.box((0.5, 0.25, 0.28), (18.0, 7.2, 1.2), m["dark"], bevel=0.08)
    mb.to_object("Mailbox", collection="Street")
    return us
