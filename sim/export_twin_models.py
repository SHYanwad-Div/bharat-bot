r"""Export the browser twin's 3D models (docs/twin/models) from the film's own procedural builders.

  "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python sim/export_twin_models.py

street.glb   the film's Indian street (environment.build_india_street) without its road surface, which the browser
             rebuilds from world.py's terrain function (docs/twin/js/terrain.js); static meshes merged into one
robots.glb   Bharat-Bot, its body split into labelled parts for the explode view, plus the standard sidewalk robot
             and the food parcel (characters.build_robot / build_bag)
people.glb   the thief, the customer and two passers-by (characters.build_person)
auto.glb     the auto-rickshaw and its driver (characters.build_auto)
dog_shiba.glb, dog_husky.glb, cow.glb   the CC0 Quaternius animals, keeping only the clips the twin plays
sky.jpg, sky.hdr   the Poly Haven sky the film is lit by, at web size

glTF has no "object colour", which most of the film's materials read. Each object's colour is written into a colour
attribute ("Col", exported as COLOR_0) and those materials become plain "vc_<name>" ones that the browser multiplies
by it. Meshes are Draco-compressed; the effects (sensor sweep, alarm rings, bark rings) are drawn by the browser.
"""
import json
import math
import os
import struct
import sys
import time

import bmesh
import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import bpy_utils as U  # noqa: E402
import characters as C  # noqa: E402
import environment as E  # noqa: E402

PI = math.pi
OUT = os.path.join(ROOT, "docs", "twin", "models")
ANIMALS = os.path.join(ROOT, "assets", "polypizza", "animals")
SKY = os.path.join(ROOT, "assets", "polyhaven", "hdri", "kloofendal_43d_clear_puresky_2k.hdr")
DOG_CLIPS = ("Gallop", "Walk", "Attack", "Idle", "Eating", "Idle_2", "Idle_2_HeadLow")
COW_CLIPS = ("Eating", "Idle", "Idle_Headlow")
FX_SUFFIXES = ("_range", "_sweep", "_deter", "_siren", "_alarmlight", "_flash", "_bark")


# ----------------------------------------------------------------------------------------------- scene plumbing
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for d in (U.MATS, U.COLLS, U.FONTS, E.DETAIL, PLAIN):
        d.clear()
    U.Part._tmp = None


def tree(root):
    out = [root]
    for ch in root.children:
        out += tree(ch)
    return out


def remove(ob):
    for ch in list(ob.children):
        remove(ch)
    bpy.data.objects.remove(ob, do_unlink=True)


