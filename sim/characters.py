"""Procedural characters for the Bharat-Bot scene. Built from primitives so the scene has no asset dependencies.

Every builder returns a dict of the objects the animator needs. Local frames: +X forward, +Y left, +Z up.
"""
import math

import bpy
from mathutils import Vector

from bpy_utils import Part, coll, empty, mat_flat, mat_fx, mat_led, mat_obj, no_shadow, text

PI = math.pi


def M():
    return dict(
        paint=mat_obj("Paint", 0.55), fur=mat_obj("Fur", 0.9, spec=0.3),
        rubber=mat_flat("Rubber", (0.022, 0.022, 0.025), 0.85),
        black=mat_flat("BlackGloss", (0.01, 0.01, 0.012), 0.15, coat=0.6),
        dark=mat_flat("DarkMetal", (0.045, 0.047, 0.05), 0.4, metal=0.7),
        steel=mat_flat("Steel", (0.55, 0.56, 0.58), 0.3, metal=1.0),
        led=mat_led(), fx=mat_fx(),
        glass=mat_flat("Glass", (0.02, 0.03, 0.04), 0.05, coat=1.0),
        cavity=mat_flat("Cavity", (0.012, 0.012, 0.014), 0.9),
        white=mat_flat("ShellWhite", (0.84, 0.85, 0.86), 0.3, coat=0.5),
        saffron=mat_flat("Saffron", (0.95, 0.40, 0.03), 0.45),
        green=mat_flat("IndiaGreen", (0.02, 0.38, 0.12), 0.45),
        orange=mat_flat("FlagOrange", (1.0, 0.28, 0.02), 0.6, emit=0.4),
        kraft=mat_flat("Kraft", (0.55, 0.40, 0.24), 0.8),
        red=mat_flat("RedPaint", (0.6, 0.04, 0.03), 0.5),
        lidar=mat_flat("LidarRing", (0.1, 0.85, 1.0), 0.3, emit=6.0),
        screen=mat_flat("PhoneScreen", (0.55, 0.75, 1.0), 0.2, emit=3.0),
        horn=mat_flat("Horn", (0.22, 0.18, 0.13), 0.6),
    )


def annulus(name, r_in, r_out, color, parent=None, collection="FX", seg=48, loc=(0, 0, 0), rot=(0, 0, 0)):
    """Flat glowing ring (FX material) in the local XY plane."""
    p = Part()
    pts_o = [(r_out * math.cos(2 * PI * k / seg), r_out * math.sin(2 * PI * k / seg), 0) for k in range(seg)]
    pts_i = [(r_in * math.cos(2 * PI * k / seg), r_in * math.sin(2 * PI * k / seg), 0) for k in range(seg)]
    import bmesh
    t = bmesh.new()
    vo = [t.verts.new(q) for q in pts_o]
    vi = [t.verts.new(q) for q in pts_i]
    for k in range(seg):
        j = (k + 1) % seg
        t.faces.new((vi[k], vo[k], vo[j], vi[j]))
    p._add(t, M()["fx"])
    ob = p.to_object(name, parent=parent, collection=collection, loc=loc, rot=rot, color=color)
    return no_shadow(ob)


def wheel_mesh(name, r, w, hub_mat, treads=16):
    m = M()
    p = Part()
    rx = (PI / 2, 0, 0)
    p.cyl(r, w, mat=m["rubber"], rot=rx, seg=28, bevel=r * 0.16)
    for k in range(treads):
        a = 2 * PI * k / treads
        p.box((0.032 * r / 0.16, w * 0.92, 0.022 * r / 0.16), loc=(r * math.cos(a), 0, r * math.sin(a)),
              rot=(0, PI / 2 - a, 0), mat=m["rubber"])
    p.cyl(r * 0.5, w * 1.06, mat=hub_mat, rot=rx, seg=20)
    for side in (1, -1):
        for k in range(3):
            a = 2 * PI * k / 3
            p.box((r * 0.42, 0.012, r * 0.09), loc=(r * 0.22 * math.cos(a), side * w * 0.54, r * 0.22 * math.sin(a)),
                  rot=(0, -a, 0), mat=m["dark"])
    me_ob = p.to_object(name)
    me = me_ob.data
    bpy.data.objects.remove(me_ob)
    return me


