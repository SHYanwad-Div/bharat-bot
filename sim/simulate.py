"""Bharat-Bot street simulation: lattice path planner, robot terrain kinematics and reactive street agents.

Pure Python + numpy, so it runs standalone (python simulate.py all) or inside Blender (build_scene.py imports it).
Every run produces a per-frame timeline (robot, dogs, thief, customer, auto-rickshaw) plus an event log that follows
the GH-01 rule: SENSE -> AI suggests -> SAFETY decides -> ACT, with OK / ALARM outcomes.

Without a seed each scenario is the film's run: one fixed street, fixed agent behaviour, byte-identical every time.
Sim(name, seed=n) instead draws the street and the agents from the research's ranges (world.STREET_RANGES,
AGENT_RANGES), lets either robot drive any scenario and applies the evaluation rules (see EVAL_SETUP and
Sim.eval_checks); evaluate.py runs hundreds of those.  python simulate.py bharat_full --seed 7 [--robot baseline]
prints one of them.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world as W  # noqa: E402

FPS = 30
DT = 1.0 / FPS

ROBOTS = {
    "bharat": dict(label="Bharat-Bot (India-adapted)", wheel_r=0.16, half_track=0.35, axles=(0.38, 0.0, -0.38),
                   clearance=0.20, max_step=0.18, travel=0.10, v_cruise=1.6, accel=0.8, decel=1.4, half_w=0.39,
                   sees_potholes=True, dog_protocol=True, tamper_alarm=True, yields=True, wading=0.08),
    "baseline": dict(label="Standard sidewalk robot", wheel_r=0.09, half_track=0.30, axles=(0.32, 0.0, -0.32),
                     clearance=0.07, max_step=0.06, travel=0.0, v_cruise=1.6, accel=0.8, decel=1.4, half_w=0.33,
                     sees_potholes=False, dog_protocol=False, tamper_alarm=False, yields=False, wading=0.03),
}

SCENARIOS = {
    "bharat_full": dict(robot="bharat", route="full", t_max=120.0, agents=("dogs", "auto", "thief", "customer")),
    "baseline_pothole": dict(robot="baseline", route=("line", 2.0, 2.85, 14.0), t_max=7.5, agents=()),
    "baseline_dogs": dict(robot="baseline", route=("line", 27.5, 2.8, 46.0), t_max=10.5, agents=("dogs",)),
    "baseline_theft": dict(robot="baseline", route=("line", 49.4, 2.8, 63.0), t_max=14.0, agents=("thief",)),
}

SPEED_REASONS = ["CRUISE", "TURN", "POTHOLE AVOID", "SPEED BREAKER", "WADING", "DOG HOTSPOT", "ARRIVING"]
DOG_TRIGGER = 5.5        # m: a resting pack reacts to a moving robot this close

# ----------------------------------------------------------------------------------------------- seeded runs
# The film's agents, and the ranges a seeded run draws them from: (min, typ, max, source) as in world.STREET_RANGES
# ("§5" = research/india-delivery-robots.md section 5, [E] = estimate; typ None = uniform).
AGENT_DEFAULTS = dict(dog_trigger=DOG_TRIGGER, dog_chase_v=3.4, dog_calm_base=0.03, dog_calm_deter=0.12,
                      auto_x=41.5, auto_gap=30.0, auto_v=7.2, auto_v_cow=5.5,
                      thief=True, thief_home=W.THIEF_HOME, thief_trigger=5.8, thief_lid=1.6)
AGENT_RANGES = {
    "dog_trigger_m": (6.0, 10.0, 15.0, "§5 dogs.notice_distance_m (film: 5.5)"),
    "dog_chase_speed_mps": (4.5, 6.0, 8.9, "§5 dogs.chase_speed_mps (film: 3.4)"),
    "dog_give_up_s": (5.0, 12.0, 30.0, "§5 dogs.give_up_time_if_robot_stationary_s (film: about 4.5)"),
    "auto_speed_kmh": (10.0, 20.0, 55.0, "§5 people_and_traffic.autorickshaw_speed_kmh (film: 26)"),
    "auto_appears_at_x_m": (30.0, None, 46.0, "[E] where the robot is when the auto turns in (film: 41.5)"),
    "auto_gap_m": (20.0, None, 60.0, "[E] how far behind the robot it turns in, never closer than its stopping "
                                      "sight distance (film: 30)"),
    "thief_home_x_m": (54.5, None, 58.5, "[E] where the thief waits (film: 56.9)"),
    "thief_trigger_m": (3.5, None, 9.0, "[E] how close the robot is when he steps out (film: 5.8)"),
    "thief_lid_s": (1.0, None, 3.0, "[E] how long he pulls at the lid before lifting (film: 1.6)"),
}
DOG_GIVE_UP_FILM = 4.5   # s: how long the film's pack takes to lose interest in a still, silent robot

# Per scenario: the street (random potholes between these x; None = a smooth street, so one hazard is tested at a
# time), a route if it differs from the film's (whose dog segment ends inside the cow), and the chance the thief turns
# up (0.5 on the full route is a stress test: §5 puts real attempts at 0.2-3 % of deliveries). Every seeded run gets
# a time budget of its route at EVAL_MIN_SPEED plus EVAL_SLACK seconds of waiting.
EVAL_SETUP = {
    "bharat_full": dict(street=(5.0, 59.0), thief_p=0.5),
    "baseline_pothole": dict(street=(2.0, 14.0), thief_p=0.0),
    "baseline_dogs": dict(street=None, route=("line", 27.5, 2.8, 44.0), thief_p=0.0),
    "baseline_theft": dict(street=None, thief_p=1.0),
}
EVAL_MIN_SPEED, EVAL_SLACK = 0.5, 30.0
AUTO_FRONT, AUTO_REAR, AUTO_HALF_W = 1.33, 1.325, 0.65     # auto-rickshaw footprint about its (x, y): §5 2.64 x 1.30 m
AUTO_Y_MIN = 0.15        # [E] a driver uses at most 0.5 m of the oncoming lane to get round something
AUTO_PASS_GAP = 0.35     # [E] lateral room a driver leaves when passing the robot
AUTO_BRAKE = 4.0         # [E] m/s^2, firm braking
DOG_HALF = (0.40, 0.15)  # §5 dogs.body_size_m 0.8 x 0.3
PERSON_R = 0.25          # [E]


def eval_world(scenario, seed):
    """The street of seeded run `seed` of a scenario (the same for every robot)."""
    st = EVAL_SETUP[scenario]["street"]
    return W.World.random(seed, st or (5.0, 59.0), potholes=st is not None)


def sample_agents(seed, thief_p):
    """Agents for seeded run `seed`: the same draws for every robot and scenario, except whether the thief comes."""
    rng = np.random.default_rng([seed, 2])

    def d(key):
        return W.draw(rng, key, AGENT_RANGES)

    give_up, kmh = d("dog_give_up_s"), d("auto_speed_kmh")
    p = dict(AGENT_DEFAULTS, dog_trigger=d("dog_trigger_m"), dog_chase_v=d("dog_chase_speed_mps"), dog_give_up=give_up,
             auto_x=d("auto_appears_at_x_m"), auto_gap=d("auto_gap_m"), auto_v=kmh / 3.6, auto_v_cow=kmh / 3.6 * 5.5 / 7.2,
             thief_home=(d("thief_home_x_m"), W.THIEF_HOME[1]), thief_trigger=d("thief_trigger_m"),
             thief_lid=d("thief_lid_s"))
    k = DOG_GIVE_UP_FILM / give_up          # the pack's agitation fades this much faster than the film's
    v = p["auto_v"]
    p.update(dog_calm_base=0.03 * k, dog_calm_deter=0.12 * k, thief=bool(rng.random() < thief_p),
             auto_gap=max(p["auto_gap"], 1.5 * v + v * v / (2 * AUTO_BRAKE) + 3.0))   # 1.5 s to react, then brake
    return p


def box(cx, cy, h, back, front, half_w):
    """Corners of a rectangle lying along heading h (back/front measured along h from (cx, cy))."""
    c, s = math.cos(h), math.sin(h)
    return [(cx + u * c - v * s, cy + u * s + v * c) for u, v in
            ((back, -half_w), (front, -half_w), (front, half_w), (back, half_w))]


def _seg_dist(px, py, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    t = clamp(((px - a[0]) * vx + (py - a[1]) * vy) / (vx * vx + vy * vy), 0.0, 1.0)
    return math.hypot(px - a[0] - t * vx, py - a[1] - t * vy)


def gap(P, Q):
    """Signed clearance between two convex polygons: their distance apart, or minus their overlap."""
    overlap = math.inf
    for poly in (P, Q):
        for i in range(len(poly)):
            (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
            nx, ny = ay - by, bx - ax
            n = math.hypot(nx, ny)
            p = [(x * nx + y * ny) / n for x, y in P]
            q = [(x * nx + y * ny) / n for x, y in Q]
            o = min(max(p), max(q)) - max(min(p), min(q))
            if o <= 0:
                return min(min(_seg_dist(x, y, Q[j], Q[(j + 1) % len(Q)]) for x, y in P for j in range(len(Q))),
                           min(_seg_dist(x, y, P[j], P[(j + 1) % len(P)]) for x, y in Q for j in range(len(P))))
            overlap = min(overlap, o)
    return -overlap


def gap_point(P, px, py, r):
    """Signed clearance between a convex polygon and a disc."""
    inside = all((b[0] - a[0]) * (py - a[1]) - (b[1] - a[1]) * (px - a[0]) >= 0 for a, b in zip(P, P[1:] + P[:1]))
    return -r if inside else min(_seg_dist(px, py, a, b) for a, b in zip(P, P[1:] + P[:1])) - r


def pothole_relevant(path, p):
    """Is this pothole near enough to the planned route to matter to the robot?"""
    k = int(np.argmin(np.abs(path.x - p.cx)))
    return abs(path.y[k] - p.cy) < p.ry * 1.25 + 0.9 and abs(path.x[k] - p.cx) < 0.5


# ----------------------------------------------------------------------------------------------- helpers
def clamp(v, a, b):
    return a if v < a else b if v > b else v


def approach(v, target, step):
    return min(v + step, target) if v < target else max(v - step, target)


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def turn_toward(h, target, step):
    d = wrap(target - h)
    return h + clamp(d, -step, step)


def sstep(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def gaussian_smooth(a, sigma):
    a = np.asarray(a, float)
    if sigma <= 0:
        return a.copy()
    r = max(1, int(3 * sigma + 0.5))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(a, r, mode="edge"), k, mode="valid")


def bezier(p0, p1, p2, p3, n):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, float) for p in (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


class Path:
    """Arc-length parametrised, smoothed 2D polyline."""

    def __init__(self, pts, step=0.05, smooth=0.25):
        pts = np.asarray(pts, float)
        pts = pts[np.r_[True, np.hypot(*np.diff(pts, axis=0).T) > 1e-6]]
        x, y = pts[:, 0], pts[:, 1]
        for _ in range(2):
            s = np.r_[0.0, np.cumsum(np.hypot(np.diff(x), np.diff(y)))]
            n = max(2, int(round(s[-1] / step)) + 1)
            ss = np.linspace(0.0, s[-1], n)
            x, y = np.interp(ss, s, x), np.interp(ss, s, y)
            if _ == 0 and smooth > 0:
                sg = smooth / (ss[1] - ss[0])
                x, y = gaussian_smooth(x, sg), gaussian_smooth(y, sg)
        self.s, self.x, self.y = ss, x, y
        self.length = float(ss[-1])
        self.ds = float(ss[1] - ss[0])
        self.h = np.unwrap(np.arctan2(np.gradient(y), np.gradient(x)))
        self.k = np.abs(gaussian_smooth(np.gradient(self.h) / self.ds, 3))

    def at(self, s):
        s = clamp(s, 0.0, self.length)
        return (float(np.interp(s, self.s, self.x)), float(np.interp(s, self.s, self.y)),
                float(np.interp(s, self.s, self.h)))


# ----------------------------------------------------------------------------------------------- planning
def dp_lane(cfg, xa, xb, y0, y1, y_pref=2.8, dx=0.5, Wm=W):
    """Lattice planner: dynamic programming over (station x, lateral y). Cost = pothole depth under the
    robot's footprint + standing water + clearance to obstacles + keep-left preference + smoothness."""
    xs = np.arange(xa, xb + 1e-9, dx)
    ys = np.round(np.arange(0.70, 3.151, 0.05), 3)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    dep = np.zeros_like(X)
    wat = np.zeros_like(X)
    for ox in (-0.44, -0.22, 0.0, 0.22, 0.44):
        for oy in (-0.36, -0.18, 0.0, 0.18, 0.36):
            dep = np.maximum(dep, Wm.pothole_depth(X + ox, Y + oy))
            wat = np.maximum(wat, Wm.water_depth(X + ox, Y + oy))
    cost = 2.5 * (Y - y_pref) ** 2
    if cfg["sees_potholes"]:
        cost += np.where(dep > 0.012, 30.0 + 600.0 * dep, 0.0)
        cost += np.where(wat > cfg["wading"], 1e4, 40.0 * wat)
    for kind, ax, ay, bx, by, r in Wm.STATIC_OBSTACLES:
        d = Wm.capsule_distance(X, Y, ax, ay, bx, by) - r - cfg["half_w"]
        cost += np.where(d < 0.25, 1e5, 0.0) + np.where(d < 1.2, 2.0 / (np.maximum(d, 0.05) + 0.1), 0.0)
    cost[0] += 60 * (ys - y0) ** 2
    cost[-1] += 60 * (ys - y1) ** 2
    n, m = cost.shape
    dyy = ys[None, :] - ys[:, None]
    trans = 8.0 * dyy ** 2 + np.where(np.abs(dyy) > 0.36, 1e6, 0.0)
    J = cost[0].copy()
    back = np.zeros((n, m), int)
    for k in range(1, n):
        tot = J[:, None] + trans
        back[k] = np.argmin(tot, axis=0)
        J = tot[back[k], np.arange(m)] + cost[k]
    j = int(np.argmin(J))
    yk = np.empty(n)
    for k in range(n - 1, -1, -1):
        yk[k] = ys[j]
        j = back[k, j]
    return xs, gaussian_smooth(yk, 0.8)