def realize(ob):
    """Replace a text or curve object by a mesh object with the same name, place, parent, children and colour."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    new = bpy.data.objects.new(ob.name + "~", me)
    for c in ob.users_collection:
        c.objects.link(new)
    new.parent = ob.parent
    new.matrix_parent_inverse = ob.matrix_parent_inverse.copy()
    new.matrix_basis = ob.matrix_basis.copy()
    new.color = ob.color
    for ch in list(ob.children):
        mw = ch.matrix_world.copy()
        ch.parent = new
        ch.matrix_world = mw
    name = ob.name
    bpy.data.objects.remove(ob, do_unlink=True)
    new.name = name
    return new


def realize_all(objs):
    return [realize(o) if o.type in ("FONT", "CURVE") else o for o in objs]


# ----------------------------------------------------------------------------------------------- object colours
PLAIN = {}


def reads_object_colour(mat):
    return bool(mat and mat.node_tree and any(n.type == "OBJECT_INFO" for n in mat.node_tree.nodes))


def plain(mat):
    """A plain copy of a material that reads the object colour: white base (the browser multiplies COLOR_0 in)."""
    if mat.name in PLAIN:
        return PLAIN[mat.name]
    src = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    m, nt, p = U.new_material("vc_" + mat.name)
    for k in ("Roughness", "Metallic", "Coat Weight", "Specular IOR Level"):
        if src is not None and not src.inputs[k].is_linked:
            p.inputs[k].default_value = src.inputs[k].default_value
    p.inputs["Base Color"].default_value = (1, 1, 1, 1)
    if mat.name == "LED":
        p.inputs["Base Color"].default_value = (0.02, 0.02, 0.025, 1)
    PLAIN[mat.name] = m
    return m


def bake_colours(objs):
    """Write each object's colour into the 'Col' colour attribute on the faces whose material reads it (white
    elsewhere) and swap those materials for plain copies."""
    for ob in objs:
        if ob.type != "MESH":
            continue
        me = ob.data
        mats = list(me.materials)
        reads = [reads_object_colour(m) for m in mats]
        if any(reads) and me.users > 1:
            ob.data = me = me.copy()
        col = tuple(ob.color[:3])
        for ca in list(me.color_attributes):
            me.color_attributes.remove(ca)
        ca = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
        me.color_attributes.active_color = ca
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
        n = len(me.loops)
        rgba = np.ones((n, 4), np.float32)
        if any(reads) and n:
            mi = np.zeros(len(me.polygons), np.int32)
            me.polygons.foreach_get("material_index", mi)
            ls = np.zeros(len(me.polygons), np.int32)
            lt = np.zeros(len(me.polygons), np.int32)
            me.polygons.foreach_get("loop_start", ls)
            me.polygons.foreach_get("loop_total", lt)
            hit = np.array([reads[i] if i < len(reads) else False for i in mi])
            loop_poly = np.repeat(np.arange(len(me.polygons)), lt)
            rgba[hit[loop_poly], :3] = col
        ca.data.foreach_set("color", rgba.ravel())
        for i, m in enumerate(mats):
            if reads[i]:
                me.materials[i] = plain(m)


# ----------------------------------------------------------------------------------------------- merging & splitting
def join(objs, name, collection):
    """Merge mesh objects into one new object at the origin (world-space geometry, materials per face kept)."""
    me = bpy.data.meshes.new(name)
    target = bpy.data.objects.new(name, me)
    U.coll(collection).objects.link(target)
    objs = [o for o in objs if o.type == "MESH"]
    for o in objs:
        if o.data.users > 1:
            o.data = o.data.copy()
    with bpy.context.temp_override(active_object=target, object=target, selected_objects=[target] + objs,
                                   selected_editable_objects=[target] + objs):
        bpy.ops.object.join()
    cas = target.data.color_attributes
    for ca in [c for c in cas if c.name != "Col"]:
        cas.remove(ca)
    if "Col" in cas:
        cas.active_color = cas["Col"]
        cas.render_color_index = cas.active_color_index
    return target


def chunk(ob, size, collection):
    """Cut a merged mesh into pieces along x (by face centre), so the browser can skip pieces that are off screen or
    outside the shadow box."""
    me = ob.data
    cen = np.empty(len(me.polygons) * 3)
    me.polygons.foreach_get("center", cen)
    keys = np.floor(cen.reshape(-1, 3)[:, 0] / size).astype(int)
    out = []
    for k in sorted(set(keys.tolist())):
        keep = np.nonzero(keys == k)[0]
        m2 = me.copy()
        bm = bmesh.new()
        bm.from_mesh(m2)
        bm.faces.ensure_lookup_table()
        drop = np.ones(len(bm.faces), bool)
        drop[keep] = False
        bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(drop)[0]], context="FACES")
        bm.to_mesh(m2)
        bm.free()
        cas = m2.color_attributes
        if "Col" in cas:
            cas.active_color = cas["Col"]
            cas.render_color_index = cas.active_color_index
        o2 = bpy.data.objects.new(f"{ob.name}_{len(out)}", m2)
        U.coll(collection).objects.link(o2)
        out.append(o2)
    bpy.data.objects.remove(ob, do_unlink=True)
    return out


def components(me):
    """Loose parts of a mesh: lists of face indices."""
    parent = list(range(len(me.vertices)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for e in me.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b:
            parent[a] = b
    comps = {}
    for p in me.polygons:
        comps.setdefault(find(p.vertices[0]), []).append(p.index)
    return list(comps.values())


def split(ob, classify, prefix):
    """Split a mesh object into one object per labelled group of loose parts: classify(centre, size, material)."""
    me = ob.data
    groups = {}
    for faces in components(me):
        vs = sorted({v for f in faces for v in me.polygons[f].vertices})
        co = np.array([me.vertices[v].co[:] for v in vs])
        centre, size = (co.min(0) + co.max(0)) / 2, co.max(0) - co.min(0)
        mat = me.materials[me.polygons[faces[0]].material_index].name
        groups.setdefault(classify(centre, size, mat), set()).update(faces)
    out = {}
    for key, keep in groups.items():
        m2 = me.copy()
        bm = bmesh.new()
        bm.from_mesh(m2)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context="FACES")
        bm.to_mesh(m2)
        bm.free()
        o2 = bpy.data.objects.new(f"{prefix}_part_{key}", m2)
        for c in ob.users_collection:
            c.objects.link(o2)
        o2.parent = ob.parent
        o2.matrix_basis = ob.matrix_basis.copy()
        o2.color = ob.color
        out[key] = o2
    bpy.data.objects.remove(ob, do_unlink=True)
    return out


def bharat_part(c, s, mat):
    """Which labelled part of Bharat-Bot a loose piece of its body belongs to (robot frame: +x forward, +z up)."""
    x, y, z = c
    if mat == "Cavity":
        return "cargo"
    if mat in ("Saffron", "IndiaGreen"):
        return "bumper"
    if mat == "ShellWhite":
        return "shell"
    if mat == "DarkMetal":
        return "flag" if z > 0.6 else ("rockerL" if y > 0 else "rockerR") if abs(y) > 0.2 else "lidar"
    if mat == "BlackGloss":
        if x > 0.35 and abs(y) < 0.25:
            return "depthcam"
        return "camB" if x < -0.3 else "camL" if y > 0 else "camR"
    return "shell"


# ----------------------------------------------------------------------------------------------- builders
def strip_fx(root):
    for ob in tree(root)[1:]:
        if ob.name in bpy.data.objects and (ob.type == "LIGHT" or any(s in ob.name for s in FX_SUFFIXES)):
            remove(ob)


def add_siren(R, name):
    """Siren + strobe on Bharat-Bot's back (the film shows the alarm only as light and rings)."""
    m = C.M()
    red = U.mat_flat("SirenRed", (0.85, 0.04, 0.03), 0.3)
    L = R["L"]
    p = U.Part()
    p.box((0.016, 0.11, 0.032), (0, 0.15, 0.30), red, bevel=0.008)
    p.cyl(0.032, 0.018, loc=(0, -0.15, 0.30), rot=(0, PI / 2, 0), mat=m["dark"], seg=20)
    p.cyl(0.022, 0.02, loc=(-0.004, -0.15, 0.30), rot=(0, PI / 2, 0), mat=m["black"], seg=20)
    return p.to_object(name + "_part_siren", parent=R["root"], collection=R["root"].users_collection[0].name,
                       loc=(-L / 2 - 0.008, 0, 0))