# ----------------------------------------------------------------------------------------------- robots
def build_robot(kind, name, collection="Robot"):
    """kind 'bharat' (India-adapted, rocker-bogie) or 'baseline' (US-style sidewalk robot)."""
    m = M()
    R = dict(kind=kind)
    root = empty(name, collection=collection, size=0.5)
    R["root"] = root
    if kind == "bharat":
        r, w, ht, axles = 0.16, 0.085, 0.35, (0.38, 0.0, -0.38)
        L, W, z0, z1 = 0.82, 0.52, 0.04, 0.40
    else:
        r, w, ht, axles = 0.09, 0.06, 0.30, (0.32, 0.0, -0.32)
        L, W, z0, z1 = 0.74, 0.54, -0.02, 0.40
    R.update(r=r, ht=ht, axles=axles, L=L, W=W, top=z1)
    b = Part()
    zc = (z0 + z1) / 2
    if kind == "bharat":
        b.box((L, W, z1 - z0), (0, 0, zc), m["white"], bevel=0.05)
        b.box((L + 0.02, W + 0.02, 0.07), (0, 0, z0 + 0.035), m["saffron"], bevel=0.025)
        b.box((L + 0.016, W + 0.016, 0.018), (0, 0, z0 + 0.082), m["green"], bevel=0.006)
        b.box((0.03, 0.40, 0.17), (L / 2 - 0.005, 0, 0.275), m["black"], bevel=0.012)
        b.cyl(0.045, 0.07, loc=(0.22, 0, z1 + 0.035), mat=m["dark"])
        for s in (1, -1):
            b.cyl(0.042, 0.03, loc=(0.06, s * (W / 2 + 0.015), 0.10), rot=(PI / 2, 0, 0), mat=m["dark"])
        cams = ((L / 2, 0.19, 0), (L / 2, -0.19, 0), (0, W / 2, PI / 2), (0, -W / 2, -PI / 2), (-L / 2, 0, PI))
    else:
        b.box((L, W, z1 - z0), (0, 0, zc), m["white"], bevel=0.1)
        b.box((L + 0.01, W + 0.01, 0.10), (0, 0, z0 + 0.05), m["dark"], bevel=0.04)
        b.box((0.02, 0.26, 0.06), (L / 2 - 0.002, 0, 0.30), m["black"], bevel=0.01)
        cams = ((L / 2 + 0.005, 0.08, 0), (L / 2 + 0.005, -0.08, 0))
    for (x, y, zr) in cams:
        b.cyl(0.017, 0.022, loc=(x, y, 0.335 if kind == "bharat" else 0.30), rot=(0, PI / 2, zr), mat=m["black"])
    b.box((L - 0.12, W - 0.08, 0.004), (0, 0, z1 + 0.002), m["cavity"])
    b.cyl(0.009, 0.82, loc=(-L / 2 + 0.08, 0.20, z1 + 0.41), mat=m["dark"])
    R["body"] = b.to_object(name + "_body", parent=root, collection=collection)
    # lid on a rear hinge
    hinge = empty(name + "_lidhinge", parent=root, loc=(-L / 2 + 0.04, 0, z1 + 0.003), collection=collection, size=0.05)
    lp = Part()
    lw = L - 0.08
    lp.box((lw, W - 0.04, 0.045), (lw / 2, 0, 0.0225), m["white"], bevel=0.018)
    if kind == "bharat":
        lp.box((lw * 0.9, 0.035, 0.004), (lw / 2, 0.12, 0.046), m["saffron"])
        lp.box((lw * 0.9, 0.035, 0.004), (lw / 2, -0.12, 0.046), m["green"])
    R["lid"] = lp.to_object(name + "_lid", parent=hinge, collection=collection)
    R["hinge"] = hinge
    if kind == "bharat":
        t = text("BHARAT-BOT", 0.075, "bold", loc=(lw / 2, 0, 0.047), rot=(0, 0, -PI / 2), color=(0.05, 0.08, 0.12),
                 parent=hinge, collection=collection, extrude=0.0015)
        t.data.space_character = 1.1
    # lights
    led = m["led"]
    if kind == "bharat":
        e = Part()
        for s in (1, -1):
            e.box((0.012, 0.085, 0.055), (0, s * 0.08, 0), led, bevel=0.02)
        R["eyes"] = e.to_object(name + "_eyes", parent=root, collection=collection, loc=(L / 2 + 0.013, 0, 0.285),
                                color=(0.1, 0.85, 1.0, 0.25))
        st = Part()
        for s in (1, -1):
            st.box((0.6, 0.012, 0.014), (0, s * (W / 2 + 0.002), z1 - 0.015), led, bevel=0.005)
        R["status"] = st.to_object(name + "_status", parent=root, collection=collection, color=(0.1, 1.0, 0.4, 0.2))
        lid_ob = Part()
        lid_ob.cyl(0.062, 0.055, mat=m["dark"], seg=24)
        lid_ob.cyl(0.0625, 0.01, loc=(0, 0, 0.012), mat=m["lidar"], seg=24)
        lid_ob.box((0.02, 0.05, 0.03), (0.06, 0, 0.0), m["black"])
        R["lidar"] = lid_ob.to_object(name + "_lidar", parent=root, collection=collection, loc=(0.22, 0, z1 + 0.10))
    hl = Part()
    hl.box((0.012, 0.34 if kind == "bharat" else 0.28, 0.022), (0, 0, 0), led, bevel=0.008)
    R["headlight"] = hl.to_object(name + "_headlight", parent=root, collection=collection,
                                  loc=(L / 2 + 0.008, 0, 0.17 if kind == "bharat" else 0.12), color=(1.0, 0.95, 0.85, 0.12))
    tl = Part()
    tl.box((0.012, 0.30, 0.022), (0, 0, 0), led, bevel=0.008)
    R["taillight"] = tl.to_object(name + "_taillight", parent=root, collection=collection,
                                  loc=(-L / 2 - 0.008, 0, 0.17 if kind == "bharat" else 0.12), color=(1.0, 0.05, 0.02, 0.15))
    # flag
    fl = Part()
    fl.poly([(0, 0, 0), (0, 0, -0.17), (-0.27, 0, -0.07)], m["orange"])
    R["flag"] = fl.to_object(name + "_flag", parent=root, collection=collection, loc=(-L / 2 + 0.08, 0.20, z1 + 0.82))
    # wheels
    wm = wheel_mesh(name + "_wheel", r, w, m["saffron"] if kind == "bharat" else m["steel"], 16 if kind == "bharat" else 10)
    R["wheels"] = []
    for side in (1, -1):
        for ax in axles:
            ob = bpy.data.objects.new(f"{name}_wheel_{'L' if side > 0 else 'R'}{ax:+.2f}", wm)
            coll(collection).objects.link(ob)
            ob.parent = root
            ob.location = (ax, side * ht, 0)
            R["wheels"].append(ob)
    # rocker-bogie arms (bharat only): unit-length bars, animated per frame
    R["arms"] = []
    if kind == "bharat":
        bar = Part()
        bar.box((1.0, 0.03, 0.036), (0, 0, 0), m["dark"], bevel=0.008)
        bar_ob = bar.to_object(name + "_armmesh")
        bar_me = bar_ob.data
        bpy.data.objects.remove(bar_ob)
        for side in (1, -1):
            for nm in ("rf", "rb", "bf", "bb"):
                ob = bpy.data.objects.new(f"{name}_arm_{nm}{'L' if side > 0 else 'R'}", bar_me)
                coll(collection).objects.link(ob)
                ob.parent = root
                R["arms"].append((side, nm, ob))
        # sensor FX: range ring on the ground + rotating scan wedge
        R["range"] = annulus(name + "_range", 6.45, 6.5, (0.1, 0.9, 1.0, 0.0), parent=root, loc=(0, 0, -r + 0.03))
        wp = Part()
        import bmesh
        tb = bmesh.new()
        c = tb.verts.new((0, 0, 0))
        n = 10
        ring = [tb.verts.new((6.4 * math.cos(math.radians(-14 + 28 * k / n)), 6.4 * math.sin(math.radians(-14 + 28 * k / n)), 0))
                for k in range(n + 1)]
        for k in range(n):
            tb.faces.new((c, ring[k], ring[k + 1]))
        wp._add(tb, m["fx"])
        R["sweep"] = no_shadow(wp.to_object(name + "_sweep", parent=R["lidar"], collection="FX", loc=(0, 0, -0.43),
                                            color=(0.1, 0.9, 1.0, 0.0)))
    # behaviour FX rings
    R["deter"] = [annulus(f"{name}_deter{i}", 0.93, 1.0, (0.55, 0.95, 1.0, 0.0), parent=root, loc=(0, 0, -r + 0.05))
                  for i in range(4)]
    R["siren"] = [annulus(f"{name}_siren{i}", 0.9, 1.0, (1.0, 0.05, 0.03, 0.0), parent=root, loc=(0, 0, z1 + 0.15))
                  for i in range(4)]
    lt = bpy.data.lights.new(name + "_alarmlight", "POINT")
    lt.energy = 0.0
    lt.color = (1.0, 0.1, 0.05)
    lt.shadow_soft_size = 0.1
    R["alarmlight"] = bpy.data.objects.new(name + "_alarmlight", lt)
    coll(collection).objects.link(R["alarmlight"])
    R["alarmlight"].parent = root
    R["alarmlight"].location = (0, 0, z1 + 0.35)
    fl2 = bpy.data.lights.new(name + "_flash", "POINT")
    fl2.energy = 0.0
    fl2.shadow_soft_size = 0.05
    R["flash"] = bpy.data.objects.new(name + "_flash", fl2)
    coll(collection).objects.link(R["flash"])
    R["flash"].parent = root
    R["flash"].location = (L / 2 + 0.3, 0, 0.4)
    return R


