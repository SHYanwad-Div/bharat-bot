"""Checks for seeded runs and the film's runs they must not disturb (python sim/test_seeded.py, about 30 s).

1. The film's runs are unchanged: HUD telemetry regenerated from the default runs is byte-identical to the copies the
   film uses (video/src/data/*.telemetry.json). Nothing is written there; the check uses a temporary folder.
2. world.World on the film's street gives exactly the module functions' numbers, and a headless run on it reproduces
   the film's event logs, so batch runs use the same physics as the film.
3. Seeded runs are reproducible, and every robot on a seed meets the same street and the same agents.
"""
import filecmp
import json
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import export_telemetry as E  # noqa: E402
import simulate as S  # noqa: E402
import world as W  # noqa: E402

FILM_DATA = os.path.join(os.path.dirname(HERE), "video", "src", "data")


def check(label, ok):
    print(("PASS  " if ok else "FAIL  ") + label)
    return ok


def main():
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        E.OUT = tmp
        for name in S.SCENARIOS:
            sim = S.run(name)
            path, _, _ = E.export(sim)
            ok &= check(f"{name}: telemetry identical to the film's copy",
                        filecmp.cmp(path, os.path.join(FILM_DATA, f"{name}.telemetry.json"), shallow=False))
            fast = S.run(name, world=W.World.default(), headless=True)
            ok &= check(f"{name}: headless run on World.default() logs the same events",
                        fast.events == sim.events and fast.f == sim.f)
    film = W.World.default()
    rng = np.random.default_rng(1)
    x, y = rng.uniform(-14, 84, 50000), rng.uniform(-6.5, 6.5, 50000)
    for f in ("terrain_height", "pothole_depth", "water_depth"):
        ok &= check(f"World.{f} equals world.{f} on the film's street", np.array_equal(getattr(W, f)(x, y),
                                                                                       getattr(film, f)(x, y)))
    row = lambda sim: json.dumps(sim.result(), sort_keys=True, default=str)  # noqa: E731
    a = S.Sim("bharat_full", seed=5, headless=True).run()
    b = S.Sim("bharat_full", seed=5, headless=True).run()
    ok &= check("seeded runs are reproducible", row(a) == row(b) and a.events == b.events)
    c = S.Sim("bharat_full", seed=5, robot="baseline", headless=True)
    ok &= check("every robot on a seed gets the same street and agents", c.W.info == a.W.info and c.p == a.p)
    print("all passed" if ok else "SOME CHECKS FAILED")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