def build_robots():
    out = []
    B = C.build_robot("bharat", "BharatBot", collection="Robots")
    strip_fx(B["root"])
    split(B["body"], bharat_part, "BharatBot")
    add_siren(B, "BharatBot")
    out.append(B["root"])
    S = C.build_robot("baseline", "StdBot", collection="Robots")
    strip_fx(S["root"])
    out.append(S["root"])
    bag = C.build_bag("Parcel", collection="Robots")
    out.append(bag)
    for r in out:
        realize_all(tree(r))
    objs = [o for r in out for o in tree(r)]
    bake_colours(objs)
    return objs


def build_people():
    specs = [("Thief", (0.07, 0.07, 0.085), (0.04, 0.045, 0.06), (0.40, 0.25, 0.16), "hoodie"),
             ("Customer", (0.42, 0.62, 0.85), (0.72, 0.66, 0.52), (0.46, 0.30, 0.19), "man"),
             ("Walker0", (0.85, 0.85, 0.82), (0.2, 0.2, 0.25), (0.36, 0.23, 0.15), "man"),
             ("Walker1", (0.75, 0.1, 0.4), (0.75, 0.1, 0.4), (0.42, 0.23, 0.15), "saree")]
    objs = []
    for name, shirt, pants, skin, style in specs:
        P = C.build_person(name, shirt, pants, skin=skin, style=style, collection="People")
        objs += tree(P["root"])
    bake_colours(objs)
    return objs