def build_bag(name="FoodParcel", collection="Robot"):
    m = M()
    p = Part()
    p.box((0.24, 0.19, 0.20), (0, 0, 0.0), m["kraft"], bevel=0.01)
    p.box((0.245, 0.195, 0.04), (0, 0, 0.03), m["red"])
    p.box((0.02, 0.12, 0.06), (0, 0, 0.12), m["kraft"])
    return p.to_object(name, collection=collection)


# ----------------------------------------------------------------------------------------------- animals
def build_dog(name, fur, collection="Animals"):
    m = M()
    f = m["fur"]
    D = dict()
    root = empty(name, collection=collection, size=0.3)
    pelvis = empty(name + "_pelvis", parent=root, collection=collection, size=0.1)
    b = Part()
    b.sphere(0.30, loc=(0, 0, 0.45), scale=(1.0, 0.36, 0.42), mat=f)
    b.sphere(0.12, loc=(0.17, 0, 0.47), scale=(1.0, 0.88, 1.05), mat=f)
    b.sphere(0.11, loc=(-0.20, 0, 0.47), scale=(1.0, 0.95, 0.95), mat=f)
    b.cyl(0.05, 0.18, loc=(0.29, 0, 0.55), rot=(0, 0.8, 0), r2=0.045, mat=f)
    D["body"] = b.to_object(name + "_body", parent=pelvis, collection=collection, color=fur)
    head = empty(name + "_head", parent=pelvis, loc=(0.35, 0, 0.61), collection=collection, size=0.05)
    h = Part()
    h.sphere(0.085, loc=(0.02, 0, 0.03), scale=(1.15, 0.95, 0.95), mat=f)
    h.cyl(0.03, 0.13, loc=(0.13, 0, 0.0), rot=(0, PI / 2, 0), r2=0.042, mat=f)
    h.sphere(0.02, loc=(0.195, 0, 0.012), mat=m["black"])
    for s in (1, -1):
        h.cyl(0.032, 0.09, loc=(0.0, s * 0.05, 0.115), rot=(s * 0.35, -0.12, 0), r2=0.004, mat=f)
        h.sphere(0.012, loc=(0.085, s * 0.043, 0.055), mat=m["black"])
    D["headmesh"] = h.to_object(name + "_headmesh", parent=head, collection=collection, color=fur)
    D["legs"] = []
    for nm, (x, y) in (("FL", (0.19, 0.075)), ("FR", (0.19, -0.075)), ("BL", (-0.21, 0.075)), ("BR", (-0.21, -0.075))):
        lp = Part()
        lp.cyl(0.022, 0.38, loc=(0, 0, -0.19), r2=0.032, mat=f)
        lp.sphere(0.03, loc=(0.015, 0, -0.38), scale=(1.3, 1, 0.7), mat=f)
        D["legs"].append(lp.to_object(name + "_leg" + nm, parent=pelvis, collection=collection, loc=(x, y, 0.42), color=fur))
    tp = Part()
    tp.cyl(0.012, 0.27, loc=(0, 0, 0.135), r2=0.024, mat=f)
    D["tail"] = tp.to_object(name + "_tail", parent=pelvis, collection=collection, loc=(-0.29, 0, 0.52), color=fur)
    D["bark"] = annulus(name + "_bark", 0.85, 1.0, (1.0, 0.95, 0.8, 0.0), parent=head, loc=(0.26, 0, 0.0),
                        rot=(0, PI / 2, 0), seg=32)
    D.update(root=root, pelvis=pelvis, head=head)
    return D


