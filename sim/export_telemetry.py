"""Export each simulated shot as a Remotion telemetry file (video/src/data/<shot>.telemetry.json).

Follows the contract in video/src/lib/telemetry.ts (one row per rendered frame, same order as the MP4) and adds
`map` (route, potholes, obstacles, places) and per-event `level`/`detail` for the control-room HUD.

  python sim/export_telemetry.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simulate as S  # noqa: E402
import world as W  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "video", "src", "data")
SEVERITY = {"ALARM": "alert", "SAFETY": "warn"}
STATE_ALIAS = {"TURN": "CRUISE"}


def export(sim):
    rec = sim.rec
    n = len(rec["t"])
    frames = []
    for i in range(n):
        frames.append(dict(
            f=i, t=round(rec["t"][i], 3), speed=round(rec["r_v"][i], 3),
            state=STATE_ALIAS.get(rec["r_mode"][i], rec["r_mode"][i]),
            x=round(rec["r_x"][i], 3), y=round(rec["r_y"][i], 3),
            heading=round(math.degrees(rec["r_h"][i]) % 360, 1),
            battery=round(0.84 - 0.000012 * i, 4)))
    events = [dict(frame=e["f"], durationFrames=90, type=e["level"].lower(), level=e["level"],
                   label=e["title"], detail=e["detail"], severity=SEVERITY.get(e["level"], "info"))
              for e in sim.events]
    xs, ys = rec["r_x"], rec["r_y"]
    x0, x1 = min(xs) - 4, max(xs) + 4
    potholes = [dict(x=p.cx, y=p.cy, r=round(max(p.rx, p.ry), 2), depth=p.depth, water=p.water)
                for p in W.POTHOLES if x0 <= p.cx <= x1]
    places = [dict(kind="start", x=W.START[0], y=W.START[1]), dict(kind="gate", x=W.GATE[0], y=W.GATE[1]),
              dict(kind="dogs", x=37.3, y=5.5), dict(kind="cow", x=W.COW[0], y=W.COW[1]),
              dict(kind="thief", x=W.THIEF_HOME[0], y=W.THIEF_HOME[1]),
              dict(kind="breaker", x=W.SPEED_BREAKER_X, y=0.0)]
    data = dict(version=1, scene=sim.name, label=sim.cfg["label"], fps=S.FPS, frameCount=n, frames=frames,
                events=events,
                map=dict(xMin=x0, xMax=x1, roadHalf=W.ROAD_HALF, shoulder=W.SHOULDER, potholes=potholes,
                         places=[p for p in places if x0 - 2 <= p["x"] <= x1 + 2],
                         route=dict(x=sim.to_dict()["path"]["x"], y=sim.to_dict()["path"]["y"])))
    path = os.path.join(OUT, f"{sim.name}.telemetry.json")
    with open(path, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    return path, n, len(events)


def export_us():
    n, frames = 180, []
    for i in range(n):
        t = i / S.FPS
        v = min(1.6, 0.8 * t + 1.2)
        frames.append(dict(f=i, t=round(t, 3), speed=round(v, 3), state="CRUISE", x=round(-4 + 1.4 * t, 3), y=6.1,
                           heading=0.0, battery=0.9))
    data = dict(version=1, scene="us_sidewalk", label="Standard sidewalk robot", fps=S.FPS, frameCount=n,
                frames=frames, events=[], map=None)
    path = os.path.join(OUT, "us_sidewalk.telemetry.json")
    with open(path, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    return path, n, 0


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name in S.SCENARIOS:
        print(*export(S.run(name)))
    print(*export_us())