def build_route(sc, cfg, Wm=W, route=None, plan_lines=False):
    """The film's route for scenario sc (or `route`). plan_lines: a straight segment is planned with dp_lane too, so
    a robot that sees potholes can steer round them (seeded runs)."""
    route = route or sc["route"]
    if route == "full":
        xa, xb, y0, y1 = 3.5, 61.0, 2.9, 2.8
        merge = bezier(Wm.START[:2], (0.6, Wm.START[1]), (1.9, y0), (xa, y0), 40)
        xs, ys = dp_lane(cfg, xa, xb, y0, y1, Wm=Wm)
        lane = np.c_[xs, ys]
        gx, gy = Wm.GATE
        turn = bezier((xb, y1), (xb + 1.9, y1), (gx, y1 + 0.9), (gx, gy), 50)
        return Path(np.vstack([merge, lane[1:], turn[1:]]))
    _, x0, y, x1 = route
    if plan_lines:
        xs, ys = dp_lane(cfg, x0, x1, y, y, y_pref=y, Wm=Wm)
        return Path(np.c_[xs, ys])
    return Path(np.array([[x0, y], [x1, y]]), smooth=0)


def speed_profile(path, cfg, Wm=W):
    """Speed limit along the path plus a zone label for the HUD (the label marks the zone, not the binding cap)."""
    n = len(path.s)
    v = np.full(n, cfg["v_cruise"])
    why = np.zeros(n, int)
    v = np.minimum(v, np.sqrt(0.55 / np.maximum(path.k, 1e-4)))
    why[v < cfg["v_cruise"] - 1e-6] = 1
    if cfg.get("dog_map", cfg["sees_potholes"]):         # fleet map of dog hotspots (comes with the terrain map)
        hot = (path.x > 28.5) & (path.x < 41.0)
        v[hot] = np.minimum(v[hot], 1.15)
        why[hot] = 5
    if cfg["sees_potholes"]:
        for p in Wm.POTHOLES:
            if p.depth > 0.06 and pothole_relevant(path, p):
                near = np.abs(path.x - p.cx) < p.rx + 1.8
                v[near] = np.minimum(v[near], 1.0)
                why[near] = 2
        ahead = Wm.water_depth(path.x + 0.6 * np.cos(path.h), path.y + 0.6 * np.sin(path.h))
        wet = np.maximum(ahead, Wm.water_depth(path.x, path.y)) > 0.004
        v[wet] = np.minimum(v[wet], 0.65)
        why[wet] = 4
        for sb in Wm.SPEED_BREAKERS:
            m = np.abs(path.x - sb.x0) < 0.75
            v[m] = np.minimum(v[m], 0.6)
            why[np.abs(path.x - sb.x0) < 1.8] = 3
    why[path.s > path.length - 3.0] = 6
    v[-1] = 0.0
    ds = path.ds
    for i in range(n - 2, -1, -1):
        v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2 * cfg["decel"] * 0.7 * ds))
    return v, why


