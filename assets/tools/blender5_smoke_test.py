"""Blender 5.x smoke test / starter template for the Bharat-Bot street scene.

Builds a tiny Indian-street shot out of the downloaded assets and renders it with EEVEE to an MP4.
Every API call here was verified on Blender 5.2.2 LTS (see research/blender.md for the notes).

    blender -b --factory-startup --python assets/tools/blender5_smoke_test.py -- [OUT_DIR] [N_FRAMES] [WIDTHxHEIGHT]

Defaults: OUT_DIR = <temp>/blender5_smoke, 48 frames, 960x540.  Writes smoke_frame.png and smoke_*.mp4.
Nothing is written inside the project unless you point OUT_DIR there.

World convention (1 unit = 1 m, Z up): road runs along +X, glTF assets face -Y after import, so rotate
Z by +90 deg to make an asset face +X (travel direction), -90 deg for -X, 180 deg for +Y.
"""
import math
import os
import sys
import tempfile
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.abspath(os.path.join(HERE, ".."))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT_DIR = os.path.abspath(argv[0]) if len(argv) > 0 else os.path.join(tempfile.gettempdir(), "blender5_smoke")
N_FRAMES = int(argv[1]) if len(argv) > 1 else 48
RES = tuple(int(v) for v in argv[2].lower().split("x")) if len(argv) > 2 else (960, 540)
FPS = 24
SAMPLES = int(os.environ.get("BB_SAMPLES", "32"))      # EEVEE render samples (TAA)
RAYTRACING = os.environ.get("BB_RT", "0") == "1"          # EEVEE ray tracing (reflections/refraction), costly on an iGPU
os.makedirs(OUT_DIR, exist_ok=True)

# ----------------------------------------------------------------------------- helpers
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def asset(*parts):
    return os.path.join(ASSETS, *parts)


def import_glb(relpath, name, scale=1.0, loc=(0, 0, 0), yaw_deg=90.0, ground_z=0.0):
    """Import a GLB, delete importer junk, wrap it in an empty you can move/rotate/scale freely.

    The empty is lifted so the lowest mesh vertex sits at ground_z (several assets have their origin mid-height:
    Vespa, tree, bush, carts - see the "ground lift" column in research/blender.md).
    """
    before = {o.name for o in bpy.data.objects}
    bpy.ops.import_scene.gltf(filepath=asset(*relpath.split("/")))
    new = [o for o in bpy.data.objects if o.name not in before]
    # FBX2glTF leftovers: leaf-bone empties "*_end" and a stray 2 m "Icosphere" (collect names first,
    # Python references to removed objects become invalid)
    junk = [o.name for o in new if (o.type == "EMPTY" and o.name.endswith("_end")) or o.name.startswith("Icosphere")]
    for n in junk:
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    new = [o for o in bpy.data.objects if o.name not in before]
    holder = bpy.data.objects.new(name, None)
    scene.collection.objects.link(holder)
    for o in new:
        if o.parent is None:
            o.parent = holder
    holder.scale = (scale, scale, scale)
    holder.location = loc
    holder.rotation_euler = (0, 0, math.radians(yaw_deg))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    zmin = math.inf
    for o in new:
        if o.type == "MESH":
            oe = o.evaluated_get(dg)
            for c in oe.bound_box:
                zmin = min(zmin, (oe.matrix_world @ Vector(c)).z)
    if zmin != math.inf:
        holder.location.z += ground_z - zmin
    return holder, new


def find_armature(objs):
    return next((o for o in objs if o.type == "ARMATURE"), None)


def play_action(arm, action_name, cyclic=True):
    """Assign one imported action (the importer parks the rest in muted NLA tracks) and loop it forever."""
    ad = arm.animation_data
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    act = bpy.data.actions[action_name]
    ad.action = act  # 5.x: the single slot is picked automatically
    if cyclic:
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    for fc in cb.fcurves:
                        if not any(m.type == "CYCLES" for m in fc.modifiers):
                            fc.modifiers.new("CYCLES")
    return act


def animate_linear(obj, data_path, index, key_a, key_b):
    """Slotted-action keyframes with the 5.x API: assign action + slot first, then fcurve_ensure_for_datablock."""
    ad = obj.animation_data or obj.animation_data_create()
    if ad.action is None:
        act = bpy.data.actions.new(obj.name + "_move")
        ad.action = act
        ad.action_slot = act.slots.new(id_type="OBJECT", name=obj.name)
    fc = ad.action.fcurve_ensure_for_datablock(obj, data_path, index=index)
    for frame, value in (key_a, key_b):
        kp = fc.keyframe_points.insert(frame, value)
        kp.interpolation = "LINEAR"
    return fc


