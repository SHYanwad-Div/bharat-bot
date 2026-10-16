#!/usr/bin/env python3
"""Inspect .glb / .gltf files WITHOUT Blender (stdlib only).

Reads the JSON chunk of each file and reports: file size, node / mesh / skin / joint
counts, triangle count, materials / textures, animation clips (name, duration, channel
count), glTF-space bounding box (units are metres by the glTF spec), long axis, and
the glTF extensions used.

Usage:
    python -I inspect_glb.py FILE_OR_DIR [FILE_OR_DIR ...] [--json out.json] [--md]

glTF conventions (what a Blender import will convert):
    glTF is Y-up, +Z is "front", +X is "left" of a front-facing asset, right-handed.
    Blender's glTF importer maps (x, y, z)_gltf -> (x, -z, y)_blender, so an asset that
    faces +Z in the file faces -Y in Blender (Blender's "front view" convention).
"""
import json
import math
import os
import struct
import sys

COMPONENT_BYTES = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
TYPE_COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}


def read_gltf(path):
    """Return (json_dict, container) where container is 'glb' or 'gltf'."""
    with open(path, "rb") as f:
        head = f.read(4)
        f.seek(0)
        if head == b"glTF":
            data = f.read()
            magic, version, length = struct.unpack_from("<4sII", data, 0)
            off, doc = 12, None
            while off < len(data):
                clen, ctype = struct.unpack_from("<II", data, off)
                if ctype == 0x4E4F534A:  # 'JSON'
                    doc = json.loads(data[off + 8: off + 8 + clen].decode("utf8"))
                off += 8 + clen
            if doc is None:
                raise ValueError("no JSON chunk")
            return doc, "glb"
        return json.loads(f.read().decode("utf8")), "gltf"


# ---- tiny 4x4 matrix helpers (column-major lists of 16, as in glTF) ------------------
def ident():
    return [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]


def mat_mul(a, b):
    out = [0.0] * 16
    for c in range(4):
        for r in range(4):
            out[c * 4 + r] = sum(a[k * 4 + r] * b[c * 4 + k] for k in range(4))
    return out


def trs_to_mat(t, q, s):
    x, y, z, w = q
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z
    sx, sy, sz = s
    return [
        (1 - 2 * (yy + zz)) * sx, (2 * (xy + wz)) * sx, (2 * (xz - wy)) * sx, 0,
        (2 * (xy - wz)) * sy, (1 - 2 * (xx + zz)) * sy, (2 * (yz + wx)) * sy, 0,
        (2 * (xz + wy)) * sz, (2 * (yz - wx)) * sz, (1 - 2 * (xx + yy)) * sz, 0,
        t[0], t[1], t[2], 1,
    ]


def node_local(node):
    if "matrix" in node:
        return list(node["matrix"])
    return trs_to_mat(node.get("translation", [0, 0, 0]),
                      node.get("rotation", [0, 0, 0, 1]),
                      node.get("scale", [1, 1, 1]))


def xform_point(m, p):
    return [m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12],
            m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
            m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14]]


