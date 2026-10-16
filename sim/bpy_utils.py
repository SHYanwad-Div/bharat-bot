"""bpy helpers: object-colour driven materials, a multi-material mesh builder, fast grids, F-curve arrays and text.

Most props share a handful of materials whose base colour comes from the object's colour (Object Info), so
EEVEE compiles few shaders and every object can still have its own colour.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

FONTS = {}
MATS = {}
COLLS = {}
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXDIR = os.path.join(PROJECT, "assets", "polyhaven", "textures")


def find_tex(tid, kind="diff"):
    """Path of a downloaded Poly Haven map (1k or 2k jpg), or None."""
    for res in ("1k", "2k"):
        p = os.path.join(TEXDIR, tid, f"{tid}_{kind}_{res}.jpg")
        if os.path.exists(p):
            return p
    return None


def tex(nt, tid, kind, vector, x=0, y=0, noncolor=False, box=False):
    img = bpy.data.images.load(find_tex(tid, kind), check_existing=True)
    if noncolor:
        img.colorspace_settings.name = "Non-Color"
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = img
    n.location = (x, y)
    if box:
        n.projection = "BOX"
        n.projection_blend = 0.25
    nt.links.new(vector, n.inputs["Vector"])
    return n


# ----------------------------------------------------------------------------------------------- scene plumbing
def coll(name):
    if name not in COLLS:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        COLLS[name] = c
    return COLLS[name]


def empty(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), collection="Rigs", size=0.2):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_size = size
    coll(collection).objects.link(ob)
    ob.parent = parent
    ob.location, ob.rotation_euler = loc, rot
    return ob


def font(key):
    paths = {"impact": r"C:\Windows\Fonts\impact.ttf", "bold": r"C:\Windows\Fonts\bahnschrift.ttf",
             "indic": r"C:\Windows\Fonts\Nirmala.ttc", "segoe": r"C:\Windows\Fonts\segoeuib.ttf"}
    if key not in FONTS:
        try:
            FONTS[key] = bpy.data.fonts.load(paths[key], check_existing=True)
        except Exception:
            FONTS[key] = None
    return FONTS[key]


# ----------------------------------------------------------------------------------------------- node helpers
def sock(sockets, name, kind=None):
    for s in sockets:
        if s.name == name and (kind is None or s.type == kind) and s.enabled:
            return s
    for s in sockets:
        if s.name == name and (kind is None or s.type == kind):
            return s
    raise KeyError(name)


def nn(nt, kind, x=0, y=0, **props):
    n = nt.nodes.new(kind)
    n.location = (x, y)
    for k, v in props.items():
        if hasattr(n, k):
            setattr(n, k, v)
        else:
            n.inputs[k].default_value = v
    return n


def math_node(nt, op, a, b=None, x=0, y=0, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    n.location = (x, y)
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def mix(nt, fac, a, b, blend="MIX", x=0, y=0):
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    n.blend_type = blend
    n.location = (x, y)
    for s, v in ((sock(n.inputs, "Factor", "VALUE"), fac), (sock(n.inputs, "A", "RGBA"), a), (sock(n.inputs, "B", "RGBA"), b)):
        if isinstance(v, (int, float)):
            s.default_value = v
        elif isinstance(v, tuple):
            s.default_value = v if len(v) == 4 else (*v, 1.0)
        else:
            nt.links.new(v, s)
    return sock(n.outputs, "Result", "RGBA")


def new_material(name):
    m = bpy.data.materials.new(name)
    return m, m.node_tree, m.node_tree.nodes.get("Principled BSDF")


# ----------------------------------------------------------------------------------------------- materials
def mat_obj(name="Paint", rough=0.6, metal=0.0, coat=0.0, spec=0.5):
    """Principled material whose base colour is the object's colour."""
    if name in MATS:
        return MATS[name]
    m, nt, p = new_material(name)
    oi = nn(nt, "ShaderNodeObjectInfo", -400, 200)
    nt.links.new(oi.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Coat Weight"].default_value = coat
    p.inputs["Specular IOR Level"].default_value = spec
    MATS[name] = m
    return m


def mat_flat(name, color, rough=0.6, metal=0.0, emit=0.0, coat=0.0):
    """Fixed-colour material (for parts that must differ from the object's colour)."""
    if name in MATS:
        return MATS[name]
    m, nt, p = new_material(name)
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Coat Weight"].default_value = coat
    if emit:
        p.inputs["Emission Color"].default_value = (*color, 1)
        p.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = (*color, 1)
    MATS[name] = m
    return m


def mat_led():
    """Emissive: colour = object colour, strength = object alpha x 30. Dark glossy when off."""
    if "LED" in MATS:
        return MATS["LED"]
    m, nt, p = new_material("LED")
    oi = nn(nt, "ShaderNodeObjectInfo", -500, 0)
    p.inputs["Base Color"].default_value = (0.02, 0.02, 0.025, 1)
    p.inputs["Roughness"].default_value = 0.25
    nt.links.new(oi.outputs["Color"], p.inputs["Emission Color"])
    nt.links.new(math_node(nt, "MULTIPLY", oi.outputs["Alpha"], 30.0, -250, -150), p.inputs["Emission Strength"])
    MATS["LED"] = m
    return m


def mat_fx():
    """Unlit translucent glow for HUD-style effects: colour = object colour, opacity = object alpha."""
    if "FX" in MATS:
        return MATS["FX"]
    m = bpy.data.materials.new("FX")
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    oi = nn(nt, "ShaderNodeObjectInfo", -600, 0)
    em = nn(nt, "ShaderNodeEmission", -300, -100)
    em.inputs["Strength"].default_value = 3.5
    nt.links.new(oi.outputs["Color"], em.inputs["Color"])
    tr = nn(nt, "ShaderNodeBsdfTransparent", -300, 100)
    mx = nn(nt, "ShaderNodeMixShader", -100, 0)
    nt.links.new(oi.outputs["Alpha"], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    m.surface_render_method = "BLENDED"
    m.use_backface_culling = False
    MATS["FX"] = m
    return m


def mat_wall():
    """Painted plaster: object colour, darkened by grime toward the ground and noise stains."""
    if "Wall" in MATS:
        return MATS["Wall"]
    m, nt, p = new_material("Wall")
    tc = nn(nt, "ShaderNodeTexCoord", -1200, 0)
    oi = nn(nt, "ShaderNodeObjectInfo", -1200, 300)
    noise = nn(nt, "ShaderNodeTexNoise", -950, -100, Scale=1.6, Detail=6.0, Roughness=0.6)
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    sep = nn(nt, "ShaderNodeSeparateXYZ", -950, 150)
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    low = nn(nt, "ShaderNodeMapRange", -750, 150)
    nt.links.new(sep.outputs["Z"], low.inputs["Value"])
    low.inputs["From Min"].default_value, low.inputs["From Max"].default_value = 0.0, 1.4
    low.inputs["To Min"].default_value, low.inputs["To Max"].default_value = 0.42, 0.0
    stain = math_node(nt, "MULTIPLY", math_node(nt, "SUBTRACT", noise.outputs["Fac"], 0.42, -750, -100), 0.9, -600, -100)
    grime = math_node(nt, "ADD", low.outputs["Result"], stain, -450, 0, clamp=True)
    base = oi.outputs["Color"]
    if find_tex("painted_plaster_wall"):          # real plaster detail, tinted by the object colour
        mp = nn(nt, "ShaderNodeMapping", -950, 450)
        mp.inputs["Scale"].default_value = (0.5, 0.5, 0.5)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        pl = tex(nt, "painted_plaster_wall", "diff", mp.outputs[0], -750, 450, box=True)
        base = mix(nt, 1.0, base, pl.outputs["Color"], "MULTIPLY", -500, 400)
        base = mix(nt, 1.0, base, (1.25, 1.25, 1.25), "MULTIPLY", -350, 400)
    col = mix(nt, grime, base, (0.18, 0.15, 0.12), "MIX", -250, 200)
    nt.links.new(col, p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.88
    bump = nn(nt, "ShaderNodeBump", -250, -200, Strength=0.12)
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    MATS["Wall"] = m
    return m


def mat_water():
    if "Water" in MATS:
        return MATS["Water"]
    m, nt, p = new_material("Water")
    p.inputs["Base Color"].default_value = (0.075, 0.06, 0.042, 1)
    p.inputs["Roughness"].default_value = 0.03
    p.inputs["IOR"].default_value = 1.33
    p.inputs["Specular IOR Level"].default_value = 0.6
    tc = nn(nt, "ShaderNodeTexCoord", -900, 0)
    noise = nn(nt, "ShaderNodeTexNoise", -650, 0, Scale=9.0, Detail=3.0)
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    bump = nn(nt, "ShaderNodeBump", -350, -150, Strength=0.06)
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    MATS["Water"] = m
    return m


# ----------------------------------------------------------------------------------------------- mesh builder
class Part:
    """Accumulates primitives (each with its own material) into one mesh object.

    Each primitive is built in its own temporary bmesh (bevel + transform there), then appended, so primitives
    never interfere. All faces are smooth-shaded; edges sharper than 40 degrees are marked sharp at the end."""

    _tmp = None

    def __init__(self):
        self.bm = bmesh.new()
        self.mats = []
        if Part._tmp is None or Part._tmp.name not in bpy.data.meshes:
            Part._tmp = bpy.data.meshes.new("_part_tmp")

    @staticmethod
    def _mat(loc, rot, scale=(1, 1, 1)):
        return (Matrix.Translation(Vector(loc)) @ Euler(rot).to_matrix().to_4x4()
                @ Matrix.Diagonal(Vector((*scale, 1.0))))

    def _add(self, tbm, mat, matrix=None, bevel=0.0, seg=3):
        if bevel > 0:
            bmesh.ops.bevel(tbm, geom=list(tbm.verts) + list(tbm.edges), offset=bevel, segments=seg,
                            affect="EDGES", profile=0.5, clamp_overlap=True)
        if matrix is not None:
            bmesh.ops.transform(tbm, matrix=matrix, verts=list(tbm.verts))
        if mat not in self.mats:
            self.mats.append(mat)
        mi = self.mats.index(mat)
        for f in tbm.faces:
            f.material_index = mi
            f.smooth = True
        tbm.to_mesh(Part._tmp)
        tbm.free()
        self.bm.from_mesh(Part._tmp)
        return self

    def box(self, size, loc=(0, 0, 0), mat=None, rot=(0, 0, 0), bevel=0.0, seg=3):
        t = bmesh.new()
        bmesh.ops.create_cube(t, size=1.0)
        bmesh.ops.scale(t, vec=Vector(size), verts=list(t.verts))
        return self._add(t, mat, self._mat(loc, rot), min(bevel, 0.49 * min(size)), seg)

    def cyl(self, r, depth, loc=(0, 0, 0), mat=None, rot=(0, 0, 0), seg=16, r2=None, caps=True, bevel=0.0):
        t = bmesh.new()
        bmesh.ops.create_cone(t, cap_ends=caps, cap_tris=False, segments=seg, radius1=r,
                              radius2=r if r2 is None else r2, depth=depth)
        return self._add(t, mat, self._mat(loc, rot), bevel, 2)

    def sphere(self, r, loc=(0, 0, 0), mat=None, rot=(0, 0, 0), scale=(1, 1, 1), seg=16, rings=10):
        t = bmesh.new()
        bmesh.ops.create_uvsphere(t, u_segments=seg, v_segments=rings, radius=r)
        return self._add(t, mat, self._mat(loc, rot, scale))

    def ico(self, r, loc=(0, 0, 0), mat=None, scale=(1, 1, 1), sub=1, rot=(0, 0, 0)):
        t = bmesh.new()
        bmesh.ops.create_icosphere(t, subdivisions=sub, radius=r)
        return self._add(t, mat, self._mat(loc, rot, scale))

    def poly(self, pts, mat=None, thickness=0.0):
        """Polygon from a list of 3D points (optionally extruded down by `thickness`)."""
        t = bmesh.new()
        vs = [t.verts.new(p) for p in pts]
        f = t.faces.new(vs)
        if thickness > 0:
            r = bmesh.ops.extrude_face_region(t, geom=[f])
            bmesh.ops.translate(t, vec=Vector((0, 0, -thickness)), verts=[v for v in r["geom"] if isinstance(v, bmesh.types.BMVert)])
            bmesh.ops.recalc_face_normals(t, faces=list(t.faces))
        return self._add(t, mat)

    def strip(self, pts, width, mat=None, closed=False):
        """Flat ribbon of given width along a 3D polyline (lies in the ground plane)."""
        t = bmesh.new()
        pts = [Vector(p) for p in pts]
        n = len(pts)
        left, right = [], []
        for i, p in enumerate(pts):
            a = pts[(i - 1) % n] if (closed or i > 0) else p
            b = pts[(i + 1) % n] if (closed or i < n - 1) else p
            d = (b - a)
            d.z = 0
            d = d.normalized() if d.length > 1e-9 else Vector((1, 0, 0))
            nrm = Vector((-d.y, d.x, 0)) * (width / 2)
            left.append(t.verts.new(p + nrm))
            right.append(t.verts.new(p - nrm))
        for i in (range(n) if closed else range(n - 1)):
            j = (i + 1) % n
            t.faces.new((right[i], right[j], left[j], left[i]))
        return self._add(t, mat)

    def to_object(self, name, parent=None, collection="Scene", loc=(0, 0, 0), rot=(0, 0, 0), color=None):
        me = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        me.set_sharp_from_angle(angle=math.radians(40))
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        coll(collection).objects.link(ob)
        ob.parent = parent
        ob.location, ob.rotation_euler = loc, rot
        if color is not None:
            ob.color = (*color, 1.0) if len(color) == 3 else color
        return ob


def grid_object(name, xs, ys, Z, collection="Scene", attrs=None, mat=None):
    """Fast height-field mesh from separable x/y samples. attrs: {name: (N,4) float colours per vertex}."""
    nx, ny = len(xs), len(ys)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    V = np.c_[X.ravel(), Y.ravel(), Z.ravel()].astype(np.float32)
    idx = np.arange(nx * ny).reshape(nx, ny)
    Q = np.stack([idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()], 1).astype(np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.ravel())
    me.loops.add(Q.size)
    me.loops.foreach_set("vertex_index", Q.ravel())
    me.polygons.add(len(Q))
    me.polygons.foreach_set("loop_start", np.arange(0, Q.size, 4, dtype=np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set("use_smooth", np.ones(len(Q), bool))
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", (V[Q.ravel()][:, :2] * 0.25).ravel())
    for an, data in (attrs or {}).items():
        ca = me.color_attributes.new(an, "FLOAT_COLOR", "POINT")
        ca.data.foreach_set("color", np.asarray(data, np.float32).ravel())
    if mat:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    coll(collection).objects.link(ob)
    return ob


def text(body, size=0.4, fnt="impact", loc=(0, 0, 0), rot=(0, 0, 0), color=(1, 1, 1), parent=None, extrude=0.004,
         mat=None, collection="Props", align="CENTER", name=None):
    cu = bpy.data.curves.new(name or ("T_" + body[:12]), "FONT")
    cu.body = body
    f = font(fnt)
    if f:
        cu.font = f
    cu.size = size
    cu.extrude = extrude
    cu.align_x = align
    cu.align_y = "CENTER"
    ob = bpy.data.objects.new(name or ("T_" + body[:12]), cu)
    coll(collection).objects.link(ob)
    ob.parent = parent
    ob.location, ob.rotation_euler = loc, rot
    ob.color = tuple(color) if len(color) == 4 else (*color, 1.0)
    cu.materials.append(mat or mat_obj())
    return ob


def curve_line(name, pts, radius=0.008, mat=None, collection="Props", color=(0.03, 0.03, 0.03)):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 1
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (*q, 1.0)
    cu.materials.append(mat or mat_obj())
    ob = bpy.data.objects.new(name, cu)
    coll(collection).objects.link(ob)
    ob.color = (*color, 1.0)
    return ob


# ----------------------------------------------------------------------------------------------- animation
INTERP = {"CONSTANT": 0, "LINEAR": 1, "BEZIER": 2}


def key(idb, path, values, index=0, start=1, interp="LINEAR", decimate=True):
    """Write one F-curve of per-frame values (frame `start`, start+1, ...). Repeated values are thinned out."""
    vals = np.asarray(values, float)
    frames = np.arange(start, start + len(vals), dtype=float)
    if decimate and len(vals) > 2:
        if interp == "CONSTANT":
            keep = np.r_[True, vals[1:] != vals[:-1]]
        else:
            same_prev = np.r_[False, np.isclose(vals[1:], vals[:-1], atol=1e-6)]
            same_next = np.r_[np.isclose(vals[:-1], vals[1:], atol=1e-6), False]
            keep = ~(same_prev & same_next)
        frames, vals = frames[keep], vals[keep]
    ad = idb.animation_data or idb.animation_data_create()
    if ad.action is None:
        ad.action = bpy.data.actions.new(idb.name + "_anim")
    fc = ad.action.fcurve_ensure_for_datablock(idb, path, index=index)
    kp = fc.keyframe_points
    kp.add(len(vals))
    co = np.empty(2 * len(vals), np.float32)
    co[0::2], co[1::2] = frames, vals
    kp.foreach_set("co", co)
    kp.foreach_set("interpolation", np.full(len(vals), INTERP[interp], np.int32))
    fc.update()
    return fc


def key_vec(idb, path, arr, start=1, interp="LINEAR"):
    arr = np.asarray(arr, float)
    for i in range(arr.shape[1]):
        key(idb, path, arr[:, i], index=i, start=start, interp=interp)


def look_euler(pos, target, prev=None):
    q = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y")
    return q.to_euler("XYZ", prev) if prev is not None else q.to_euler("XYZ")


def no_shadow(ob):
    ob.visible_shadow = False
    return ob