GLB_DOGS = [  # (file, scale, walk m/s at that scale, gallop m/s at that scale, resting clip) from research/blender.md
    ("quaternius_shiba_inu.glb", 0.181, 0.42, 1.40, "Eating"),
    ("quaternius_husky.glb", 0.185, 0.43, 1.50, "Idle_2_HeadLow"),
    ("quaternius_shiba_inu.glb", 0.168, 0.39, 1.30, "Idle_2"),
]


def glb_dog_available():
    import os
    from bpy_utils import PROJECT
    return all(os.path.exists(os.path.join(PROJECT, "assets", "polypizza", "animals", g[0])) for g in GLB_DOGS)


def import_rig(fname, name, scale, collection="Animals"):
    """Import a rigged Quaternius GLB under our own root empty (importer junk removed, glTF's default
    metallic=1 turned off, feet put on z=0). Returns root, holder, armature, actions by clip name, meshes."""
    import os
    from bpy_utils import PROJECT
    root = empty(name, collection=collection, size=0.3)
    before_o, before_a, before_m = set(bpy.data.objects), set(bpy.data.actions), set(bpy.data.materials)
    bpy.ops.import_scene.gltf(filepath=os.path.join(PROJECT, "assets", "polypizza", "animals", fname))
    junk = [o.name for o in bpy.data.objects if o not in before_o and
            ((o.type == "EMPTY" and o.name.endswith("_end")) or o.name.startswith("Icosphere"))]
    for nm in junk:
        bpy.data.objects.remove(bpy.data.objects[nm], do_unlink=True)
    new = [o for o in bpy.data.objects if o not in before_o]
    holder = empty(name + "_model", parent=root, collection=collection, size=0.1)
    holder.rotation_euler = (0, 0, PI / 2)
    holder.scale = (scale, scale, scale)
    for o in new:
        if o.parent is None:
            o.parent = holder
    for mt in bpy.data.materials:
        if mt not in before_m and mt.node_tree:
            for nd in mt.node_tree.nodes:
                if nd.type == "BSDF_PRINCIPLED":
                    nd.inputs["Metallic"].default_value = 0.0
                    nd.inputs["Roughness"].default_value = 0.8
                    nd.inputs["Specular IOR Level"].default_value = 0.35
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    zmin = min(((oe.matrix_world @ Vector(c)).z for o in new if o.type == "MESH"
                for oe in [o.evaluated_get(dg)] for c in oe.bound_box), default=0.0)
    holder.location.z = -zmin
    arm = next(o for o in new if o.type == "ARMATURE")
    acts = {}
    for a in bpy.data.actions:
        if a not in before_a and "|" in a.name:
            acts[a.name.split("|", 1)[1].split(".")[0]] = a
    return root, holder, arm, acts, [o for o in new if o.type == "MESH"]