def inspect(path):
    doc, container = read_gltf(path)
    acc = doc.get("accessors", [])
    nodes = doc.get("nodes", [])
    meshes = doc.get("meshes", [])
    skins = doc.get("skins", [])
    anims = doc.get("animations", [])

    # world matrices for every node (walk the scene graph)
    world = {}
    parent_of = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent_of[c] = i

    def world_of(i):
        if i in world:
            return world[i]
        m = node_local(nodes[i])
        if i in parent_of:
            m = mat_mul(world_of(parent_of[i]), m)
        world[i] = m
        return m

    # triangles + bounds
    tris = 0
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    local_lo = [math.inf] * 3
    local_hi = [-math.inf] * 3
    skinned_meshes = 0
    for mesh in meshes:
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) == 4:
                if "indices" in prim:
                    tris += acc[prim["indices"]]["count"] // 3
                elif "POSITION" in prim.get("attributes", {}):
                    tris += acc[prim["attributes"]["POSITION"]]["count"] // 3
    for i, n in enumerate(nodes):
        if "mesh" not in n:
            continue
        is_skinned = "skin" in n
        skinned_meshes += 1 if is_skinned else 0
        for prim in meshes[n["mesh"]].get("primitives", []):
            pa = prim.get("attributes", {}).get("POSITION")
            if pa is None or "min" not in acc[pa]:
                continue
            mn, mx = acc[pa]["min"], acc[pa]["max"]
            corners = [[x, y, z] for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])]
            for p in corners:
                for k in range(3):
                    local_lo[k] = min(local_lo[k], p[k])
                    local_hi[k] = max(local_hi[k], p[k])
                # per the glTF spec a skinned mesh ignores its node transform
                q = p if is_skinned else xform_point(world_of(i), p)
                for k in range(3):
                    lo[k] = min(lo[k], q[k])
                    hi[k] = max(hi[k], q[k])
    have_bounds = lo[0] != math.inf
    size = [hi[k] - lo[k] for k in range(3)] if have_bounds else None

    # animation clips
    clips = []
    for a in anims:
        duration = 0.0
        for s in a.get("samplers", []):
            inp = acc[s["input"]]
            if "max" in inp:
                duration = max(duration, inp["max"][0])
        paths = sorted({c["target"].get("path", "?") for c in a.get("channels", [])})
        clips.append({"name": a.get("name", ""), "duration_s": round(duration, 3),
                      "channels": len(a.get("channels", [])), "paths": paths})

    joints = sum(len(s.get("joints", [])) for s in skins)
    node_names = [n.get("name", "") for n in nodes]
    if container == "glb":
        total_bytes = os.path.getsize(path)
    else:  # .gltf + external files: add up the files it references
        base = os.path.dirname(path)
        total_bytes = os.path.getsize(path)
        for coll in ("buffers", "images"):
            for e in doc.get(coll, []):
                uri = e.get("uri")
                if uri and not uri.startswith("data:"):
                    fp = os.path.join(base, uri.replace("/", os.sep))
                    if os.path.exists(fp):
                        total_bytes += os.path.getsize(fp)

    long_axis = None
    if size:
        horiz = {"x": size[0], "z": size[2]}
        long_axis = max(horiz, key=horiz.get)
    out = {
        "file": os.path.basename(path),
        "container": container,
        "bytes": total_bytes,
        "generator": doc.get("asset", {}).get("generator"),
        "asset_copyright": doc.get("asset", {}).get("copyright"),
        "nodes": len(nodes),
        "meshes": len(meshes),
        "mesh_nodes": sum(1 for n in nodes if "mesh" in n),
        "skins": len(skins),
        "joints": joints,
        "triangles": tris,
        "materials": len(doc.get("materials", [])),
        "textures": len(doc.get("textures", [])),
        "images": len(doc.get("images", [])),
        "animations": clips,
        "extensions_used": doc.get("extensionsUsed", []),
        "extensions_required": doc.get("extensionsRequired", []),
        "bbox_size_gltf_xyz_m": [round(v, 3) for v in size] if size else None,
        "bbox_min_gltf": [round(v, 3) for v in lo] if have_bounds else None,
        "bbox_max_gltf": [round(v, 3) for v in hi] if have_bounds else None,
        "mesh_local_size_xyz": [round(local_hi[k] - local_lo[k], 3) for k in range(3)] if have_bounds else None,
        "skinned_mesh_nodes": skinned_meshes,
        "long_horizontal_axis_gltf": long_axis,
        "root_nodes": [nodes[i].get("name", str(i)) for i in doc.get("scenes", [{}])[doc.get("scene", 0)].get("nodes", [])] if doc.get("scenes") else [],
    }
    return out


def collect(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                for n in sorted(names):
                    if n.lower().endswith((".glb", ".gltf")):
                        files.append(os.path.join(root, n))
        else:
            files.append(p)
    return files


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    json_out = None
    if "--json" in argv:
        json_out = argv[argv.index("--json") + 1]
        args = [a for a in args if a != json_out]
    if not args:
        print(__doc__)
        return 1
    rows = []
    for f in collect(args):
        try:
            rows.append(inspect(f) | {"path": f.replace(os.sep, "/")})
        except Exception as e:  # keep going on a bad file
            rows.append({"file": os.path.basename(f), "path": f.replace(os.sep, "/"), "error": str(e)})
    if json_out:
        with open(json_out, "w", encoding="utf8") as fh:
            json.dump(rows, fh, indent=1, ensure_ascii=False)
    for r in rows:
        if "error" in r:
            print(f"{r['path']}: ERROR {r['error']}")
            continue
        clips = ", ".join(f"{c['name']}({c['duration_s']}s)" for c in r["animations"]) or "-"
        print(f"{r['path']}: {r['bytes']/1024:.0f} KB, nodes={r['nodes']}, tris={r['triangles']}, "
              f"joints={r['joints']}, size(gltf xyz)={r['bbox_size_gltf_xyz_m']}, anims=[{clips}]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