# ----------------------------------------------------------------------------------------------- agents
class Robot:
    def __init__(self, cfg, path):
        self.cfg, self.path = cfg, path
        self.s = 0.0
        self.v = 0.0
        self.x, self.y, self.h = path.at(0.0)
        self.z = self.pitch = self.roll = 0.0
        self.dz = [0.0] * 6
        self.spin = [0.0, 0.0]          # left, right wheel angle (rad)
        self.mode = "CRUISE"
        self.why = 0
        self.lift = self.tilt = 0.0
        self.lid = 0.0
        self.lid_target = 0.0
        self.lidj = 0.0
        self.alarm = False
        self.t_alarm = -1.0
        self.deterrent = False
        self.tamper = False
        self.stuck = False
        self.carried = False
        self.dog_stop = False
        self.creep = False
        self.hold = False
        self.arrived = False
        self.unlocked = False
        self.delivered = False
        self.retry_t = 0.0
        self.go_t = 0.0


class Dog:
    def __init__(self, i, home, p=AGENT_DEFAULTS):
        self.i, self.home = i, home
        self.x, self.y, self.h = home
        self.state = "REST"
        self.lie, self.agit, self.v, self.phase = 1.0, 0.0, 0.0, 0.9 * i
        self.bark, self.next_bark, self.timer = 0.0, 0.0, 0.0
        self.calm = False
        self.slot = (0.42, 1.55, 2.55)[i]
        self.rad = (1.45, 1.30, 1.45)[i]
        self.rng = np.random.default_rng(40 + i)
        self.trigger, self.chase_v = p["dog_trigger"], p["dog_chase_v"]
        self.calm_base, self.calm_deter = p["dog_calm_base"], p["dog_calm_deter"]

    def update(self, sim):
        R = sim.R
        d = math.hypot(self.x - R.x, self.y - R.y)
        moved = 0.0
        if self.state == "REST":
            self.lie = approach(self.lie, 1.0, 0.7 * DT)
            self.v = 0.0
            if sim.enabled("dogs") and (d < 3.5 and R.v > 1.2 if self.calm else d < self.trigger and R.v > 0.25):
                sim.pack_alert(d)
        elif self.state == "ALERT":
            self.lie = approach(self.lie, 0.0, 3.0 * DT)
            self.h = turn_toward(self.h, math.atan2(R.y - self.y, R.x - self.x), 4.0 * DT)
            self.timer -= DT
            if self.timer <= 0:
                self.state = "CHASE"
        elif self.state == "CHASE":
            self.lie = approach(self.lie, 0.0, 3.0 * DT)
            a = R.h + self.slot
            tx, ty = R.x + self.rad * math.cos(a), R.y + self.rad * math.sin(a)
            dx, dy = tx - self.x, ty - self.y
            dist = math.hypot(dx, dy)
            self.v = approach(self.v, min(self.chase_v, 2.2 * dist) if dist > 0.08 else 0.0, 7.0 * DT)
            face = math.atan2(dy, dx) if dist > 0.3 else math.atan2(R.y - self.y, R.x - self.x)
            self.h = turn_toward(self.h, face, 6.0 * DT)
            step = min(self.v * DT, dist)
            self.x += step * math.cos(self.h)
            self.y += step * math.sin(self.h)
            moved = step
            near = d < 3.2               # a still, silent robot up close gives the dog nothing to chase: interest fades
            calm = R.deterrent or (sim.still_calms and R.v < 0.05)
            self.agit = clamp(self.agit + (0.42 * R.v - self.calm_base - (self.calm_deter if calm and near else 0.0))
                              * DT, 0.0, 1.0)
            if d < 4.2 and sim.t >= self.next_bark and self.agit > 0.25:
                self.bark = 1.0
                self.next_bark = sim.t + 0.38 + 0.3 * float(self.rng.random())
                sim.barks.append([sim.f, self.i])
            if self.agit <= 0.10 and R.v < 0.05:
                self.state = "RETREAT"
                sim.on_dog_retreat(self)
        elif self.state == "RETREAT":
            hx, hy, hh = self.home
            dx, dy = hx - self.x, hy - self.y
            dist = math.hypot(dx, dy)
            if dist < 0.12:
                self.state, self.calm, self.v = "REST", True, 0.0
            else:
                self.lie = approach(self.lie, 0.0, 3.0 * DT)
                self.v = approach(self.v, min(1.4, 2.0 * dist), 3.0 * DT)
                self.h = turn_toward(self.h, math.atan2(dy, dx), 4.0 * DT)
                step = min(self.v * DT, dist)
                self.x += step * math.cos(self.h)
                self.y += step * math.sin(self.h)
                moved = step
        if self.state == "REST" and self.calm:
            self.h = turn_toward(self.h, self.home[2], 1.2 * DT)
        self.bark = max(0.0, self.bark - 4.0 * DT)
        self.phase += moved / 0.62 * 2 * math.pi


class Person:
    def __init__(self, x, y, h):
        self.x, self.y, self.h = x, y, h
        self.v = 0.0
        self.phase = 0.0
        self.arm = 0.0        # 0 relaxed .. 1 reaching forward
        self.grab = 0.0       # 0 .. 1 both arms down holding something heavy
        self.phone = 0.0
        self.wave = 0.0
        self.vis = 1.0
        self.state = "WAIT"
        self.timer = 0.0
        self.wp = []

    def walk_to(self, tx, ty, speed, accel=4.0):
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-4:
            self.v = 0.0
            return 0.0
        self.v = approach(self.v, min(speed, 2.5 * dist + 0.2), accel * DT)
        self.h = turn_toward(self.h, math.atan2(dy, dx), 7.0 * DT)
        step = min(self.v * DT, dist)
        self.x += step * dx / dist
        self.y += step * dy / dist
        self.phase += step / 1.25 * 2 * math.pi
        return dist - step

    def face(self, tx, ty, rate=5.0):
        self.h = turn_toward(self.h, math.atan2(ty - self.y, tx - self.x), rate * DT)


class Thief(Person):
    def __init__(self, p=AGENT_DEFAULTS):
        super().__init__(p["thief_home"][0], p["thief_home"][1], -math.pi / 2 - 0.4)
        self.phone = 1.0
        self.trigger, self.lid_time = p["thief_trigger"], p["thief_lid"]

    def update(self, sim):
        R = sim.R
        if self.state == "WAIT":
            self.v = 0.0
            if sim.enabled("thief") and R.x > self.x - self.trigger:
                self.state = "APPROACH"
                sim.log("SENSE", "Person stepping into the path", "1 adult, 3 m ahead, walking toward the robot")
        elif self.state == "APPROACH":
            self.phone = approach(self.phone, 0.0, 3 * DT)
            tx = R.x + 1.45 * math.cos(R.h) - 0.1 * math.sin(R.h)
            ty = R.y + 1.45 * math.sin(R.h) + 0.1 * math.cos(R.h)
            if self.walk_to(tx, ty, 1.6) < 0.15:
                self.state, self.timer = "BLOCK", 0.0
        elif self.state == "BLOCK":
            self.v = 0.0
            self.face(R.x, R.y)
            if R.v < 0.03:
                self.timer += DT
                if self.timer > 0.45:
                    self.state = "SIDE"
        elif self.state == "SIDE":
            lx, ly = -math.sin(R.h), math.cos(R.h)
            if self.walk_to(R.x + 0.66 * lx + 0.03 * math.cos(R.h), R.y + 0.66 * ly + 0.03 * math.sin(R.h), 0.9) < 0.04:
                self.state, self.timer = "TRY_LID", 0.0
        elif self.state == "TRY_LID":
            self.v = 0.0
            self.face(R.x, R.y, 6.0)
            self.arm = approach(self.arm, 0.85, 3.0 * DT)
            self.timer += DT
            if not R.tamper:
                R.tamper = True
                if sim.cfg["tamper_alarm"]:
                    sim.log("SENSE", "Lid pulled by a stranger", "lid force sensor: 180 N")
                    sim.log("SAFETY", "Lid stays locked", "it opens only with the customer's OTP")
                else:
                    sim.log("SENSE", "Lid pulled", "it's locked, so he goes for the whole robot")
            if self.timer > self.lid_time:
                self.state, self.timer = "LIFT", 0.0
        elif self.state == "LIFT":
            self.arm = approach(self.arm, 0.0, 3.0 * DT)
            self.grab = approach(self.grab, 1.0, 3.0 * DT)
            self.timer += DT
            if self.timer > 0.35:
                R.lift = approach(R.lift, 0.17, 0.24 * DT)
                R.tilt = approach(R.tilt, 0.16, 0.26 * DT)
            if sim.cfg["tamper_alarm"]:
                if R.lift > 0.045 and not R.alarm:
                    sim.trigger_alarm()
                if R.alarm and sim.t - R.t_alarm > 0.45:
                    self.state, self.timer = "STARTLED", 0.0
            elif R.lift >= 0.165:
                self.state = "CARRY"
                R.carried = True
                self.wp = [(53.0, 6.9), W.ALLEY]
                sim.log("ALARM", "Robot lifted and carried away", "no tamper sensing, no alarm: nobody notices")
        elif self.state == "STARTLED":
            self.grab = approach(self.grab, 0.0, 4.0 * DT)
            self.timer += DT
            if self.timer > 0.35:
                self.state = "RUN"
                self.wp = [(53.4, 6.6), W.ALLEY]
        elif self.state in ("RUN", "CARRY"):
            speed = 4.3 if self.state == "RUN" else 1.45
            tx, ty = self.wp[0]
            if self.walk_to(tx, ty, speed, accel=8.0) < 0.2:
                self.wp.pop(0)
                if not self.wp:
                    self.state = "GONE"
                    if R.carried:
                        sim.log("ALARM", "STOLEN", "robot and food gone into a side lane")
        elif self.state == "GONE":
            self.vis = 0.0
            self.v = 0.0