def loop_clip(arm, act, n_frames):
    """Play one clip on repeat for the whole shot (NLA strip)."""
    ad = arm.animation_data or arm.animation_data_create()
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    ad.action = None
    s = ad.nla_tracks.new().strips.new(act.name, 1, act)
    if hasattr(s, "action_slot") and len(act.slots):
        s.action_slot = act.slots[0]
    s.repeat = max(1.0, n_frames / max(1.0, act.frame_range[1] - act.frame_range[0]))
    return s


def build_glb_cow(name="Cow", n_frames=3000):
    root, holder, arm, acts, meshes = import_rig("quaternius_cow.glb", name, 0.294)
    loop_clip(arm, acts.get("Eating", next(iter(acts.values()))), n_frames)
    return dict(root=root, holder=holder, arm=arm)


def build_glb_dog(i, name, collection="Animals"):
    """Animated Quaternius dog (CC0) wrapped in our own root empty; the sim drives the root, NLA drives the gait."""
    fname, scale, walk_v, run_v, rest = GLB_DOGS[i]
    root, holder, arm, acts, meshes = import_rig(fname, name, scale, collection)
    bark = annulus(name + "_bark", 0.85, 1.0, (1.0, 0.95, 0.8, 0.0), parent=root, loc=(0.42, 0, 0.42),
                   rot=(0, PI / 2, 0), seg=32)
    return dict(root=root, holder=holder, arm=arm, acts=acts, walk_v=walk_v, run_v=run_v, rest=rest, bark=bark,
                meshes=meshes)