def build_auto():
    A = C.build_auto("AutoRickshaw", collection="Vehicles")
    objs = tree(A["root"])
    bake_colours(objs)
    return objs


def build_street():
    E.build_terrain = lambda: None            # the browser builds the road surface itself (terrain.js)
    E.build_india_street()
    objs = [o for c in ("Street", "Buildings", "Props") if c in U.COLLS for o in U.COLLS[c].objects]
    objs = realize_all(objs)
    bake_colours(objs)
    water = [o for o in objs if o.name == "Puddles"]
    sky = [o for o in objs if o.name in ("Skyline", "EndBlocks")]
    rest = [o for o in objs if o not in water and o not in sky and o.type == "MESH"]
    merged = chunk(join(rest, "Street", "Export"), 16.0, "Export") + [join(sky, "Backdrop", "Export")]
    for o in water:
        o.name = "Water"
    return merged + water


# ----------------------------------------------------------------------------------------------- export
def export(objs, name, draco=True):
    path = os.path.join(OUT, name)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    kw = dict(filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
              export_animations=False, export_lights=False, export_cameras=False, export_extras=False,
              export_texcoords=False, export_normals=True, export_vertex_color="ACTIVE",
              export_active_vertex_color_when_no_material=True, export_materials="EXPORT")
    if draco:
        kw.update(export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
                  export_draco_position_quantization=14, export_draco_normal_quantization=10,
                  export_draco_color_quantization=8)
    bpy.ops.export_scene.gltf(**kw)
    tris = 0
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.type == "MESH":
            me = o.evaluated_get(dg).data
            me.calc_loop_triangles()
            tris += len(me.loop_triangles)
    mats = {m.name for o in objs if o.type == "MESH" for m in o.data.materials if m}
    print(f"EXPORT {name}: {len(objs)} objects, {tris} triangles, {len(mats)} materials, "
          f"{os.path.getsize(path) / 1024:.0f} KB", flush=True)