class Customer(Person):
    def __init__(self):
        super().__init__(W.CUSTOMER_HOME[0], W.CUSTOMER_HOME[1], -math.pi / 2)

    def update(self, sim):
        R = sim.R
        gx, gy = W.GATE
        if self.state == "WAIT":
            if sim.enabled("customer") and math.hypot(R.x - gx, R.y - gy) < 8.5:
                self.state = "OUT"
                sim.log("INFO", "Customer notified", "app push: 'Bharat-Bot is at your gate in 20 s'")
        elif self.state == "OUT":
            if self.walk_to(gx, 6.32, 1.25) < 0.05:
                self.state = "AT_GATE"
        elif self.state == "AT_GATE":
            self.v = 0.0
            self.face(R.x, R.y)
            if R.arrived:
                self.state, self.timer = "OTP", 0.0
        elif self.state == "OTP":
            self.phone = approach(self.phone, 1.0, 3.0 * DT)
            self.timer += DT
            if self.timer > 1.3:
                self.state = "WAIT_LID"
                R.unlocked = True
                R.lid_target = 1.0
                sim.log("OK", "OTP 4819 verified", "lid unlocks for this customer only")
        elif self.state == "WAIT_LID":
            self.phone = approach(self.phone, 0.0, 3.0 * DT)
            if R.lid > 0.95:
                self.state, self.timer = "TAKE", 0.0
        elif self.state == "TAKE":
            self.timer += DT
            self.arm = 0.9 * math.sin(math.pi * clamp(self.timer / 1.4, 0, 1)) + (0.45 if self.timer > 0.7 else 0.0)
            sim.handoff = clamp(self.timer / 1.4, 0.0, 1.0)
            if self.timer > 1.4:
                self.state, self.timer = "THANK", 0.0
                R.lid_target = 0.0
        elif self.state == "THANK":
            self.timer += DT
            self.arm = approach(self.arm, 0.45, 2 * DT)
            self.wave = math.sin(clamp(self.timer / 1.2, 0, 1) * math.pi)
            if self.timer > 1.2:
                self.state = "BACK"
        elif self.state == "BACK":
            self.wave = 0.0
            self.walk_to(W.CUSTOMER_HOME[0], W.CUSTOMER_HOME[1] + 1.4, 1.1)


class Auto:
    def __init__(self, p=AGENT_DEFAULTS):
        self.active = False
        self.spawned = False
        self.x, self.y, self.h, self.v, self.spin = -60.0, 1.75, 0.0, 0.0, 0.0
        self.v_far, self.v_cow = p["auto_v"], p["auto_v_cow"]
        self.braked = 0.0        # seeded runs: most speed (m/s) the robot forced the driver to shed

    def spawn(self, x):
        self.active = self.spawned = True
        self.x, self.y, self.v = x, 1.75, self.v_far

    def update(self, sim):
        if not self.active:
            return
        if sim.eval:
            return self.drive(sim)
        cx = W.COW[0]
        self.v = approach(self.v, self.v_cow if abs(self.x - cx) < 7 else self.v_far, 3.0 * DT)
        nx = self.x + self.v * DT
        ny = 1.75 - 1.15 * math.exp(-((nx - cx) / 2.8) ** 2)
        self.h = math.atan2(ny - self.y, nx - self.x)
        self.x, self.y = nx, ny
        self.spin += self.v * DT / 0.2
        if self.x > W.X1 + 20:
            self.active = False

    def drive(self, sim):
        """Seeded runs. The film's driver follows a fixed line and would drive through a robot standing in it; this
        one keeps the same line but moves right to pass the robot with AUTO_PASS_GAP to spare (using at most 0.5 m
        of the oncoming lane) and brakes behind it when there is no room or no time to get round."""
        R, c = sim.R, sim.cfg
        cx = W.COW[0]
        v_t = self.v_cow if abs(self.x - cx) < 7 else self.v_far
        y_t = 1.75 - 1.15 * math.exp(-((self.x - cx) / 2.8) ** 2)
        if not R.carried:
            hl, hw = max(c["axles"]) + c["wheel_r"], c["half_w"]
            ch, sh = abs(math.cos(R.h)), abs(math.sin(R.h))
            ex, ey = hl * ch + hw * sh, hl * sh + hw * ch          # robot's half extent along x and y
            ahead = (R.x - ex) - (self.x + AUTO_FRONT)              # free road between the auto's nose and the robot
            if R.x + ex > self.x - AUTO_REAR and ahead < 6.0 + 2.5 * self.v:
                y_pass = R.y - ey - AUTO_HALF_W - AUTO_PASS_GAP
                if y_pass < y_t:
                    in_time = self.y - y_pass <= 1.2 * max(ahead, 0.0) / max(self.v, 0.5) + 0.05
                    if y_pass >= AUTO_Y_MIN and in_time:
                        y_t = y_pass
                    else:                                           # no room: stop 1.5 m behind the robot
                        v_stop = math.sqrt(2 * AUTO_BRAKE * max(ahead - 1.5, 0.0))
                        if v_stop < v_t:
                            self.braked = max(self.braked, min(self.v, v_t) - v_stop)
                            v_t = v_stop
        self.v = approach(self.v, v_t, ((AUTO_BRAKE + 2.0) if v_t < self.v else 3.0) * DT)
        nx = self.x + self.v * DT
        ny = approach(self.y, y_t, 1.2 * DT)
        if nx > self.x:
            self.h = math.atan2(ny - self.y, nx - self.x)
        self.x, self.y = nx, ny
        self.spin += self.v * DT / 0.2
        if self.x > W.X1 + 20:
            self.active = False