def build_cow(name="Cow", collection="Animals"):
    m = M()
    f = m["fur"]
    col = (0.80, 0.78, 0.74)
    C = {}
    root = empty(name, collection=collection, size=0.5)
    b = Part()
    b.sphere(0.80, loc=(0, 0, 1.0), scale=(1.0, 0.5, 0.5), mat=f)                 # barrel
    b.sphere(0.36, loc=(-0.52, 0, 1.03), scale=(1.0, 1.05, 1.0), mat=f)          # rump
    b.sphere(0.30, loc=(0.42, 0, 1.36), scale=(1.0, 0.85, 0.95), mat=f)          # zebu hump
    b.sphere(0.30, loc=(0.68, 0, 1.08), scale=(1.0, 0.72, 1.0), mat=f)           # shoulder / neck
    b.sphere(0.26, loc=(0.74, 0, 0.74), scale=(0.65, 0.3, 1.15), mat=f)          # dewlap
    for x, y in ((0.50, 0.2), (0.50, -0.2), (-0.56, 0.2), (-0.56, -0.2)):
        b.cyl(0.07, 0.70, loc=(x, y, 0.42), r2=0.095, mat=f)
        b.cyl(0.072, 0.07, loc=(x, y, 0.035), mat=m["black"])
    C["body"] = b.to_object(name + "_body", parent=root, collection=collection, color=col)
    head = empty(name + "_head", parent=root, loc=(0.9, 0, 1.24), collection=collection, size=0.1)
    h = Part()
    h.sphere(0.25, loc=(0.15, 0, -0.12), rot=(0, 0.95, 0), scale=(1.0, 0.46, 0.5), mat=f)
    h.sphere(0.11, loc=(0.29, 0, -0.33), scale=(0.95, 1.15, 0.8), mat=m["black"])
    for s in (1, -1):
        h.cyl(0.035, 0.17, loc=(0.0, s * 0.09, 0.11), rot=(-s * 0.5, -0.25, 0), r2=0.01, mat=m["horn"])
        h.sphere(0.15, loc=(0.0, s * 0.19, -0.06), rot=(s * 1.0, 0, 0), scale=(0.45, 1.0, 0.22), mat=f)
        h.sphere(0.02, loc=(0.17, s * 0.1, -0.02), mat=m["black"])
    C["headmesh"] = h.to_object(name + "_headmesh", parent=head, collection=collection, color=col)
    tail = Part()
    tail.cyl(0.02, 0.72, loc=(0, 0, -0.36), mat=f)
    tail.sphere(0.055, loc=(0, 0, -0.74), scale=(1, 1, 1.8), mat=m["black"])
    C["tail"] = tail.to_object(name + "_tail", parent=root, collection=collection, loc=(-0.86, 0, 1.2), color=col)
    C.update(root=root, head=head)
    return C


