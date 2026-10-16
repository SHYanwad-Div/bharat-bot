"""Export the simulation runs for the browser digital twin (docs/twin): every agent's pose on every frame.

  python sim/export_twin.py

Writes docs/twin/data/<run>.json for the four film scenarios plus "baseline_full" (the standard robot on Bharat-Bot's
full route), docs/twin/data/street.json (the street's potholes and speed breaker, so the browser rebuilds the road
surface with world.terrain_height's arithmetic, plus check points that prove it matches) and web-size copies of the
Poly Haven textures in docs/twin/models/tex. The 3D models come from sim/export_twin_models.py (run in Blender).

A run file holds per-frame channels for the robot (position, heading, pitch, roll, wheel spin, the rocker-bogie's
wheel lift, lid), the food parcel, the three dogs, the thief, the customer and the auto-rickshaw, the same
SENSE -> AI -> SAFETY -> ACT event log as the film's HUD (sim/export_telemetry.py) and the map. Number channels are
{"k": scale, "d": 0/1, "v": [integers]}: value = v / k, and with d = 1 the integers are frame-to-frame differences (a
running sum restores them). Text and on/off channels are runs: [[first frame, value], ...].
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import simulate as S  # noqa: E402
import world as W  # noqa: E402

TWIN = os.path.join(ROOT, "docs", "twin")
DATA = os.path.join(TWIN, "data")
TEX_OUT = os.path.join(TWIN, "models", "tex")
TELEMETRY = os.path.join(ROOT, "video", "src", "data")

# The comparison clips: Bharat-Bot's handling of each failure test, cut from its full run on the same street.
# (robot x where the clip starts, robot x where it may end, event that must have happened, seconds kept after it)
WINDOWS = {
    "pothole": dict(x0=-99.0, x1=16.5, after=None, keep=0.0),
    "dogs": dict(x0=27.5, x1=0.0, after="Back to cruise", keep=0.4),           # ends before the cow comes up
    "theft": dict(x0=49.4, x1=0.0, after="Thief fled · alarm off", keep=1.8),  # ...and before the customer's message
}
BASELINE_FULL_AFTER_STUCK = 8.0      # s of the standard robot's full-route run kept after it gets stuck


# ----------------------------------------------------------------------------------------------- encoding
def num(values, k, delta=False):
    q = np.rint(np.asarray(values, float) * k).astype(np.int64)
    if delta:
        q = np.diff(q, prepend=0)
    return dict(k=k, d=int(delta), v=q.tolist())


def runs(values):
    out = []
    for f, v in enumerate(values):
        if not out or out[-1][1] != v:
            out.append([f, v])
    return out


def unwrap(a):
    return np.unwrap(np.asarray(a, float))


def col(rows, i):
    return [r[i] for r in rows]


# ----------------------------------------------------------------------------------------------- one run
def trim(sim, n):
    """Keep the first n frames of a run (and its events and barks)."""
    sim.rec = {k: v[:n] for k, v in sim.rec.items()}
    sim.events = [e for e in sim.events if e["f"] < n]
    sim.barks = [b for b in sim.barks if b[0] < n]
    return sim


def windows(sim):
    rec = sim.rec
    x = np.array(rec["r_x"])
    n = len(x)
    out = {}
    for key, w in WINDOWS.items():
        f0 = int(np.argmax(x >= w["x0"])) if (x >= w["x0"]).any() else 0
        if w["after"]:
            ev = next(e for e in sim.events if e["title"] == w["after"])
            f1 = ev["f"] + int(w["keep"] * S.FPS)
        else:
            f1 = int(np.argmax(x >= w["x1"]))
        out[key] = [f0, min(n - 1, f1)]
    return out


def encode(sim, name):
    rec = sim.rec
    n = len(rec["t"])
    robot = dict(
        x=num(rec["r_x"], 1000, True), y=num(rec["r_y"], 1000, True), z=num(rec["r_z"], 1000, True),
        h=num(unwrap(rec["r_h"]), 1000, True), pitch=num(rec["r_pitch"], 10000, True),
        roll=num(rec["r_roll"], 10000, True), v=num(rec["r_v"], 1000), s=num(rec["r_s"], 1000, True),
        lid=num(rec["r_lid"], 1000), lidj=num(rec["r_lidj"], 1000),
        spinL=num(col(rec["r_spin"], 0), 1000, True), spinR=num(col(rec["r_spin"], 1), 1000, True),
        **{f"dz{i}": num(col(rec["r_dz"], i), 10000) for i in range(6)},
        mode=runs(rec["r_mode"]), alarm=runs(rec["r_alarm"]), deter=runs(rec["r_deter"]),
        carried=runs(rec["r_carried"]), stuck=runs(rec["r_stuck"]), vis=runs(rec["r_vis"]))
    dogs = []
    for i in range(len(sim.dogs)):
        rows = rec[f"d{i}"]
        dogs.append(dict(x=num(col(rows, 0), 1000, True), y=num(col(rows, 1), 1000, True),
                         h=num(unwrap(col(rows, 2)), 1000, True), lie=num(col(rows, 3), 1000),
                         phase=num(col(rows, 4), 1000, True), bark=num(col(rows, 5), 1000),
                         v=num(col(rows, 6), 1000), state=runs(col(rows, 7))))
    people = {}
    for key in ("thief", "cust"):
        rows = rec[key]
        people[key] = dict(x=num(col(rows, 0), 1000, True), y=num(col(rows, 1), 1000, True),
                           h=num(unwrap(col(rows, 2)), 1000, True), phase=num(col(rows, 3), 1000, True),
                           arm=num(col(rows, 4), 1000), grab=num(col(rows, 5), 1000), phone=num(col(rows, 6), 1000),
                           wave=num(col(rows, 7), 1000), v=num(col(rows, 8), 1000), vis=runs(col(rows, 9)),
                           state=runs(col(rows, 10)))
    au = rec["auto"]
    auto = dict(x=num(col(au, 0), 1000, True), y=num(col(au, 1), 1000, True), h=num(unwrap(col(au, 2)), 1000, True),
                spin=num(col(au, 3), 1000, True), active=runs(col(au, 4)))
    d = sim.to_dict()
    x_lo, x_hi = min(rec["r_x"]), max(rec["r_x"])
    out = dict(
        version=1, run=name, scenario=sim.name, robot=sim.robot, label=sim.cfg["label"], fps=S.FPS, n=n,
        duration=round(n / S.FPS, 3), routeLength=round(sim.path.length, 3), battery=[0.84, -0.000012],
        cfg={k: sim.cfg[k] for k in ("wheel_r", "half_track", "axles", "v_cruise", "max_step", "wading",
                                     "sees_potholes", "dog_protocol", "tamper_alarm", "yields")},
        events=[dict(f=e["f"], t=e["t"], level=e["level"], title=e["title"], detail=e["detail"]) for e in sim.events],
        barks=sim.barks, robotPose=robot, dogs=dogs, thief=people["thief"], cust=people["cust"], auto=auto,
        map=dict(xMin=round(x_lo - 4, 2), xMax=round(x_hi + 4, 2), route=d["path"],
                 potholes=[dict(cx=p["cx"], cy=p["cy"], rx=p["rx"], ry=p["ry"], rot=p["rot"], depth=p["depth"],
                                water=p["water"], detect=p["detect_f"], passed=p["pass_f"]) for p in d["potholes"]],
                 places=[dict(kind="start", x=W.START[0], y=W.START[1]), dict(kind="breaker", x=W.SPEED_BREAKER_X, y=0.0),
                         dict(kind="dogs", x=37.3, y=5.5), dict(kind="cow", x=W.COW[0], y=W.COW[1]),
                         dict(kind="thief", x=W.THIEF_HOME[0], y=W.THIEF_HOME[1]),
                         dict(kind="gate", x=W.GATE[0], y=W.GATE[1])]))
    if sim.name == "bharat_full" and sim.robot == "bharat":
        out["bag"] = dict(x=num(col(rec["bag"], 0), 1000, True), y=num(col(rec["bag"], 1), 1000, True),
                          z=num(col(rec["bag"], 2), 1000, True))
        out["windows"] = windows(sim)
    return out


def check_events(name, events):
    """The twin's log must be the film HUD's log: compare with video/src/data/<name>.telemetry.json."""
    path = os.path.join(TELEMETRY, f"{name}.telemetry.json")
    if not os.path.exists(path):
        return "no telemetry file to compare"
    with open(path, encoding="utf-8") as fh:
        tel = json.load(fh)["events"]
    mine = [(e["f"], e["level"], e["title"], e["detail"]) for e in events]
    film = [(e["frame"], e["level"], e["label"], e["detail"]) for e in tel]
    return "same events as the film HUD" if mine == film else "WARNING: events differ from the film HUD telemetry"


def write(name, data):
    os.makedirs(DATA, exist_ok=True)
    path = os.path.join(DATA, f"{name}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, separators=(",", ":"), ensure_ascii=False)
    return path, os.path.getsize(path)


# ----------------------------------------------------------------------------------------------- street
def street():
    rng = np.random.default_rng(2026)
    pts = [(float(rng.uniform(W.X0, W.X1)), float(rng.uniform(-W.BUILD_Y, W.BUILD_Y))) for _ in range(120)]
    for p in W.POTHOLES:                    # most checks where the arithmetic is busiest: in and round the holes
        for _ in range(12):
            a, r = rng.uniform(0, 2 * math.pi), rng.uniform(0, p.reach)
            pts.append((p.cx + r * math.cos(a), p.cy + r * math.sin(a)))
    for _ in range(20):
        pts.append((float(W.SPEED_BREAKER_X + rng.uniform(-0.6, 0.6)), float(rng.uniform(-3.6, 3.6))))
    xs, ys = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
    checks = np.c_[xs, ys, W.terrain_height(xs, ys), W.water_depth(xs, ys), W.road_mask(xs, ys), W.pothole_depth(xs, ys)]
    sb = W.SPEED_BREAKERS[0]
    return dict(
        version=1, roadHalf=W.ROAD_HALF, shoulder=W.SHOULDER, buildY=W.BUILD_Y, x0=W.X0, x1=W.X1,
        speedBreaker=dict(x0=sb.x0, width=sb.width, height=sb.height),
        potholes=[dict(cx=p.cx, cy=p.cy, rx=p.rx, ry=p.ry, depth=p.depth, rot=p.rot, water=p.water,
                       ph=[float(v) for v in p.ph], reach=p.reach,
                       level=W.water_level(p) if p.water > 0 else None) for p in W.POTHOLES],
        places=dict(start=W.START, gate=W.GATE, dogHomes=W.DOG_HOMES, cow=W.COW, thiefHome=W.THIEF_HOME, alley=W.ALLEY,
                    customerHome=W.CUSTOMER_HOME),
        obstacles=[list(o) for o in W.STATIC_OBSTACLES],
        checks=np.round(checks, 9).tolist())


# ----------------------------------------------------------------------------------------------- textures
TEXTURES = [  # (Poly Haven id, map, size, JPEG quality)
    ("asphalt_02", "diff", 1024, 82), ("asphalt_02", "nor_gl", 1024, 88),
    ("road_damaged_2", "diff", 1024, 80),
    ("red_laterite_soil_stones", "diff", 1024, 80), ("red_laterite_soil_stones", "nor_gl", 512, 88),
    ("red_dirt_mud_01", "diff", 512, 82),
    ("painted_plaster_wall", "diff", 512, 82),
]


def textures():
    from PIL import Image
    os.makedirs(TEX_OUT, exist_ok=True)
    out = []
    for tid, kind, size, q in TEXTURES:
        src = next((p for p in (os.path.join(ROOT, "assets", "polyhaven", "textures", tid, f"{tid}_{kind}_{r}.jpg")
                                for r in ("1k", "2k")) if os.path.exists(p)), None)
        if src is None:
            print("missing texture", tid, kind)
            continue
        dst = os.path.join(TEX_OUT, f"{tid}_{kind}.jpg")
        Image.open(src).convert("RGB").resize((size, size), Image.LANCZOS).save(dst, quality=q, optimize=True)
        out.append((os.path.basename(dst), os.path.getsize(dst)))
    return out


# ----------------------------------------------------------------------------------------------- main
def main():
    total = 0
    for name in S.SCENARIOS:
        sim = S.run(name)
        data = encode(sim, name)
        path, size = write(name, data)
        total += size
        print(f"{name}: {data['n']} frames, {len(data['events'])} events, {size / 1024:.0f} KB; {check_events(name, sim.events)}")
        if "windows" in data:
            print("   comparison clips (frames):", data["windows"])
    sim = S.Sim("bharat_full", robot="baseline").run()
    stuck = next(e["f"] for e in sim.events if e["level"] == "ALARM")
    trim(sim, min(len(sim.rec["t"]), stuck + int(BASELINE_FULL_AFTER_STUCK * S.FPS)))
    data = encode(sim, "baseline_full")
    path, size = write("baseline_full", data)
    total += size
    print(f"baseline_full: {data['n']} frames, {len(data['events'])} events, {size / 1024:.0f} KB")
    path, size = write("street", street())
    total += size
    print(f"street: {size / 1024:.0f} KB; data total {total / 1024:.0f} KB")
    tex = textures()
    print("textures:", ", ".join(f"{n} {s / 1024:.0f} KB" for n, s in tex), f"= {sum(s for _, s in tex) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
