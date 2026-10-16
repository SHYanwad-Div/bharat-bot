"""Indian street layout and terrain, shared by the simulator (simulate.py) and the Blender builder (build_scene.py).

Units are metres, Z is up. The street runs along +X. India keeps LEFT, so the robot rides near the
left edge of the carriageway (+Y side). Everything here is plain numpy so it runs inside or outside Blender.
"""
import math

import numpy as np

ROAD_HALF = 3.5          # carriageway |y| <= 3.5 m (two 3.5 m lanes)
SHOULDER = 6.2           # broken footpath / dirt shoulder out to |y| = 6.2 m
BUILD_Y = 6.6            # shop and house fronts
X0, X1 = -14.0, 84.0     # modelled length of the street

# Key places along the route (x, y[, heading])
START = (-1.6, 5.15, 0.0)          # robot leaves the restaurant counter, facing +x
GATE = (64.5, 5.45)                # robot stops here facing the apartment gate (+y)
SPEED_BREAKER_X = 24.0
DOG_HOMES = [(36.1, 5.55, -2.2), (37.3, 5.75, -1.1), (38.5, 5.35, 2.7)]   # resting by the garbage heap
COW = (47.1, 2.65, math.pi)        # standing in the robot's lane, facing oncoming
THIEF_HOME = (56.9, 5.3)
ALLEY = (52.5, 9.6)                # gap between buildings where the thief runs off
CUSTOMER_HOME = (64.5, 8.6)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _hash2(ix, iy, seed):
    h = (ix * 374761393 + iy * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def vnoise(x, y, scale, seed=0):
    """Smooth value noise in [0, 1]."""
    x = np.asarray(x, float) / scale
    y = np.asarray(y, float) / scale
    ix = np.floor(x).astype(np.int64)
    iy = np.floor(y).astype(np.int64)
    fx, fy = x - ix, y - iy
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = _hash2(ix, iy, seed), _hash2(ix + 1, iy, seed)
    c, d = _hash2(ix, iy + 1, seed), _hash2(ix + 1, iy + 1, seed)
    return (a + (b - a) * sx) * (1 - sy) + (c + (d - c) * sx) * sy


class Pothole:
    """Irregular bowl with steep broken walls. `water` = depth of muddy water standing in it."""

    def __init__(self, cx, cy, rx, ry, depth, rot=0.0, water=0.0, seed=0):
        self.cx, self.cy, self.rx, self.ry = cx, cy, rx, ry
        self.depth, self.rot, self.water = depth, rot, water
        rng = np.random.default_rng(seed + 11)
        self.ph = rng.uniform(0, 2 * math.pi, 3)
        self.reach = max(rx, ry) * 1.45

    def wobble(self, th):
        return 1.0 + 0.16 * np.sin(3 * th + self.ph[0]) + 0.08 * np.sin(5 * th + self.ph[1]) + 0.04 * np.sin(9 * th + self.ph[2])

    def depth_at(self, x, y):
        xb, yb = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        out = np.zeros(xb.shape)
        m = (np.abs(xb - self.cx) < self.reach) & (np.abs(yb - self.cy) < self.reach)
        if not m.any():
            return out
        dx, dy = xb[m] - self.cx, yb[m] - self.cy
        c, s = math.cos(self.rot), math.sin(self.rot)
        u, v = (dx * c + dy * s) / self.rx, (-dx * s + dy * c) / self.ry
        rn = np.hypot(u, v) / self.wobble(np.arctan2(v, u))
        wall = 1.0 - smoothstep(0.78, 1.0, rn)
        floor = 0.88 + 0.12 * np.clip(1.0 - rn * rn, 0.0, 1.0)
        lip = 0.010 * np.exp(-((rn - 1.08) / 0.07) ** 2)          # broken asphalt lip around the rim
        out[m] = self.depth * wall * floor - lip
        return out

    def rim_radius(self, th):
        """Distance from the centre to the rim along world angle th (for markers and water outlines)."""
        a = th - self.rot
        u, v = math.cos(a) / self.rx, math.sin(a) / self.ry
        return float(self.wobble(math.atan2(v, u))) / math.hypot(u, v)


class SpeedBreaker:
    def __init__(self, x0, width=1.0, height=0.12):
        self.x0, self.width, self.height = x0, width, height

    def height_at(self, x, y):
        d = np.abs(np.asarray(x, float) - self.x0)
        prof = np.where(d < self.width / 2, np.cos(np.pi * d / self.width) ** 2, 0.0)
        taper = 1.0 - smoothstep(ROAD_HALF - 0.4, ROAD_HALF - 0.05, np.abs(np.asarray(y, float)))
        return self.height * prof * taper


POTHOLES = [
    # the robot's lane: forces a slalom
    Pothole(8.0, 2.95, 0.75, 0.55, 0.11, 0.30, 0.0, 1),
    Pothole(11.6, 1.60, 0.95, 0.68, 0.13, -0.40, 0.05, 2),
    Pothole(15.0, 2.85, 0.60, 0.50, 0.09, 0.80, 0.0, 3),
    Pothole(19.2, 2.20, 1.35, 0.80, 0.14, 0.15, 0.10, 4),     # deep muddy crater: 10 cm of water, too deep to wade
    Pothole(28.6, 2.00, 1.40, 2.00, 0.045, 0.0, 0.035, 5),    # shallow waterlogging across the lane: wade slowly
    Pothole(44.0, 2.90, 0.42, 0.36, 0.06, 0.0, 0.0, 13),
    # the rest of the road (scenery, and the auto-rickshaw's problem)
    Pothole(6.0, -1.2, 0.60, 0.45, 0.08, 0.50, 0.0, 6),
    Pothole(10.0, -2.4, 0.80, 0.50, 0.10, 1.10, 0.04, 7),
    Pothole(14.0, 0.2, 0.45, 0.40, 0.07, 0.0, 0.0, 8),
    Pothole(17.5, -1.6, 1.00, 0.60, 0.11, -0.30, 0.05, 9),
    Pothole(22.0, -0.4, 0.50, 0.40, 0.08, 0.60, 0.0, 10),
    Pothole(33.0, -2.0, 0.70, 0.50, 0.09, 0.20, 0.0, 11),
    Pothole(41.0, 0.6, 0.55, 0.45, 0.08, 0.90, 0.0, 12),
    Pothole(52.0, -1.0, 0.80, 0.55, 0.10, 0.40, 0.05, 14),
    Pothole(60.0, 1.2, 0.50, 0.40, 0.07, 0.10, 0.0, 15),
    Pothole(70.0, -2.2, 0.70, 0.50, 0.09, 0.70, 0.0, 16),
]
SPEED_BREAKERS = [SpeedBreaker(SPEED_BREAKER_X)]

# Things that stand on the ground, as capsules (kind, x0, y0, x1, y1, radius)
STATIC_OBSTACLES = [
    ("garbage", 36.4, 4.55, 37.8, 4.35, 0.85),
    ("cow", 46.1, 2.65, 48.2, 2.65, 0.42),
    ("scooter", 55.2, 4.35, 56.6, 4.35, 0.40),
]


def pothole_depth(x, y):
    xb, yb = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    d = np.zeros(xb.shape)
    for p in POTHOLES:
        d = np.maximum(d, p.depth_at(xb, yb))
    return d


def road_mask(x, y):
    """1 on asphalt, 0 on the dirt shoulder, with a ragged broken edge."""
    ay = np.abs(np.asarray(y, float))
    edge = ROAD_HALF + 0.05 + 0.22 * (vnoise(x, y, 0.45, 5) - 0.5) + 0.12 * (vnoise(x, y, 1.7, 6) - 0.5)
    return 1.0 - smoothstep(edge - 0.03, edge + 0.03, ay)


def terrain_height(x, y):
    xb, yb = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    ay = np.abs(yb)
    road = 0.025 * (1.0 - np.clip(ay / ROAD_HALF, 0, 1) ** 2) + 0.004 * (vnoise(xb, yb, 0.6, 3) - 0.5)
    t = np.clip((ay - ROAD_HALF) / 1.3, 0, 1)
    dirt = (-0.035 + 0.085 * t + 0.025 * (vnoise(xb, yb, 0.5, 7) - 0.5) + 0.04 * (vnoise(xb, yb, 2.2, 9) - 0.5))
    m = road_mask(xb, yb)
    z = road * m + dirt * (1 - m)
    for p in POTHOLES:
        z = z - p.depth_at(xb, yb)
    for sb in SPEED_BREAKERS:
        z = z + sb.height_at(xb, yb)
    return z


def water_level(p):
    """Absolute z of the water surface standing in pothole p (None if dry)."""
    if p.water <= 0:
        return None
    return float(terrain_height(p.cx, p.cy)) + p.water


def water_depth(x, y):
    """Depth of standing water at (x, y), 0 where dry."""
    xb, yb = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    out = np.zeros(xb.shape)
    z = None
    for p in POTHOLES:
        if p.water <= 0:
            continue
        m = (np.abs(xb - p.cx) < p.reach) & (np.abs(yb - p.cy) < p.reach)
        if not m.any():
            continue
        if z is None:
            z = terrain_height(xb, yb)
        out = np.where(m, np.maximum(out, water_level(p) - z), out)
    return np.clip(out, 0, None)


def capsule_distance(px, py, x0, y0, x1, y1):
    px, py = np.asarray(px, float), np.asarray(py, float)
    vx, vy = x1 - x0, y1 - y0
    t = np.clip(((px - x0) * vx + (py - y0) * vy) / (vx * vx + vy * vy + 1e-12), 0, 1)
    return np.hypot(px - (x0 + t * vx), py - (y0 + t * vy))


# ----------------------------------------------------------------------------------------------- seeded streets
# Ranges for randomised streets: (min, typ, max, source). "§5" = research/india-delivery-robots.md section 5,
# [E] = estimate. typ=None means uniform between min and max, otherwise triangular with its peak at typ.
STREET_RANGES = {
    "pothole_depth_m": (0.03, 0.06, 0.15, "§5 terrain.pothole_depth_m"),
    "pothole_diameter_m": (0.10, 0.40, 1.00, "§5 terrain.pothole_diameter_m"),
    "pothole_spacing_m": (5.0, 8.0, 15.0, "§5 terrain.pothole_spacing_broken_road_m"),
    "pothole_aspect": (0.6, None, 1.0, "[E] short / long axis"),
    "pothole_centre_y_m": (0.6, None, 3.1, "[E] anywhere across the robot's lane"),
    "speed_breaker_height_m": (0.08, 0.12, 0.20, "§5 terrain.speed_breaker_height_m"),
    "wet_pothole_fraction": (0.5, None, 1.0, "§5 terrain.pothole_hidden_in_flooded_patch_fraction"),
    "puddle_depth_m": (0.03, 0.08, 0.10, "§5 water.puddle_depth_m (water in potholes and patches)"),
    "patch_length_m": (2.0, None, 3.6, "[E] waterlogged patch, along the road"),
    "patch_width_m": (2.0, None, 4.0, "[E] waterlogged patch, across the road"),
}
P_MONSOON = 0.5          # [E] share of streets seen just after rain, when potholes hold water
P_PATCH = 0.7            # [E] chance that a wet street also has one waterlogged patch across the lane
_ASPHALT = ROAD_HALF - 0.16   # nearer the centre line than this, road_mask() is exactly 1 (its edge is >= 3.38 m)


def draw(rng, key, table=STREET_RANGES):
    lo, typ, hi = table[key][:3]
    return float(rng.uniform(lo, hi) if typ is None else rng.triangular(lo, typ, hi))


class World:
    """One street for the simulator: potholes (some holding water), speed breakers and static obstacles.

    The module-level POTHOLES and functions above are the film's street (and what the Blender builder uses). A World
    answers the same queries for its own features with the same arithmetic, but skips every pothole whose reach box
    misses the query points, which makes the small per-frame queries of a batch run much cheaper. World.default() is
    the film's street (sim/test_seeded.py checks that both give identical numbers); World.random(seed) draws a street
    from STREET_RANGES."""

    START, GATE, SPEED_BREAKER_X = START, GATE, SPEED_BREAKER_X
    DOG_HOMES, COW, THIEF_HOME, ALLEY, CUSTOMER_HOME = DOG_HOMES, COW, THIEF_HOME, ALLEY, CUSTOMER_HOME
    X0, X1 = X0, X1
    capsule_distance = staticmethod(capsule_distance)

    def __init__(self, potholes, speed_breakers=None, obstacles=None, info=None):
        self.POTHOLES = list(potholes)
        self.SPEED_BREAKERS = list(SPEED_BREAKERS if speed_breakers is None else speed_breakers)
        self.STATIC_OBSTACLES = list(STATIC_OBSTACLES if obstacles is None else obstacles)
        self.info = info or {}
        e = 1e-6                                  # padding, so float rounding can never drop a pothole that matters
        self._boxes = [(p.cx - p.reach - e, p.cx + p.reach + e, p.cy - p.reach - e, p.cy + p.reach + e)
                       for p in self.POTHOLES]
        self._box = np.array(self._boxes, float).reshape(-1, 4)
        self._level = {}
        self.plans = {}                           # routes planned on this street, shared by robots that plan alike

    @classmethod
    def default(cls):
        return cls(POTHOLES, SPEED_BREAKERS, STATIC_OBSTACLES, info=dict(street="film"))

    @classmethod
    def random(cls, seed, x_range=(5.0, 59.0), potholes=True):
        """A street drawn from STREET_RANGES: potholes every 5-15 m across the robot's lane within x_range and, on a
        wet street, water in most of them plus maybe one waterlogged patch. potholes=False keeps only the (random)
        speed breaker, for scenarios that test one hazard at a time."""
        rng = np.random.default_rng([seed, 1])
        sb = SpeedBreaker(SPEED_BREAKER_X, height=draw(rng, "speed_breaker_height_m"))
        monsoon = bool(rng.random() < P_MONSOON)
        wet_frac = draw(rng, "wet_pothole_fraction")
        want_patch = bool(rng.random() < P_PATCH)
        xa, xb = x_range
        holes, patch = [], None
        if monsoon and want_patch:
            w = draw(rng, "puddle_depth_m")
            rx, ry = draw(rng, "patch_length_m") / 2, draw(rng, "patch_width_m") / 2
            cx, cy = float(rng.uniform(xa + 1.0, xb - 1.0)), float(rng.uniform(1.2, 2.6))
            patch = Pothole(cx, cy, rx, ry, w + float(rng.uniform(0.005, 0.015)), float(rng.uniform(-0.3, 0.3)), w,
                            int(rng.integers(1 << 30)))
            if abs(cx - sb.x0) > patch.reach + sb.width:
                holes.append(patch)
            else:
                patch = None
        x = xa + float(rng.uniform(0.0, 8.0))
        while x <= xb:
            d, asp = draw(rng, "pothole_diameter_m"), draw(rng, "pothole_aspect")
            depth, cy = draw(rng, "pothole_depth_m"), draw(rng, "pothole_centre_y_m")
            rot, wet, w = float(rng.uniform(0, math.pi)), bool(rng.random() < wet_frac), draw(rng, "puddle_depth_m")
            p = Pothole(x, cy, d / 2, d / 2 * asp, depth, rot, 0.0, int(rng.integers(1 << 30)))
            if monsoon and wet and min(w, depth - 0.005) >= 0.01:
                p.water = min(w, depth - 0.005)          # the water stays inside the bowl
            if abs(x - sb.x0) > p.reach + sb.width and all(
                    abs(x - q.cx) > p.reach + q.reach + 0.2 or abs(cy - q.cy) > p.reach + q.reach + 0.2 for q in holes):
                holes.append(p)
            x += draw(rng, "pothole_spacing_m")
        if not potholes:
            holes, patch = [], None
        holes.sort(key=lambda p: p.cx)
        info = dict(street="random", seed=seed, monsoon=monsoon, potholes=len(holes) - (patch is not None),
                    wet_potholes=sum(1 for p in holes if p.water > 0 and p is not patch),
                    patch_water_m=round(patch.water, 3) if patch else 0.0, breaker_m=round(sb.height, 3),
                    deepest_pothole_m=round(max([p.depth for p in holes if p is not patch] + [0.0]), 3),
                    deepest_water_m=round(max([p.water for p in holes] + [0.0]), 3))
        return cls(holes, [sb], STATIC_OBSTACLES, info)

    def near(self, x0, x1, y0, y1):
        """Indices (in list order) of the potholes whose reach box overlaps the rectangle [x0, x1] x [y0, y1]."""
        return [i for i, (a, b, c, d) in enumerate(self._boxes) if b > x0 and a < x1 and d > y0 and c < y1]

    def _near(self, xb, yb, pad=0.0):
        """Indices (in list order) of the potholes whose reach box can touch the query points."""
        if not self._boxes or xb.size == 0:
            return ()
        if xb.size <= 64:                         # per-frame queries: plain floats are quicker than numpy here
            xs, ys = xb.ravel().tolist(), yb.ravel().tolist()
            return self.near(min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad)
        b = self._box
        return np.flatnonzero((b[:, 1] > xb.min() - pad) & (b[:, 0] < xb.max() + pad) &
                              (b[:, 3] > yb.min() - pad) & (b[:, 2] < yb.max() + pad))

    def relief_near(self, x, y, r):
        """Is a pothole or speed breaker within r of the point (x, y)? Everywhere else the ground is gentle."""
        return bool(self.near(x - r, x + r, y - r, y + r)) or any(
            abs(sb.x0 - x) < sb.width / 2 + r for sb in self.SPEED_BREAKERS)

    def pothole_depth(self, x, y):
        xb, yb = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        d = np.zeros(xb.shape)
        for i in self._near(xb, yb):
            d = np.maximum(d, self.POTHOLES[i].depth_at(xb, yb))
        return d

    def terrain_height(self, x, y):
        xb, yb = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        ay = np.abs(yb)
        road = 0.025 * (1.0 - np.clip(ay / ROAD_HALF, 0, 1) ** 2) + 0.004 * (vnoise(xb, yb, 0.6, 3) - 0.5)
        off = ay >= _ASPHALT
        if off.any():                         # near the road edge: terrain_height()'s road/dirt blend on those points
            xe, ye = xb[off], yb[off]
            t = np.clip((ay[off] - ROAD_HALF) / 1.3, 0, 1)
            dirt = (-0.035 + 0.085 * t + 0.025 * (vnoise(xe, ye, 0.5, 7) - 0.5) + 0.04 * (vnoise(xe, ye, 2.2, 9) - 0.5))
            m = road_mask(xe, ye)
            z = np.array(road, float)
            z[off] = road[off] * m + dirt * (1 - m)
        else:
            z = road
        for i in self._near(xb, yb):
            z = z - self.POTHOLES[i].depth_at(xb, yb)
        for sb in self.SPEED_BREAKERS:
            z = z + sb.height_at(xb, yb)
        return z

    def water_level(self, p):
        if p.water <= 0:
            return None
        if id(p) not in self._level:
            self._level[id(p)] = float(self.terrain_height(p.cx, p.cy)) + p.water
        return self._level[id(p)]

    def water_depth(self, x, y):
        xb, yb = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        out = np.zeros(xb.shape)
        z = None
        for i in self._near(xb, yb):
            p = self.POTHOLES[i]
            if p.water <= 0:
                continue
            m = (np.abs(xb - p.cx) < p.reach) & (np.abs(yb - p.cy) < p.reach)
            if not m.any():
                continue
            if z is None:
                z = self.terrain_height(xb, yb)
            out = np.where(m, np.maximum(out, self.water_level(p) - z), out)
        return np.clip(out, 0, None)