# ----------------------------------------------------------------------------------------------- people
def build_person(name, shirt, pants, skin=(0.40, 0.25, 0.16), hair=(0.025, 0.02, 0.018), style="man", collection="People"):
    m = M()
    ms = mat_flat(name + "_shirt", shirt, 0.85)
    mp = mat_flat(name + "_pants", pants, 0.85)
    mk = mat_flat("Skin%.2f" % skin[0], skin, 0.55)
    mh = mat_flat(name + "_hair", hair, 0.7)
    P = {}
    root = empty(name, collection=collection, size=0.3)
    hip = empty(name + "_hip", parent=root, loc=(0, 0, 0.92), collection=collection, size=0.1)
    t = Part()
    if style == "saree":
        t.box((0.22, 0.34, 0.50), (0, 0, 0.30), ms, bevel=0.07)
        t.box((0.05, 0.36, 0.55), (0.02, 0.02, 0.30), mh, rot=(0.5, 0, 0))
    else:
        t.box((0.22, 0.36, 0.53), (0, 0, 0.30), ms, bevel=0.07)
    t.cyl(0.05, 0.08, loc=(0, 0, 0.60), mat=mk)
    if style == "hoodie":
        t.sphere(0.13, loc=(-0.06, 0, 0.55), scale=(1.0, 1.25, 0.5), mat=ms)
    P["torso"] = t.to_object(name + "_torso", parent=hip, collection=collection)
    head = empty(name + "_head", parent=hip, loc=(0, 0, 0.64), collection=collection, size=0.05)
    h = Part()
    h.sphere(0.105, loc=(0.0, 0, 0.11), scale=(1.0, 0.9, 1.1), mat=mk)
    for s in (1, -1):
        h.sphere(0.012, loc=(0.093, s * 0.035, 0.125), mat=m["black"])
    if style == "hoodie":
        h.sphere(0.125, loc=(-0.045, 0, 0.13), scale=(1.05, 1.02, 1.1), mat=ms)
        h.box((0.13, 0.2, 0.02), (0.09, 0, 0.215), ms)
    elif style == "saree":
        h.sphere(0.112, loc=(-0.015, 0, 0.14), scale=(1.0, 0.96, 0.9), mat=mh)
        h.sphere(0.06, loc=(-0.11, 0, 0.09), mat=mh)
    else:
        h.sphere(0.11, loc=(-0.012, 0, 0.145), scale=(1.0, 0.96, 0.82), mat=mh)
    P["headmesh"] = h.to_object(name + "_headmesh", parent=head, collection=collection)
    P["arms"] = []
    for s in (1, -1):
        a = Part()
        a.cyl(0.052, 0.30, loc=(0, 0, -0.15), mat=ms)
        a.cyl(0.04, 0.28, loc=(0, 0, -0.43), mat=mk, r2=0.046)
        a.sphere(0.045, loc=(0, 0, -0.60), scale=(1, 0.8, 1.1), mat=mk)
        P["arms"].append(a.to_object(f"{name}_arm{'L' if s > 0 else 'R'}", parent=hip, collection=collection,
                                     loc=(0, s * 0.215, 0.52)))
    P["legs"] = []
    for s in (1, -1):
        lp = Part()
        if style == "saree":
            lp.cyl(0.07, 0.86, loc=(0, 0, -0.43), mat=ms, r2=0.075)
        else:
            lp.cyl(0.068, 0.86, loc=(0, 0, -0.43), mat=mp, r2=0.075)
        lp.box((0.25, 0.10, 0.07), (0.05, 0, -0.885), m["black"], bevel=0.02)
        P["legs"].append(lp.to_object(f"{name}_leg{'L' if s > 0 else 'R'}", parent=hip, collection=collection,
                                      loc=(0, s * 0.10, 0.0)))
    if style == "saree":
        sk = Part()
        sk.cyl(0.30, 0.9, loc=(0, 0, -0.45), r2=0.17, mat=ms, seg=20)
        P["skirt"] = sk.to_object(name + "_skirt", parent=hip, collection=collection)
    ph = Part()
    ph.box((0.012, 0.075, 0.15), (0, 0, 0), m["black"], bevel=0.008)
    ph.box((0.002, 0.065, 0.13), (-0.007, 0, 0), m["screen"])
    P["phone"] = ph.to_object(name + "_phone", parent=hip, collection=collection, loc=(0.27, -0.06, 0.40), rot=(0, -0.5, 0))
    P.update(root=root, hip=hip, head=head)
    return P