# ----------------------------------------------------------------------------------------------- simulation
class Sim:
    def __init__(self, scenario, seed=None, robot=None, cfg=None, world=None, headless=False):
        """seed=None: the film's run. seed=n: street and agents drawn for run n (identical for every robot), and the
        evaluation rules apply. robot picks "bharat" or "baseline" (default: the scenario's), cfg overrides robot
        settings (ablations), world replaces the street (a world.World), headless skips the per-frame recording and
        body pose that only the renderer needs."""
        self.name = scenario
        self.sc = SCENARIOS[scenario]
        self.seed, self.eval, self.headless = seed, seed is not None, headless
        self.robot = robot or self.sc["robot"]
        self.cfg = dict(ROBOTS[self.robot], **cfg) if cfg else ROBOTS[self.robot]
        self.still_calms = self.cfg.get("still_calms", False)   # sensitivity: any still robot calms dogs like calm mode
        self.agents, self.t_max, route, self.p = self.sc["agents"], self.sc["t_max"], None, AGENT_DEFAULTS
        Wm = W if world is None else world
        if self.eval:
            setup = EVAL_SETUP[scenario]
            route = setup.get("route")
            if world is None:
                Wm = eval_world(scenario, seed)
            self.p = sample_agents(seed, setup["thief_p"])
            if not self.p["thief"]:
                self.agents = tuple(a for a in self.agents if a != "thief")
        self.W, self.fast = Wm, Wm is not W
        c = self.cfg
        plans = getattr(Wm, "plans", None)        # a World caches plans; the module (film street) doesn't
        key = (route or self.sc["route"], self.eval, c["sees_potholes"], c["wading"], c["half_w"])
        if plans is None or key not in plans:
            path = build_route(self.sc, c, Wm, route, plan_lines=self.eval)
            if plans is None:
                plans = {}
            plans[key] = (path, {})
        self.path, profiles = plans[key]
        pkey = (c["v_cruise"], c["decel"], c["sees_potholes"], c.get("dog_map", c["sees_potholes"]))
        if pkey not in profiles:
            profiles[pkey] = speed_profile(self.path, c, Wm)
        self.vprof, self.vwhy = profiles[pkey]
        if self.eval:
            self.t_max = self.path.length / EVAL_MIN_SPEED + EVAL_SLACK
        self.R = Robot(self.cfg, self.path)
        self.dogs = [Dog(i, h, self.p) for i, h in enumerate(Wm.DOG_HOMES)]
        self.thief, self.customer, self.auto = Thief(self.p), Customer(), Auto(self.p)
        self.t, self.f = 0.0, 0
        self.events, self.barks = [], []
        self.handoff = 0.0
        self.person_block = False
        self.t_end = None
        self.flags = {}
        self.ph_state = {i: dict(detect_f=None, pass_f=None) for i in range(len(Wm.POTHOLES))}
        self.relevant = [pothole_relevant(self.path, p) for p in Wm.POTHOLES]
        m = (self.path.x > 42.0) & (self.path.x < 50.0) & (self.path.y < 1.95)
        self.s_intrude = float(self.path.s[np.argmax(m)]) if m.any() else None
        self.rec = {}
        self.done, self.outcome, self.refuse_s = False, None, None
        if self.eval:
            if not self.enabled("thief"):
                self.thief.vis = 0.0                  # no thief on this street
            if self.cfg["sees_potholes"]:
                self.refuse_s = self.flood_refusal()
            self.m = dict(t_goal=math.nan, chase_s=0.0, wade_max=0.0, holes=set(), min_dog=math.inf,
                          min_person=math.inf, min_vehicle=math.inf, theft_try=False, note="", dog_hits=0,
                          touching=set())
        self.terrain_pose()

    def enabled(self, name):
        return name in self.agents

    def log(self, level, title, detail=""):
        self.events.append(dict(f=self.f, t=round(self.t, 2), level=level, title=title, detail=detail))

    def events_t(self, title):
        return next((e["t"] for e in self.events if e["title"] == title), self.t)

    def once(self, key):
        if self.flags.get(key):
            return False
        self.flags[key] = True
        return True

    # ---------------------------------------------------------------- robot body on the terrain
    def wheel_world(self, x, y, h):
        c = self.cfg
        ax = np.array(c["axles"] * 2)
        sd = np.array([1, 1, 1, -1, -1, -1], float) * c["half_track"]
        ch, sh = math.cos(h), math.sin(h)
        return x + ax * ch - sd * sh, y + ax * sh + sd * ch, ax, sd

    def wheel_centres(self, wx, wy, h):
        r = self.cfg["wheel_r"]
        offs = np.array([-0.85, -0.55, -0.25, 0.0, 0.25, 0.55, 0.85]) * r
        sx = wx[:, None] + offs[None, :] * math.cos(h)
        sy = wy[:, None] + offs[None, :] * math.sin(h)
        hz = self.W.terrain_height(sx, sy)
        return (hz + np.sqrt(r * r - offs ** 2)[None, :]).max(axis=1)

    def terrain_pose(self):
        R, c = self.R, self.cfg
        wx, wy, ax, sd = self.wheel_world(R.x, R.y, R.h)
        zc = self.wheel_centres(wx, wy, R.h)
        if c["travel"] > 0:                       # rocker-bogie: body follows the average, wheels take the rest
            A = np.c_[np.ones(6), ax, sd]
            a, b, cc = np.linalg.lstsq(A, zc, rcond=None)[0]
            dz = np.clip(zc - (a + b * ax + cc * sd), -c["travel"], c["travel"])
            a += float(np.max(zc - (a + b * ax + cc * sd) - dz).clip(0, None))
        else:                                     # rigid chassis rests on the highest supports around its CoG
            axles = np.array(c["axles"])
            za = np.maximum(zc[:3], zc[3:])
            best = None
            for i in range(3):
                for j in range(3):
                    if axles[i] <= axles[j]:
                        continue
                    bb = (za[i] - za[j]) / (axles[i] - axles[j])
                    aa = za[i] - bb * axles[i]
                    if np.all(aa + bb * axles >= za - 1e-6) and axles[j] <= 0.0 <= axles[i]:
                        if best is None or aa < best[0]:
                            best = (aa, bb)
            a, b = best if best else (float(za.max()), 0.0)
            cc = 0.6 * (zc[:3].mean() - zc[3:].mean()) / (2 * c["half_track"])
            dz = np.zeros(6)
        R.z, R.pitch, R.roll, R.dz = float(a), math.atan(b), math.atan(cc), [float(v) for v in dz]

    def front_blocked(self):
        """True when the front wheels face a rise they cannot climb (a pothole's far wall)."""
        R, c = self.R, self.cfg
        if self.fast and not self.W.relief_near(R.x, R.y, max(c["axles"]) + c["half_track"] + c["wheel_r"] + 0.15):
            return False                          # away from holes and humps no rise comes near a robot's max step
        wx, wy, ax, sd = self.wheel_world(R.x, R.y, R.h)
        now = self.wheel_centres(wx[[0, 3]], wy[[0, 3]], R.h)
        fx, fy = math.cos(R.h) * 0.10, math.sin(R.h) * 0.10
        ahead = self.wheel_centres(wx[[0, 3]] + fx, wy[[0, 3]] + fy, R.h)
        return float(np.max(ahead - now)) > c["max_step"]

    # ---------------------------------------------------------------- events from agents
    def pack_alert(self, d):
        """Street dogs react as a pack: when one goes, they all go."""
        for dog in self.dogs:
            if dog.state == "REST":
                dog.state, dog.timer = "ALERT", 0.3 + 0.2 * dog.i
                dog.agit = 0.70 + 0.06 * dog.i
        if self.once("dogs_alert"):
            if self.cfg["dog_protocol"]:
                self.log("SENSE", "3 street dogs running at the robot", f"camera + radar: {d:.1f} m, closing at 3 m/s")
                self.log("AI", "Dogs chase things that move: freeze", "stop smoothly, no sudden moves, face lights dim")
                self.log("SAFETY", "Approved: speed 0, keep position", "wheels locked, bumper armed")
            else:
                self.log("SENSE", "Dogs chasing", "robot keeps driving at 1.6 m/s, which excites them more")

    def on_dog_retreat(self, dog):
        if self.once("dogs_retreat"):
            self.log("OK", "Dogs lost interest", "no movement to chase, they walk back to rest")

    def trigger_alarm(self):
        R = self.R
        R.alarm, R.t_alarm = True, self.t
        self.log("SENSE", "IMU: robot lifted 5 cm, tilted 6 deg", "it is not supposed to leave the ground")
        self.log("ALARM", "THEFT ALARM", "110 dB siren + red strobe")
        self.log("ACT", "Photo + live GPS sent to the ops centre", "remote operator watching, police helpline flagged")

    # ---------------------------------------------------------------- behaviour (what the robot wants to do)
    def behaviour(self):
        R, c = self.R, self.cfg
        if R.carried or R.stuck or R.arrived:
            R.hold = False
            return 0.0
        v_target = c["v_cruise"]
        # people right next to the robot or in its path
        t = self.thief
        dx, dy = t.x - R.x, t.y - R.y
        fx = dx * math.cos(R.h) + dy * math.sin(R.h)
        fy = -dx * math.sin(R.h) + dy * math.cos(R.h)
        person_block = t.vis > 0 and ((0.0 < fx < 2.5 and abs(fy) < 0.8) or math.hypot(dx, dy) < 1.25)
        self.person_block = person_block
        if person_block:
            v_target = 0.0
            if self.once("ped_stop"):
                if c["tamper_alarm"]:
                    self.log("SAFETY", "Stop: person in the path", "never push through people")
        if R.alarm:
            v_target = 0.0
            if self.t - R.t_alarm > 3.0 and (t.vis == 0 or math.hypot(dx, dy) > 7.0):
                R.alarm = False
                R.tamper = False
                self.log("OK", "Thief fled · alarm off", "incident #BLR-2481 logged with photo; resuming the delivery")
        # dogs
        if c["dog_protocol"]:
            close = [d for d in self.dogs if d.state in ("ALERT", "CHASE") and math.hypot(d.x - R.x, d.y - R.y) < 7.5]
            if close and not R.dog_stop:
                R.dog_stop, R.creep = True, False
            if R.dog_stop:
                calm = all(d.state in ("RETREAT", "REST") for d in self.dogs)
                if calm and min(math.hypot(d.x - R.x, d.y - R.y) for d in self.dogs) > 1.6:
                    R.dog_stop, R.deterrent, R.creep = False, False, True
                    self.log("AI", "Pass slowly and calmly", "1 m/s past the resting dogs")
                else:
                    v_target = 0.0
                    if R.v < 0.05 and not R.deterrent:
                        R.deterrent = True
                        self.log("ACT", "Calm mode: motors silent, lights dimmed",
                                 "nothing to chase; no ultrasonics (no evidence they work)")
            if R.creep:
                v_target = min(v_target, 1.0)
                if R.x > max(h[0] for h in self.W.DOG_HOMES) + 2.5:
                    R.creep = False
                    lost = self.t - self.events_t("3 street dogs running at the robot")
                    self.log("OK", "Back to cruise", f"dog encounter: 0 bites, 0 chases, {lost:.0f} s")
        else:
            ahead = [d for d in self.dogs if d.state == "CHASE"]
            blocked = False
            for d in ahead:
                ddx, ddy = d.x - R.x, d.y - R.y
                fx2 = ddx * math.cos(R.h) + ddy * math.sin(R.h)
                fy2 = -ddx * math.sin(R.h) + ddy * math.cos(R.h)
                if 0 < fx2 < 1.7 and abs(fy2) < 0.95:
                    blocked = True
            if blocked:
                R.retry_t += DT
                v_target = 0.0
                if R.retry_t > 1.4:                         # naive retry: lurch forward, which re-excites the dogs
                    v_target, R.go_t = 0.6, R.go_t + DT
                    if R.go_t > 0.5:
                        R.retry_t = R.go_t = 0.0
                if self.once("blocked"):
                    self.log("ALARM", "BLOCKED by 3 dogs", "stop-start retries keep them excited; delivery stalls")
            else:
                R.retry_t = R.go_t = 0.0
            ttc = c.get("obstacle_ttc")                  # generic obstacle policy (seeded runs' steel-manned robot):
            for d in self.dogs if ttc else ():           # stop for a dog close by or about to reach the robot
                if d.state in ("ALERT", "CHASE"):
                    dx, dy = d.x - R.x, d.y - R.y
                    dist = math.hypot(dx, dy) or 1e-6
                    closing = (R.v * (dx * math.cos(R.h) + dy * math.sin(R.h))
                               - d.v * (dx * math.cos(d.h) + dy * math.sin(d.h))) / dist
                    if dist < 2.0 or (closing > 0.1 and (dist - 1.0) / closing < ttc):
                        v_target = 0.0
        # traffic: passing the cow needs the lane centre, so yield to vehicles coming from behind
        R.hold = False
        if c["yields"] and self.enabled("auto") and self.s_intrude is not None and R.s < self.s_intrude:
            a = self.auto
            if a.active and R.x - 45.0 < a.x < R.x + 2.5:
                R.hold = True
                if self.once("yield"):
                    self.log("SENSE", "Cow standing in the lane ahead", "the way round it needs the lane centre")
                    self.log("SENSE", "Rear camera: auto-rickshaw behind at 25 km/h", f"{R.x - a.x:.0f} m back")
                    self.log("AI", "Yield: wait at the lane edge", "pass the cow only after the auto has gone by")
            elif self.flags.get("yield") and self.once("yield_done"):
                self.log("OK", "Gap clear: pass the cow", "0.7 m clearance, then back to the left edge")
        return v_target

    # ---------------------------------------------------------------- one tick
    def step(self):
        R, c, P = self.R, self.cfg, self.path
        v_target = self.behaviour()
        if R.carried:
            t = self.thief
            R.x = t.x + 0.42 * math.cos(t.h)
            R.y = t.y + 0.42 * math.sin(t.h)
            R.h = t.h + math.pi / 2
            R.z, R.pitch, R.roll = 0.42, 0.0, 0.12
            R.v = 0.0
            R.mode = "STOLEN"
        else:
            i = min(int(R.s / P.ds), len(P.s) - 1)
            v_cap = min(float(self.vprof[i]), v_target)
            R.why = int(self.vwhy[i]) if v_target >= float(self.vprof[i]) else 0
            if R.hold and self.s_intrude is not None:
                v_cap = min(v_cap, math.sqrt(max(0.0, 2 * c["decel"] * 0.6 * (self.s_intrude - 0.3 - R.s))))
            if self.refuse_s is not None:
                v_cap = min(v_cap, math.sqrt(max(0.0, 2 * c["decel"] * 0.6 * (self.refuse_s - R.s))))
            if R.stuck:
                v_cap = 0.0
            R.v = max(0.0, R.v + clamp(v_cap - R.v, -c["decel"] * DT, c["accel"] * DT))
            # the film only lets the robot without pothole sensing get stuck; seeded runs check every robot
            if not R.stuck and R.v > 0 and (self.eval or not c["sees_potholes"]) and self.front_blocked():
                R.stuck, R.v = True, 0.0
                self.log_stuck()
            R.s = min(R.s + R.v * DT, P.length)
            R.x, R.y, R.h = P.at(R.s)
            if not self.headless:
                self.terrain_pose()
                R.z += R.lift
                R.roll += R.tilt
                if R.stuck:
                    R.pitch += 0.012 * math.sin(self.t * 37.0)
            if not R.arrived and R.s >= P.length - 0.02 and R.v < 0.03 and self.enabled("customer"):
                R.arrived = True
                self.log("INFO", "Arrived at the gate", "waiting for the customer's OTP")
        # wheel spin (skid steer: inner wheels slower in turns; stuck wheels still spin)
        w = (R.h - self.flags.get("_h_prev", R.h)) / DT
        self.flags["_h_prev"] = R.h
        vv = 0.9 if R.stuck else (0.0 if R.carried else R.v)
        R.spin[0] += (vv - w * c["half_track"]) * DT / c["wheel_r"]
        R.spin[1] += (vv + w * c["half_track"]) * DT / c["wheel_r"]
        # lid
        R.lid = approach(R.lid, R.lid_target, 1.4 * DT)
        R.lidj = (0.05 * math.sin(self.t * 31.0) * (1.0 if self.thief.state == "TRY_LID" else 0.0))
        if R.lift > 0 and self.thief.state in ("STARTLED", "RUN", "GONE"):
            R.lift = approach(R.lift, 0.0, 1.2 * DT)
            R.tilt = approach(R.tilt, 0.0, 1.2 * DT)
        # delivered?
        if R.unlocked and self.handoff >= 1.0 and R.lid < 0.02 and not R.delivered:
            R.delivered = True
            dodged = sum(1 for s in self.ph_state.values() if s["detect_f"] is not None)
            self.log("OK", "DELIVERED", f"{P.length:.0f} m in {self.t:.0f} s · {dodged} road hazards, dogs, cow and a theft attempt handled")
            self.t_end = self.t + 2.5
        # robot mode for the HUD
        if not R.carried:
            R.mode = ("STUCK" if R.stuck else "DELIVERED" if R.delivered else "DELIVERING" if R.arrived else
                      "ALARM" if R.alarm else "TAMPER" if R.tamper else
                      "DOG FREEZE" if R.dog_stop else "YIELD" if R.hold and R.v < 0.3 else
                      "PERSON IN PATH" if self.person_block and R.v < 0.3 else
                      "BLOCKED" if v_target == 0.0 and R.v < 0.3 else "CREEP" if R.creep else
                      SPEED_REASONS[R.why] if R.why else "CRUISE")
        # pothole sensing (India-adapted robot only)
        if c["sees_potholes"]:
            self.sense_potholes()
        # agents
        if self.enabled("auto") and not self.auto.spawned and R.x >= self.p["auto_x"]:
            self.auto.spawn(R.x - self.p["auto_gap"])
        for d in self.dogs:
            d.update(self)
        self.thief.update(self)
        self.customer.update(self)
        self.auto.update(self)
        if not self.headless:
            self.record()
        if self.eval:
            self.eval_checks()
        self.t += DT
        self.f += 1

    def log_stuck(self):
        R, c = self.R, self.cfg
        wx, wy, _, _ = self.wheel_world(R.x, R.y, R.h)
        on_hump = self.eval and not any(p.depth_at(wx[[0, 3]], wy[[0, 3]]).max() > 0.005 for p in self.W.POTHOLES)
        if on_hump:
            sb = min(self.W.SPEED_BREAKERS, key=lambda sb: abs(sb.x0 - R.x))
            self.log("ALARM", "STUCK at the speed breaker", f"{sb.height * 100:.0f} cm hump; this robot climbs {c['max_step'] * 100:.0f} cm")
        else:
            p = min(self.W.POTHOLES, key=lambda p: math.hypot(p.cx - R.x, p.cy - R.y))
            self.log("ALARM", "STUCK in a pothole", f"front wheels in a {p.depth * 100:.0f} cm hole; this robot climbs {c['max_step'] * 100:.0f} cm")
        if self.eval:
            self.m["note"] = "speed breaker" if on_hump else f"{p.depth * 100:.0f} cm pothole"
        self.log("INFO", "Needs a human to rescue it", "typical recovery: 20-40 min")

    def sense_potholes(self):
        R = self.R
        for i, p in enumerate(self.W.POTHOLES):
            st = self.ph_state[i]
            if not self.relevant[i]:
                continue
            if st["detect_f"] is None and R.x + 7.0 >= p.cx - p.rx and R.x < p.cx:
                st["detect_f"] = self.f
                k = int(np.argmin(np.abs(self.path.x - p.cx)))
                side = "left" if float(self.path.y[k]) > p.cy else "right"   # which side of the hole it passes
                dist = p.cx - p.rx - R.x
                if p.water > 0 and p.depth <= 0.06:
                    self.log("SENSE", f"Waterlogged patch {p.water * 100:.1f} cm deep", f"stereo depth + sonar, {dist:.1f} m ahead")
                    self.log("AI", f"Below the {self.cfg['wading'] * 100:.0f} cm wading limit: wade through",
                             "slow to 0.65 m/s so it doesn't splash; motors are IP67")
                elif p.water > 0:
                    self.log("SENSE", f"Water-filled pothole: {p.depth * 100:.0f} cm deep under muddy water",
                             f"{2 * p.rx:.1f} m long, {dist:.1f} m ahead; can't see the bottom")
                    self.log("AI", f"Too deep to wade: pass it on the {side}", "all six wheels stay on solid, dry road")
                    if self.once("lane_ok"):
                        self.log("SAFETY", "Approved: stays in the left lane", "no vehicle behind within 30 m")
                else:
                    self.log("SENSE", f"Pothole {p.depth * 100:.0f} cm deep, {2 * max(p.rx, p.ry):.1f} m wide",
                             f"depth camera, {dist:.1f} m ahead")
                    self.log("AI", f"Re-plan: pass it on the {side}", "wheels stay on solid road · slow to 1 m/s")
            if st["detect_f"] is not None and st["pass_f"] is None and R.x > p.cx + p.rx + 1.2:
                st["pass_f"] = self.f
        if R.x > self.W.SPEED_BREAKER_X - 5.5 and self.once("sb"):
            hump = self.W.SPEED_BREAKERS[0].height if self.W.SPEED_BREAKERS else 0.0
            self.log("SENSE", f"Speed breaker: {hump * 100:.0f} cm hump", "unmarked, 5 m ahead (IRC limit is 10 cm)")
            self.log("ACT", "Slow to 0.6 m/s", "rocker-bogie keeps all 6 wheels on the ground")
        if R.x > 28.5 and self.once("hotspot"):
            self.log("INFO", "Fleet map: dog hotspot by the garbage heap", "7 dog incidents reported here; slow to 1.15 m/s")

    # ---------------------------------------------------------------- recording
    def record(self):
        R, rec = self.R, self.rec

        def put(key, val):
            rec.setdefault(key, []).append(val)

        put("t", round(self.t, 4))
        for k in ("x", "y", "z", "h", "pitch", "roll", "v", "s", "lift", "tilt", "lid", "lidj"):
            put("r_" + k, round(float(getattr(R, k)), 5))
        put("r_mode", R.mode)
        put("r_alarm", int(R.alarm))
        put("r_deter", int(R.deterrent))
        put("r_carried", int(R.carried))
        put("r_stuck", int(R.stuck))
        put("r_spin", [round(R.spin[0], 4), round(R.spin[1], 4)])
        put("r_dz", [round(v, 4) for v in R.dz])
        put("r_vis", 0 if (R.carried and self.thief.state == "GONE") else 1)
        # bag (food parcel): in the compartment, then handed to the customer
        cu = self.customer
        cx, cy, ch = R.x, R.y, R.h
        comp = np.array([cx - 0.02 * math.cos(ch), cy - 0.02 * math.sin(ch), R.z + 0.33])
        hand = np.array([cu.x + 0.36 * math.cos(cu.h), cu.y + 0.36 * math.sin(cu.h), 0.95])
        k = sstep(self.handoff)
        bag = comp + (hand - comp) * k
        bag[2] += 0.28 * math.sin(math.pi * k)
        if self.handoff >= 1.0:
            bag = np.array([cu.x + 0.3 * math.cos(cu.h), cu.y + 0.3 * math.sin(cu.h), 0.88])
        put("bag", [round(float(v), 4) for v in bag])
        for i, d in enumerate(self.dogs):
            put(f"d{i}", [round(d.x, 4), round(d.y, 4), round(d.h, 4), round(d.lie, 3), round(d.phase, 3),
                          round(d.bark, 3), round(d.v, 3), d.state])
        for name, p in (("thief", self.thief), ("cust", self.customer)):
            put(name, [round(p.x, 4), round(p.y, 4), round(p.h, 4), round(p.phase, 3), round(p.arm, 3),
                       round(p.grab, 3), round(p.phone, 3), round(p.wave, 3), round(p.v, 3), p.vis, p.state])
        a = self.auto
        put("auto", [round(a.x, 4), round(a.y, 4), round(a.h, 4), round(a.spin, 3), int(a.active)])

    # ---------------------------------------------------------------- seeded runs: evaluation rules and metrics
    def flood_refusal(self):
        """A robot that sees water won't enter water deeper than its wading limit. If its planned route can't avoid
        such water it stops 1 m short and calls an operator (a safe failure). Returns that station, or None."""
        P, c = self.path, self.cfg
        k = np.arange(0, len(P.s), 2)
        ax = np.array(c["axles"] * 2)
        sd = np.array([1, 1, 1, -1, -1, -1], float) * c["half_track"]
        ch, sh = np.cos(P.h[k])[:, None], np.sin(P.h[k])[:, None]
        wx, wy = P.x[k][:, None] + ax * ch - sd * sh, P.y[k][:, None] + ax * sh + sd * ch
        wd = self.W.water_depth(wx, wy).max(axis=1)
        if not (wd > c["wading"]).any():
            return None
        j = int(np.argmax(wd > c["wading"]))
        deep = float(wd[j:j + 40].max())
        self.refuse_note = (f"{deep * 100:.2f} cm of water across its path at x = {P.x[k[j]]:.0f} m, "
                            f"{(deep - c['wading']) * 1000:.1f} mm over its {c['wading'] * 100:.0f} cm limit")
        return max(0.0, float(P.s[k[j]]) - 1.0)

    def end(self, outcome, note=""):
        """Stop the run. A failure that happened earlier without stopping it (a contact) stays the outcome."""
        self.done = True
        if self.outcome is None:
            self.fail(outcome, note)

    def fail(self, outcome, note=""):
        if self.outcome is None:
            self.outcome = outcome
            self.m["note"] = note or self.m["note"]
            if outcome not in ("delivered", "reached"):
                self.log("ALARM", f"RUN FAILED: {outcome}", self.m["note"])

    def at_fault(self, a, g):
        """Did the moving robot run into agent a (signed clearance g), rather than a walking into it? It did if a is
        in front and the robot closes the gap at least as fast as a does."""
        R = self.R
        dx, dy = a.x - R.x, a.y - R.y
        ahead = dx * math.cos(R.h) + dy * math.sin(R.h)
        theirs = -(dx * math.cos(a.h) + dy * math.sin(a.h)) * a.v
        return g <= 0 and ahead > 0 and R.v * ahead >= theirs

    def eval_checks(self):
        """Seeded runs, every frame: the failures the film doesn't score, and the metrics. Running into a dog or a
        person fails the run but lets it continue (so chase time etc. are measured to the end); every other failure
        ends it. Clearances are footprint to footprint: to dogs and people while the robot moves (could it hit them?),
        to the auto-rickshaw at all times (is the robot in its way?)."""
        R, c, m, Wd = self.R, self.cfg, self.m, self.W
        if any(d.state == "CHASE" for d in self.dogs):
            m["chase_s"] += DT
        m["theft_try"] = m["theft_try"] or self.thief.state == "TRY_LID"
        if R.carried:
            return self.end("stolen", "carried off by the thief")
        if R.stuck:
            return self.end("stuck")
        hl, e = max(c["axles"]) + c["wheel_r"], max(c["axles"]) + c["half_track"]
        if (R.x, R.y, R.h) != m.get("pose"):      # the robot moved: what's under its wheels now?
            m["pose"], m["wd"] = (R.x, R.y, R.h), 0.0
            if Wd.near(R.x - e, R.x + e, R.y - e, R.y + e):
                wx, wy, _, _ = self.wheel_world(R.x, R.y, R.h)
                m["wd"] = float(Wd.water_depth(wx, wy).max())
                m["wade_max"] = max(m["wade_max"], m["wd"])
                for i in Wd._near(wx, wy):
                    if i not in m["holes"] and Wd.POTHOLES[i].depth_at(wx, wy).max() > 0.03:
                        m["holes"].add(i)         # a wheel went over >= 3 cm of hole (TRL's pothole threshold)
        wd = m["wd"]
        body = box(R.x, R.y, R.h, -hl, hl, c["half_w"])
        if R.v > 0.1:                             # a moving robot that runs into a dog or a person has failed
            for d in self.dogs:
                touch = False
                if abs(d.x - R.x) < 3.0 and abs(d.y - R.y) < 3.0:
                    g = gap(body, box(d.x, d.y, d.h, -DOG_HALF[0], DOG_HALF[0], DOG_HALF[1]))
                    m["min_dog"] = min(m["min_dog"], g)
                    touch = self.at_fault(d, g)
                if touch and d.i not in m["touching"]:
                    m["dog_hits"] += 1
                    self.fail("hit_dog", f"drove into a dog at {R.v:.1f} m/s")
                (m["touching"].add if touch else m["touching"].discard)(d.i)
            people = [self.customer] + ([self.thief] if self.thief.vis > 0 and
                                        self.thief.state in ("WAIT", "APPROACH", "BLOCK") else [])
            for pe in people:
                if abs(pe.x - R.x) < 3.0 and abs(pe.y - R.y) < 3.0:
                    g = gap_point(body, pe.x, pe.y, PERSON_R)
                    m["min_person"] = min(m["min_person"], g)
                    if self.at_fault(pe, g):
                        self.fail("hit_person", f"drove into a person at {R.v:.1f} m/s")
        a = self.auto
        if a.active and abs(a.x - R.x) < 5.0 and abs(a.y - R.y) < 3.0:
            m["min_vehicle"] = min(m["min_vehicle"], gap(body, box(a.x, a.y, a.h, -AUTO_REAR, AUTO_FRONT, AUTO_HALF_W)))
        if wd > c["wading"]:
            return self.end("flooded", f"wheels in {wd * 100:.2f} cm of water, {(wd - c['wading']) * 1000:.2f} mm over "
                                       f"its {c['wading'] * 100:.0f} cm rating")
        if m["min_vehicle"] <= 0:
            return self.end("hit_vehicle", "robot and auto-rickshaw footprints touched")
        if self.refuse_s is not None and R.v < 0.03 and R.s >= self.refuse_s - 0.3:
            self.log("SAFETY", "Water deeper than the wading limit across the lane", "refuse to enter, call the operator")
            return self.end("refused_flood", self.refuse_note)
        if R.arrived and math.isnan(m["t_goal"]):
            m["t_goal"] = self.t
        if R.delivered:
            return self.end("delivered")
        if not self.enabled("customer") and R.s >= self.path.length - 0.05:
            m["t_goal"] = self.t
            return self.end("reached")

    def result(self):
        """One seeded run as a flat row of numbers (nan = not applicable on this run)."""
        R, m, nan = self.R, self.m, math.nan
        pack = bool(self.flags.get("dogs_alert"))
        out = self.outcome or "timeout"
        if out == "timeout":                      # why the clock ran out
            dogs = R.dog_stop or self.flags.get("blocked") or any(d.state in ("ALERT", "CHASE") for d in self.dogs)
            m["note"] = "dogs" if dogs else "yield" if R.hold else R.mode.lower()
        return dict(
            outcome=out, success=int(out in ("delivered", "reached")), t_goal=m["t_goal"], t_end=round(self.t, 3),
            stuck=int(out == "stuck"), flooded=int(out == "flooded"), refused=int(out == "refused_flood"),
            stolen=int(out == "stolen"), theft_try=int(m["theft_try"]), pack=int(pack),
            chase_s=m["chase_s"] if pack else nan, dog_hits=m["dog_hits"] if pack else nan,
            min_dog=m["min_dog"] if m["min_dog"] < 3.0 else nan,       # nan: never within 3 m
            min_person=m["min_person"] if m["min_person"] < 3.0 else nan,
            min_vehicle=m["min_vehicle"] if m["min_vehicle"] < 3.0 else nan,
            auto_braked=self.auto.braked if self.auto.spawned else nan,
            holes=len(m["holes"]), dist=round(R.s, 2), wade_max=m["wade_max"], note=m["note"],
            holes_wet=sum(1 for i in m["holes"] if self.W.POTHOLES[i].water > 0),     # waded through on purpose?
            holes_small=sum(1 for i in m["holes"] if self.W.POTHOLES[i].water <= 0 and
                            2 * max(self.W.POTHOLES[i].rx, self.W.POTHOLES[i].ry) < 0.45),
            dog_give_up=self.p.get("dog_give_up", nan), **{"street_" + k: v for k, v in self.W.info.items()
                                                            if k in ("monsoon", "potholes", "breaker_m", "deepest_water_m")})

    def run(self):
        while True:
            self.step()
            if self.done:
                break
            if self.t_end is not None and self.t >= self.t_end:
                break
            if self.t >= self.t_max:
                break
        return self

    def to_dict(self):
        P = self.path
        k = max(1, int(0.25 / P.ds))
        return dict(
            scenario=self.name, robot=self.robot, label=self.cfg["label"], fps=FPS, frames=self.f,
            duration=round(self.t, 3), cfg=self.cfg, speed_reasons=SPEED_REASONS,
            path=dict(x=[round(float(v), 3) for v in P.x[::k]], y=[round(float(v), 3) for v in P.y[::k]],
                      length=round(P.length, 3)),
            potholes=[dict(cx=p.cx, cy=p.cy, rx=p.rx, ry=p.ry, rot=p.rot, depth=p.depth, water=p.water,
                           detect_f=self.ph_state[i]["detect_f"], pass_f=self.ph_state[i]["pass_f"])
                      for i, p in enumerate(self.W.POTHOLES)],
            obstacles=[list(o) for o in self.W.STATIC_OBSTACLES],
            events=self.events, barks=self.barks, rec=self.rec)