def pbr_material(name, tex_id, res="1k", tile=(8.0, 8.0, 1.0), tint=None):
    """Poly Haven diff / rough / nor_gl (OpenGL) maps -> Principled BSDF."""
    folder = asset("polyhaven", "textures", tex_id)
    mat = bpy.data.materials.new(name)  # 5.x: creates the default Principled node tree, use_nodes is deprecated
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = tile
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])

    def tex(suffix, colorspace):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(folder, f"{tex_id}_{suffix}_{res}.jpg"))
        n.image.colorspace_settings.name = colorspace
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        return n

    diff = tex("diff", "sRGB")
    if tint:
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs["B"].default_value = tint
        nt.links.new(diff.outputs["Color"], mix.inputs["A"])
        nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    else:
        nt.links.new(diff.outputs["Color"], bsdf.inputs["Base Color"])
    rough = tex("rough", "Non-Color")
    nt.links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
    nor = tex("nor_gl", "Non-Color")
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(nor.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def box(name, size, loc, mat):
    me = bpy.data.meshes.new(name)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.scale = size
    ob.location = loc
    ob.data.materials.append(mat)
    scene.collection.objects.link(ob)
    return ob


# ----------------------------------------------------------------------------- render settings (EEVEE, Blender 5.x)
scene.render.engine = "BLENDER_EEVEE"  # 4.2-4.5 used BLENDER_EEVEE_NEXT, 5.x is BLENDER_EEVEE again
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.fps = FPS
scene.frame_start, scene.frame_end = 1, N_FRAMES
scene.view_settings.view_transform = "AgX"  # or "Standard" / "Khronos PBR Neutral" for faithful brand colours
scene.view_settings.look = "AgX - Punchy"  # look names carry the "AgX - " prefix in 4.x/5.x
scene.view_settings.exposure = -0.8
ee = scene.eevee
ee.taa_render_samples = SAMPLES    # 32 is laptop-friendly; 64 is the default
ee.use_shadows = True
ee.shadow_ray_count = 1
ee.shadow_step_count = 6
ee.use_raytracing = RAYTRACING     # screen-space reflections/refraction: expensive on an iGPU, enable only for hero shots
ee.use_fast_gi = True
ee.fast_gi_method = "GLOBAL_ILLUMINATION"
ee.fast_gi_resolution = "2"
scene.render.use_motion_blur = False  # moved from scene.eevee.use_motion_blur in 4.2

# ----------------------------------------------------------------------------- world: hazy Indian midday sky
world = bpy.data.worlds.new("StreetSky")  # 5.x: node tree (Background + Output) exists on creation
scene.world = world
wt = world.node_tree
sky = wt.nodes.new("ShaderNodeTexSky")
sky.sky_type = "MULTIPLE_SCATTERING"  # NISHITA was split into SINGLE_/MULTIPLE_SCATTERING in 5.0
sky.sun_elevation = math.radians(48)
sky.sun_rotation = math.radians(215)
sky.altitude = 50.0
sky.air_density = 1.0
sky.aerosol_density = 1.6            # was "dust_density"; higher = hazier / dustier
sky.ozone_density = 1.0
wt.links.new(sky.outputs["Color"], wt.nodes["Background"].inputs["Color"])
world.sun_threshold = 10.0           # EEVEE extracts the sky's sun disc as a shadow-casting sun automatically
world.use_sun_shadow = True

# ----------------------------------------------------------------------------- street geometry
road_mat = pbr_material("Road", "road_damaged_2", res="2k", tile=(14, 4, 1))
walk_mat = pbr_material("Footpath", "concrete_pavement_02", tile=(24, 3, 1))
wall_mat = pbr_material("BlueWall", "blue_plaster_weathered", tile=(10, 3, 1))
box("Road", (60, 7.0, 0.1), (0, 0, -0.05), road_mat)
box("Footpath", (60, 2.2, 0.2), (0, 4.6, 0.0), walk_mat)
box("Wall", (60, 0.4, 3.2), (0, 6.0, 1.5), wall_mat)

# ----------------------------------------------------------------------------- characters (scales from assets/CREDITS.md table)
man, man_objs = import_glb("polypizza/humans/quaternius_man.glb", "Man", scale=0.354, loc=(-3.0, 3.9, 0.0), yaw_deg=90, ground_z=0.1)
play_action(find_armature(man_objs), "HumanArmature|Man_Walk")
walk_speed = 4.255 * 0.354           # m/s at which the planted foot does not slide (measured, see research/blender.md)
animate_linear(man, "location", 0, (1, -3.0), (N_FRAMES, -3.0 + walk_speed * N_FRAMES / FPS))

dog, dog_objs = import_glb("polypizza/animals/quaternius_shiba_inu.glb", "StreetDog", scale=0.181, loc=(2.0, -1.0, 0.0), yaw_deg=-90)
play_action(find_armature(dog_objs), "AnimalArmature|Walk")
dog_speed = 2.345 * 0.181
animate_linear(dog, "location", 0, (1, 2.0), (N_FRAMES, 2.0 - dog_speed * N_FRAMES / FPS))

cow, cow_objs = import_glb("polypizza/animals/quaternius_cow.glb", "Cow", scale=0.294, loc=(-0.5, 0.4, 0.0), yaw_deg=180)
play_action(find_armature(cow_objs), "AnimalArmature|Idle")

import_glb("polypizza/vehicles/vespa_scooter_jasmine_roberts.glb", "Vespa", scale=0.411, loc=(-6.0, -1.8, 0.0), yaw_deg=90)
import_glb("polypizza/vehicles/kaylousberg_car_hatchback.glb", "Hatchback", scale=4.7, loc=(6.0, -2.2, 0.0), yaw_deg=-90)
import_glb("polypizza/trees/quaternius_palm_tree_a.glb", "Palm", scale=2.6, loc=(4.5, 5.0, 0.0), yaw_deg=0, ground_z=0.1)
import_glb("polypizza/props/quaternius_dumpster.glb", "Dumpster", scale=0.85, loc=(-6.5, 5.3, 0.0), yaw_deg=0, ground_z=0.1)
import_glb("polypizza/props/quaternius_street_light_a.glb", "StreetLight", scale=1.15, loc=(0.0, 5.3, 0.0), yaw_deg=90, ground_z=0.1)

# ----------------------------------------------------------------------------- self-check: facing convention
def forward_of(arm_obj, left_bone, right_bone):
    """Character forward = left x up, where left = pos(left bone) - pos(right bone), in world space."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ae = arm_obj.evaluated_get(dg)
    left = ae.matrix_world @ ae.pose.bones[left_bone].head - ae.matrix_world @ ae.pose.bones[right_bone].head
    left.z = 0.0
    return left.normalized().cross(Vector((0, 0, 1)))


f_man = forward_of(find_armature(man_objs), "UpperLeg.L", "UpperLeg.R")
f_dog = forward_of(find_armature(dog_objs), "FrontShoulder.L", "FrontShoulder.R")
print("FACING man (yaw +90 expected +X):", tuple(round(v, 2) for v in f_man), "| dog (yaw -90 expected -X):", tuple(round(v, 2) for v in f_dog))
assert f_man.x > 0.9 and f_dog.x < -0.9, "facing convention changed: assets no longer face -Y on import"

# ----------------------------------------------------------------------------- camera (animated with slotted-action F-curves)
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 35
cam_data.dof.use_dof = False
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam.location = (-9.0, -7.5, 1.7)
target = bpy.data.objects.new("CamTarget", None)
target.location = (0.0, 1.0, 0.9)
scene.collection.objects.link(target)
tc = cam.constraints.new("TRACK_TO")
tc.target = target
tc.track_axis = "TRACK_NEGATIVE_Z"
tc.up_axis = "UP_Y"
animate_linear(cam, "location", 0, (1, -9.0), (N_FRAMES, -7.0))

# ----------------------------------------------------------------------------- compositor: bloom (Glare) in 5.x
tree = bpy.data.node_groups.new("Bharat-Bot comp", "CompositorNodeTree")
scene.compositing_node_group = tree          # scene.node_tree no longer exists
tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
rl = tree.nodes.new("CompositorNodeRLayers")
glare = tree.nodes.new("CompositorNodeGlare")
glare.inputs["Type"].default_value = "Bloom"       # all Glare settings are input sockets now (menu sockets take the label)
glare.inputs["Threshold"].default_value = 1.2
glare.inputs["Strength"].default_value = 0.35
glare.inputs["Size"].default_value = 0.55
out = tree.nodes.new("NodeGroupOutput")             # replaces CompositorNodeComposite
tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
tree.links.new(glare.outputs["Image"], out.inputs["Image"])
scene.render.use_compositing = True

# ----------------------------------------------------------------------------- render: one PNG still, then an MP4
ims = scene.render.image_settings
mid = max(1, N_FRAMES // 2)
scene.frame_set(mid)
ims.media_type = "IMAGE"
ims.file_format = "PNG"
ims.color_mode = "RGB"
scene.render.filepath = os.path.join(OUT_DIR, "smoke_frame.png")
t0 = time.perf_counter()
bpy.ops.render.render(write_still=True)
still_s = time.perf_counter() - t0

ims.media_type = "VIDEO"        # must be set BEFORE file_format in 5.x
ims.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "HIGH"
scene.render.ffmpeg.ffmpeg_preset = "GOOD"
scene.render.ffmpeg.audio_codec = "NONE"
scene.render.filepath = os.path.join(OUT_DIR, "smoke_")
t0 = time.perf_counter()
bpy.ops.render.render(animation=True)
anim_s = time.perf_counter() - t0
mp4 = [f for f in os.listdir(OUT_DIR) if f.endswith(".mp4")]
print(f"SMOKE_TEST still {still_s:.1f}s | {N_FRAMES} frames {anim_s:.1f}s ({anim_s / N_FRAMES:.2f}s/frame) at {RES[0]}x{RES[1]} | files: {sorted(os.listdir(OUT_DIR))}")
if not mp4:
    raise SystemExit("SMOKE_TEST FAILED: no mp4 written")
print("SMOKE_TEST OK", OUT_DIR)