# ----------------------------------------------------------------------------------------------- vehicles & props
def build_auto(name="AutoRickshaw", collection="Vehicles"):
    m = M()
    g = mat_flat("AutoGreen", (0.05, 0.36, 0.10), 0.35, coat=0.5)
    y = mat_flat("AutoYellow", (0.95, 0.72, 0.02), 0.35, coat=0.5)
    canvas = mat_flat("Canvas", (0.03, 0.03, 0.03), 0.9)
    A = {}
    root = empty(name, collection=collection, size=0.6)
    b = Part()
    b.box((2.35, 1.25, 0.50), (-0.15, 0, 0.55), g, bevel=0.08)
    b.box((0.55, 0.85, 0.95), (1.05, 0, 0.78), g, bevel=0.12)
    b.box((1.55, 1.27, 0.30), (-0.45, 0, 0.95), y, bevel=0.05)
    b.box((2.0, 1.36, 0.12), (-0.25, 0, 1.78), canvas, bevel=0.05)
    b.box((0.25, 1.32, 0.10), (0.78, 0, 1.70), canvas, rot=(0, 0.45, 0), bevel=0.03)
    for (x, yy) in ((0.62, 0.62), (0.62, -0.62), (-1.2, 0.64), (-1.2, -0.64)):
        b.box((0.05, 0.05, 0.8), (x, yy, 1.35), m["dark"])
    b.box((0.04, 0.9, 0.55), (0.78, 0, 1.38), m["glass"], rot=(0, -0.25, 0))
    b.box((0.02, 0.18, 0.12), (1.33, 0, 0.90), m["steel"], bevel=0.02)
    b.cyl(0.05, 0.6, loc=(0.82, 0, 1.1), rot=(PI / 2, 0, 0), mat=m["dark"])
    b.box((0.45, 0.45, 0.06), (0.35, 0, 0.88), canvas)
    b.box((0.35, 1.1, 0.07), (-0.55, 0, 0.92), canvas)
    A["body"] = b.to_object(name + "_body", parent=root, collection=collection)
    hl = Part()
    hl.cyl(0.07, 0.03, rot=(0, PI / 2, 0), mat=m["led"])
    A["headlight"] = hl.to_object(name + "_headlight", parent=root, collection=collection, loc=(1.33, 0, 1.05),
                                  color=(1.0, 0.95, 0.8, 0.15))
    drv = build_person(name + "_driver", (0.75, 0.68, 0.45), (0.2, 0.18, 0.15), collection=collection)
    drv["root"].parent = root
    drv["root"].location = (0.30, 0, 0.0)
    drv["hip"].location = (0, 0, 0.95)
    for i, l in enumerate(drv["legs"]):
        l.rotation_euler = (0, -1.4, 0)
    for a in drv["arms"]:
        a.rotation_euler = (0, -1.1, 0)
    wm = wheel_mesh(name + "_wheel", 0.21, 0.12, m["steel"], 12)
    A["wheels"] = []
    for (x, yy) in ((1.05, 0.0), (-0.8, 0.56), (-0.8, -0.56)):
        ob = bpy.data.objects.new(name + "_wheel", wm)
        coll(collection).objects.link(ob)
        ob.parent = root
        ob.location = (x, yy, 0.21)
        A["wheels"].append(ob)
    A["root"] = root
    return A


def build_scooter(name, color, loc, heading, collection="Props"):
    m = M()
    p = Part()
    p.box((0.9, 0.30, 0.28), (-0.05, 0, 0.42), m["paint"], bevel=0.08)
    p.box((0.62, 0.26, 0.10), (-0.18, 0, 0.62), m["black"], bevel=0.04)
    p.box((0.14, 0.34, 0.55), (0.48, 0, 0.62), m["paint"], rot=(0, -0.25, 0), bevel=0.05)
    p.cyl(0.015, 0.62, loc=(0.56, 0, 0.98), rot=(PI / 2, 0, 0), mat=m["dark"])
    p.cyl(0.045, 0.03, loc=(0.6, 0, 0.88), rot=(0, PI / 2, 0), mat=m["steel"])
    for x in (0.55, -0.48):
        p.cyl(0.2, 0.09, loc=(x, 0, 0.2), rot=(PI / 2, 0, 0), mat=m["rubber"], seg=20)
        p.cyl(0.1, 0.1, loc=(x, 0, 0.2), rot=(PI / 2, 0, 0), mat=m["steel"], seg=12)
    ob = p.to_object(name, collection=collection, loc=loc, rot=(0, 0, heading), color=color)
    return ob


def build_car(name, color, loc, heading, collection="Props"):
    m = M()
    p = Part()
    p.box((3.9, 1.68, 0.62), (0, 0, 0.55), m["paint"], bevel=0.16)
    p.box((2.1, 1.52, 0.55), (-0.25, 0, 1.12), m["glass"], bevel=0.14)
    p.box((2.0, 1.54, 0.08), (-0.25, 0, 1.40), m["paint"], bevel=0.04)
    for x in (1.25, -1.25):
        for s in (1, -1):
            p.cyl(0.31, 0.2, loc=(x, s * 0.76, 0.31), rot=(PI / 2, 0, 0), mat=m["rubber"], seg=20)
            p.cyl(0.18, 0.21, loc=(x, s * 0.76, 0.31), rot=(PI / 2, 0, 0), mat=m["steel"], seg=14)
    return p.to_object(name, collection=collection, loc=loc, rot=(0, 0, heading), color=color)