# ----------------------------------------------------------------------------------------------- animals (no Blender)
def prune_glb(src, dst, clips):
    """Copy a GLB keeping only the named animation clips and the data they, the meshes and the skins use."""
    b = open(src, "rb").read()
    jlen = struct.unpack_from("<I", b, 12)[0]
    js = json.loads(b[20:20 + jlen])
    blen = struct.unpack_from("<I", b, 20 + jlen)[0]
    blob = b[28 + jlen:28 + jlen + blen]
    js["animations"] = [a for a in js.get("animations", []) if a["name"] in clips]
    used = set()
    for m in js["meshes"]:
        for p in m["primitives"]:
            used |= set(p["attributes"].values())
            if "indices" in p:
                used.add(p["indices"])
            for t in p.get("targets", []):
                used |= set(t.values())
    for s in js.get("skins", []):
        if "inverseBindMatrices" in s:
            used.add(s["inverseBindMatrices"])
    for a in js["animations"]:
        for s in a["samplers"]:
            used |= {s["input"], s["output"]}
    amap, accs = {}, []
    for i, a in enumerate(js["accessors"]):
        if i in used:
            amap[i] = len(accs)
            accs.append(a)
    views = {a["bufferView"] for a in accs if "bufferView" in a} | {im["bufferView"] for im in js.get("images", [])
                                                                    if "bufferView" in im}
    vmap, bvs, out = {}, [], bytearray()
    for i, bv in enumerate(js["bufferViews"]):
        if i not in views:
            continue
        o = bv.get("byteOffset", 0)
        nbv = dict(bv, byteOffset=len(out))
        out += blob[o:o + bv["byteLength"]]
        out += b"\0" * (-len(out) % 4)
        vmap[i] = len(bvs)
        bvs.append(nbv)
    for a in accs:
        if "bufferView" in a:
            a["bufferView"] = vmap[a["bufferView"]]
    for m in js["meshes"]:
        for p in m["primitives"]:
            p["attributes"] = {k: amap[v] for k, v in p["attributes"].items()}
            if "indices" in p:
                p["indices"] = amap[p["indices"]]
            if "targets" in p:
                p["targets"] = [{k: amap[v] for k, v in t.items()} for t in p["targets"]]
    for s in js.get("skins", []):
        if "inverseBindMatrices" in s:
            s["inverseBindMatrices"] = amap[s["inverseBindMatrices"]]
    for a in js["animations"]:
        for s in a["samplers"]:
            s["input"], s["output"] = amap[s["input"]], amap[s["output"]]
    for im in js.get("images", []):
        if "bufferView" in im:
            im["bufferView"] = vmap[im["bufferView"]]
    js["accessors"], js["bufferViews"] = accs, bvs
    js["buffers"] = [{"byteLength": len(out)}]
    jb = json.dumps(js, separators=(",", ":")).encode()
    jb += b" " * (-len(jb) % 4)
    with open(dst, "wb") as fh:
        fh.write(struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(jb) + 8 + len(out)))
        fh.write(struct.pack("<I4s", len(jb), b"JSON") + jb)
        fh.write(struct.pack("<I4s", len(out), b"BIN\0") + bytes(out))
    print(f"ANIMAL {os.path.basename(dst)}: clips {[a['name'] for a in js['animations']]}, "
          f"{os.path.getsize(src) / 1024:.0f} -> {os.path.getsize(dst) / 1024:.0f} KB", flush=True)


# ----------------------------------------------------------------------------------------------- sky
def sky():
    img = bpy.data.images.load(SKY)
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)[:, :, :3]
    # background: exposure + gentle highlight roll-off + sRGB, as a JPEG
    x = px * 0.9
    x = x / (1.0 + 0.25 * x)
    srgb = np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.clip(x, 0.0031308, None), 1 / 2.4) - 0.055)
    out = bpy.data.images.new("sky_ldr", w, h, alpha=False)
    out.pixels.foreach_set(np.dstack([np.clip(srgb, 0, 1), np.ones((h, w, 1), np.float32)]).ravel())
    path = os.path.join(OUT, "sky.jpg")
    out.filepath_raw = path
    out.file_format = "JPEG"
    out.save(filepath=path, quality=84)
    # lighting: the HDR at a quarter of the size (the browser blurs it into an environment map anyway)
    img.scale(w // 4, h // 4)
    hdr = os.path.join(OUT, "sky.hdr")
    img.filepath_raw = hdr
    img.file_format = "HDR"
    img.save(filepath=hdr)
    print(f"SKY sky.jpg {os.path.getsize(path) / 1024:.0f} KB, sky.hdr {os.path.getsize(hdr) / 1024:.0f} KB", flush=True)


# ----------------------------------------------------------------------------------------------- main
def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    prune_glb(os.path.join(ANIMALS, "quaternius_shiba_inu.glb"), os.path.join(OUT, "dog_shiba.glb"), DOG_CLIPS)
    prune_glb(os.path.join(ANIMALS, "quaternius_husky.glb"), os.path.join(OUT, "dog_husky.glb"), DOG_CLIPS)
    prune_glb(os.path.join(ANIMALS, "quaternius_cow.glb"), os.path.join(OUT, "cow.glb"), COW_CLIPS)
    reset()
    sky()
    reset()
    export(build_robots(), "robots.glb")
    reset()
    export(build_people(), "people.glb")
    reset()
    export(build_auto(), "auto.glb")
    reset()
    export(build_street(), "street.glb")
    print(f"DONE in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