def run(scenario, **kw):
    return Sim(scenario, **kw).run()


def check(sim):
    """Sanity numbers printed by the CLI."""
    rec, P = sim.rec, sim.path
    xs, ys, hs = np.array(rec["r_x"]), np.array(rec["r_y"]), np.array(rec["r_h"])
    worst = 0.0
    for x, y, h in zip(xs[::3], ys[::3], hs[::3]):
        if sim.R.carried:
            break
        ox = np.array([-0.4, 0, 0.4])
        oy = np.array([-0.3, 0, 0.3])
        gx = x + ox[:, None] * math.cos(h) - oy[None, :] * math.sin(h)
        gy = y + ox[:, None] * math.sin(h) + oy[None, :] * math.cos(h)
        worst = max(worst, float(sim.W.pothole_depth(gx, gy).max()))
    modes = []
    for m in rec["r_mode"]:
        if not modes or modes[-1][0] != m:
            modes.append([m, 0])
        modes[-1][1] += 1
    return dict(frames=sim.f, seconds=round(sim.t, 1), path_m=round(P.length, 1),
                max_v=round(max(rec["r_v"]), 2), worst_pothole_under_robot_cm=round(worst * 100, 1),
                modes=[(m, round(n / FPS, 1)) for m, n in modes])


if __name__ == "__main__":
    args = sys.argv[1:]
    opts = {}
    for flag in ("--seed", "--robot"):
        if flag in args:
            i = args.index(flag)
            opts[flag[2:]] = args[i + 1]
            del args[i:i + 2]
    names = args or ["all"]
    if names == ["all"]:
        names = list(SCENARIOS)
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(out_dir, exist_ok=True)
    for name in names:
        if opts:                                  # one seeded run: print it, write nothing
            sim = run(name, seed=int(opts.get("seed", 0)), robot=opts.get("robot"))
            print(f"\n=== {name} seed {sim.seed}, {sim.cfg['label']}: street {sim.W.info}")
            print("agents:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in sim.p.items()})
            for e in sim.events:
                print(f"  {e['t']:6.2f}s  {e['level']:<6} {e['title']}  |  {e['detail']}")
            print("result:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in sim.result().items()})
            continue
        sim = run(name)
        info = check(sim)
        print(f"\n=== {name}: {info['seconds']} s, {info['frames']} frames, path {info['path_m']} m, "
              f"max v {info['max_v']}, deepest pothole under robot {info['worst_pothole_under_robot_cm']} cm")
        print("modes:", " > ".join(f"{m} {s}s" for m, s in info["modes"]))
        for e in sim.events:
            print(f"  {e['t']:6.2f}s  {e['level']:<6} {e['title']}  |  {e['detail']}")
        with open(os.path.join(out_dir, name + ".json"), "w") as fh:
            json.dump(sim.to_dict(), fh, separators=(",", ":"))
