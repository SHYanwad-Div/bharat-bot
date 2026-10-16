"""Batch evaluation: Bharat-Bot vs a standard sidewalk robot over hundreds of seeded streets.

Each scenario runs N seeds (default 200) for every robot variant, with the same street and the same agents for every
robot on a given seed (a paired comparison). Seeded runs draw potholes, water, the speed breaker, the dogs, the
auto-rickshaw and the thief from research/india-delivery-robots.md section 5 (world.STREET_RANGES and
simulate.AGENT_RANGES) and apply the evaluation rules in simulate.py (EVAL_SETUP, Sim.eval_checks). An ablation runs
the full delivery again with one Bharat-Bot feature removed at a time.

    python sim/evaluate.py                      # 200 seeds on all cores, about 5 minutes on an i7-1355U
    python sim/evaluate.py --seeds 40 --workers 4

Headless (numpy only, no Blender). Writes research/evaluation.md and video/src/data/evaluation.json.
"""
import argparse
import datetime
import json
import math
import os
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simulate as S  # noqa: E402
import world as W  # noqa: E402

ROOT = os.path.dirname(HERE)
MD_PATH = os.path.join(ROOT, "research", "evaluation.md")
JSON_PATH = os.path.join(ROOT, "video", "src", "data", "evaluation.json")

# Without the rocker-bogie Bharat-Bot is a rigid chassis on the same 32 cm wheels; it then climbs what the standard
# robot climbs relative to its wheel: 6 cm on a 9 cm radius -> 10.7 cm on 16 cm.
RIGID_STEP = round(S.ROBOTS["bharat"]["wheel_r"] * S.ROBOTS["baseline"]["max_step"] / S.ROBOTS["baseline"]["wheel_r"], 3)
# The steel-manned standard robot gets the most generous section 5 values and what a Starship-class robot has (research
# section 4, item 1): it climbs 12 cm and wades 5 cm (top of the section 5 ranges), its lid is locked with a siren on
# tamper, and it stops for any dog within 2 m or less than OBSTACLE_TTC seconds from reaching it. It still can't see
# holes or water depth and has no dog-specific or traffic policy.
OBSTACLE_TTC = 1.5
STEELMAN = dict(max_step=0.12, wading=0.05, tamper_alarm=True, obstacle_ttc=OBSTACLE_TTC)

# id: (label, robot, cfg overrides)
VARIANTS = {
    "baseline": ("Standard robot (as in the film)", "baseline", {}),
    "steelman": ("Standard robot, steel-manned", "baseline", STEELMAN),
    "bharat": ("Bharat-Bot", "bharat", {}),
    "no_perception": ("without pothole & water perception", "bharat", dict(sees_potholes=False, dog_map=True)),
    "no_dog_freeze": ("without the dog freeze protocol", "bharat", dict(dog_protocol=False, obstacle_ttc=OBSTACLE_TTC)),
    "no_alarm": ("without the tamper alarm", "bharat", dict(tamper_alarm=False)),
    "no_yield": ("without traffic yield", "bharat", dict(yields=False)),
    "no_bogie": ("without rocker-bogie (rigid chassis)", "bharat", dict(travel=0.0, max_step=RIGID_STEP)),
    "no_perception_bogie": ("without perception and rocker-bogie", "bharat",
                            dict(sees_potholes=False, dog_map=True, travel=0.0, max_step=RIGID_STEP)),
    "steelman_still": ("Steel-manned, if any still robot calmed dogs", "baseline", dict(STEELMAN, still_calms=True)),
}
ROBOTS3 = ["baseline", "steelman", "bharat"]
ABLATIONS = ["no_perception", "no_dog_freeze", "no_alarm", "no_yield", "no_bogie", "no_perception_bogie"]
# (scenario, id, title, what it tests, variants)
SCENARIOS = [
    ("bharat_full", "full", "Full delivery",
     "restaurant to apartment gate (70 m): potholes, water, speed breaker, dog pack, cow + auto-rickshaw, a thief on "
     "half the streets, OTP hand-over", ROBOTS3 + ABLATIONS),
    ("baseline_pothole", "pothole", "Pothole stretch",
     "the film's 12 m pothole segment with a random broken surface, no agents", ROBOTS3),
    ("baseline_dogs", "dogs", "Dog pack",
     "16.5 m past three resting street dogs, smooth street", ROBOTS3 + ["steelman_still"]),
    ("baseline_theft", "theft", "Theft attempt",
     "13.6 m past a thief who always tries, smooth street", ROBOTS3),
]
OUTCOMES = {
    "delivered": "delivered", "reached": "reached the end", "stuck": "stuck",
    "flooded": "drove into water over its wading limit", "refused_flood": "stopped at water it can't wade or avoid",
    "stolen": "stolen", "hit_vehicle": "touched the auto-rickshaw", "hit_dog": "ran into a dog",
    "hit_person": "ran into a person", "timeout": "ran out of time",
}


# ----------------------------------------------------------------------------------------------- running
def job(task):
    """All variants of one scenario on one seed: the street is built once and shared (and so are planned routes)."""
    scen, seed, variants = task
    world = S.eval_world(scen, seed)
    rows = []
    for v in variants:
        _, robot, cfg = VARIANTS[v]
        sim = S.Sim(scen, seed=seed, robot=robot, cfg=cfg, world=world, headless=True).run()
        rows.append(dict(scenario=scen, seed=seed, variant=v, **sim.result()))
    return rows


def run_all(n_seeds, workers, first_seed=0):
    tasks = [(scen, seed, variants) for scen, _, _, _, variants in SCENARIOS
             for seed in range(first_seed, first_seed + n_seeds)]
    tasks.sort(key=lambda t: -len(t[2]))           # long tasks first keeps every worker busy to the end
    rows, t0 = [], time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, r in enumerate(ex.map(job, tasks, chunksize=1), 1):
            rows.extend(r)
            if i % max(1, len(tasks) // 10) == 0:
                print(f"  {i}/{len(tasks)} scenario-seeds done, {time.time() - t0:.0f} s", flush=True)
    return rows


# ----------------------------------------------------------------------------------------------- statistics
Z = 1.959963984540054


def t975(df):
    """97.5 % quantile of Student's t (Cornish-Fisher expansion; table below 3 degrees of freedom)."""
    if df < 3:
        return (12.706, 4.303)[df - 1] if df >= 1 else math.nan
    z, v = Z, float(df)
    return (z + (z ** 3 + z) / (4 * v) + (5 * z ** 5 + 16 * z ** 3 + 3 * z) / (96 * v ** 2)
            + (3 * z ** 7 + 19 * z ** 5 + 17 * z ** 3 - 15 * z) / (384 * v ** 3))


def wilson(k, n):
    """A rate with its 95 % Wilson score interval."""
    if n == 0:
        return dict(mean=None, lo=None, hi=None, n=0)
    p = k / n
    c = (p + Z * Z / (2 * n)) / (1 + Z * Z / n)
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / (1 + Z * Z / n)
    return dict(mean=p, lo=max(0.0, c - h), hi=min(1.0, c + h), n=n)


def mean_ci(x):
    """A mean with its 95 % Student-t interval; nan entries are runs where the metric doesn't apply."""
    x = np.asarray([v for v in x if not (isinstance(v, float) and math.isnan(v))], float)
    if len(x) == 0:
        return dict(mean=None, lo=None, hi=None, n=0)
    m = float(x.mean())
    if len(x) == 1:
        return dict(mean=m, lo=None, hi=None, n=1)
    h = t975(len(x) - 1) * float(x.std(ddof=1)) / math.sqrt(len(x))
    return dict(mean=m, lo=m - h, hi=m + h, n=len(x))


def summarise(rows):
    """Per scenario and variant: every metric as mean [95 % CI], plus outcome counts and the raw rows by seed."""
    by = {}
    for r in rows:
        by.setdefault((r["scenario"], r["variant"]), []).append(r)
    out = {}
    for key, rs in by.items():
        rs.sort(key=lambda r: r["seed"])
        n = len(rs)
        tries = [r for r in rs if r["theft_try"]]
        packs = [r for r in rs if r["pack"]]
        autos = [r for r in rs if not math.isnan(r["auto_braked"])]
        out[key] = dict(
            n=n,
            success=wilson(sum(r["success"] for r in rs), n),
            t_goal=mean_ci([r["t_goal"] for r in rs if r["success"]]),
            stuck=wilson(sum(r["stuck"] for r in rs), n),
            flooded=wilson(sum(r["flooded"] for r in rs), n),
            refused=wilson(sum(r["refused"] for r in rs), n),
            holes=mean_ci([100.0 * r["holes"] / r["dist"] for r in rs if r["dist"] > 5.0]),
            holed=wilson(sum(1 for r in rs if r["holes"]), n),
            chase_s=mean_ci([r["chase_s"] for r in rs]),
            dog_hit=wilson(sum(1 for r in packs if r["dog_hits"] > 0), len(packs)),
            theft=wilson(sum(r["stolen"] for r in tries), len(tries)),
            min_dog=mean_ci([r["min_dog"] for r in rs]),
            min_person=mean_ci([r["min_person"] for r in rs]),
            min_vehicle=mean_ci([r["min_vehicle"] for r in rs]),
            conflict=wilson(sum(1 for r in autos if r["auto_braked"] > 1.0 or r["min_vehicle"] < 0.2), len(autos)),
            outcomes={o: sum(1 for r in rs if r["outcome"] == o) for o in OUTCOMES if any(r["outcome"] == o for r in rs)},
            dog_standoffs=sum(1 for r in rs if r["outcome"] == "timeout" and r["note"] == "dogs"),
            hole_mix={k: sum(r[k] for r in rs) for k in ("holes", "holes_wet", "holes_small")},
            seeds={r["seed"]: r for r in rs},
        )
    return out


def paired(stats, scen, a, b, key="success"):
    """Mean per-seed difference a - b (same street, same agents) with a 95 % t interval."""
    sa, sb = stats[(scen, a)]["seeds"], stats[(scen, b)]["seeds"]
    d = mean_ci([float(sa[s][key] - sb[s][key]) for s in sa if s in sb])
    if d["lo"] is not None:                       # a difference of two rates can't leave [-1, 1]
        d["lo"], d["hi"] = max(-1.0, d["lo"]), min(1.0, d["hi"])
    return d


def by_street(stats, scen, var):
    """Success on dry vs just-rained-on streets."""
    rs = list(stats[(scen, var)]["seeds"].values())
    return {w: wilson(sum(r["success"] for r in rs if r["street_monsoon"] == w),
                      sum(1 for r in rs if r["street_monsoon"] == w)) for w in (False, True)}


# ----------------------------------------------------------------------------------------------- formatting
def pct(s, d=0, n=False):
    if s["mean"] is None:
        return "–"
    return f"{100 * s['mean']:.{d}f}% [{100 * s['lo']:.{d}f}–{100 * s['hi']:.{d}f}]" + (f" (n={s['n']})" if n else "")


def num(s, d=1, n=False):
    if s["mean"] is None:
        return "–"
    tail = f" (n={s['n']})" if n else ""
    if s["lo"] is None:
        return f"{s['mean']:.{d}f}{tail}"
    return f"{s['mean']:.{d}f} [{s['lo']:.{d}f}, {s['hi']:.{d}f}]{tail}"


def pts(s):
    """A paired difference of rates, in percentage points."""
    if s["mean"] is None:
        return "–"

    def f(v):
        r = round(100 * v)
        return "0" if r == 0 else f"{r:+d}".replace("-", "−")
    return f"{f(s['mean'])} pts [{f(s['lo'])}, {f(s['hi'])}]"


def share(k, n):
    p = 100 * k / n
    return "<1%" if 0 < p < 1 else f"{p:.0f}%"


def label(st, o):
    if o == "timeout" and st["dog_standoffs"] == st["outcomes"].get("timeout"):
        return "ran out of time in a stand-off with the dogs"
    return OUTCOMES[o]


def outcome_text(st, pct_=False):
    return ", ".join(f"{label(st, o)} {share(k, st['n']) if pct_ else k}"
                     for o, k in sorted(st["outcomes"].items(), key=lambda kv: -kv[1]))


def new_failure(st, ref):
    """The failure that grew most compared with the reference robot on the same streets."""
    grow = [(k - ref["outcomes"].get(o, 0), o) for o, k in st["outcomes"].items() if o not in ("delivered", "reached")]
    grow = [(g, o) for g, o in grow if g > 0]
    if not grow:
        return "none"
    g, o = max(grow)
    return f"{label(st, o)} (+{share(g, st['n'])} of runs)"


ROWS = [  # label, stat key, kind (rate / mean with digits), show n (the metric applies to some runs only)
    ("Success (delivered / reached the end)", "success", "rate", False),
    ("Time to door / end of stretch, successful runs (s)", "t_goal", 1, False),
    ("Stuck in a pothole or on the speed breaker", "stuck", "rate", False),
    ("Drove into water deeper than its wading limit", "flooded", "rate", False),
    ("Stopped at water it can't wade or avoid (safe failure)", "refused", "rate", False),
    ("Potholes driven over per 100 m (a wheel over ≥ 3 cm of hole)", "holes", 1, False),
    ("Dog-chase duration when the pack reacts (s)", "chase_s", 1, True),
    ("Ran into a dog, share of pack encounters", "dog_hit", "rate", True),
    ("Theft success, per attempt", "theft", "rate", True),
    ("Closest gap to a dog while moving, runs within 3 m (m)", "min_dog", 2, True),
    ("Closest gap to a person while moving, runs within 3 m (m)", "min_person", 2, True),
    ("Closest gap to the auto-rickshaw, runs within 3 m (m)", "min_vehicle", 2, True),
    ("Traffic conflict: auto braked > 1 m/s for it or passed < 0.2 m", "conflict", "rate", True),
]


def scenario_table(stats, scen, variants):
    head = "| Metric | " + " | ".join(VARIANTS[v][0] for v in variants) + " |"
    lines = [head, "|---|" + "---|" * len(variants)]
    for label, key, kind, show_n in ROWS:
        cells = [stats[(scen, v)][key] for v in variants]
        if key != "success" and all(c["n"] == 0 or not c["mean"] for c in cells):
            continue                              # doesn't apply here, or zero for every robot
        fmt = (lambda c: pct(c, n=show_n)) if kind == "rate" else (lambda c, d=kind: num(c, d, n=show_n))
        lines.append(f"| {label} | " + " | ".join(fmt(c) for c in cells) + " |")
    lines.append("| How the runs ended | " + " | ".join(outcome_text(stats[(scen, v)]) for v in variants) + " |")
    return "\n".join(lines)


def cpu_name():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
    except (ImportError, OSError):
        return platform.processor() or platform.machine()


# ----------------------------------------------------------------------------------------------- report
MEANING = {   # what a Bharat-Bot failure means, shown only for failures that happened
    "refused_flood": "*stopped at water it can't wade or avoid* is the intended safe refusal: water deeper than its "
                     "8 cm wading limit covers every line through the lane, so it stops 1 m short and calls an operator",
    "hit_person": "*ran into a person* is someone crossing its path inside its stopping distance (0.9 m from "
                  "1.6 m/s, braking at 1.4 m/s²); it stops for people in its path but doesn't predict where they walk",
    "hit_vehicle": "*touched the auto-rickshaw* means it was in the auto's way with no room or time for the driver to "
                   "get round",
    "hit_dog": "*ran into a dog* means a dog was in front of it while it was still moving",
    "flooded": "*drove into water over its wading limit* means its wheels went into water deeper than 8 cm",
    "stuck": "*stuck* means its front wheels met a rise taller than it can climb",
    "timeout": "*ran out of time* means it was still waiting (usually for dogs) when the time budget ran out",
    "stolen": "*stolen* means the thief carried it off",
}


def write_md(stats, n_seeds, first_seed, secs, workers):
    full = "bharat_full"
    b, bl, sm = (stats[(full, v)] for v in ("bharat", "baseline", "steelman"))
    d_bl, d_sm = paired(stats, full, "bharat", "baseline"), paired(stats, full, "bharat", "steelman")
    loss = {v: paired(stats, full, v, "bharat") for v in ABLATIONS}         # ablated minus complete: negative = worse
    ranked = sorted(ABLATIONS[:5], key=lambda v: loss[v]["mean"])
    seeds = f"{first_seed}–{first_seed + n_seeds - 1}"
    L = []
    L.append("# Bharat-Bot vs a standard sidewalk robot: batch evaluation\n")
    L.append(f"*Generated by `python sim/evaluate.py` on {datetime.date.today().isoformat()}: {n_seeds} seeded runs "
             f"(seeds {seeds}) per scenario and robot, with the same street and the same dogs, auto-rickshaw and thief "
             f"for every robot on a given seed. {sum(s['n'] for s in stats.values())} runs took {secs / 60:.1f} min on "
             f"{workers} worker processes ({cpu_name()}). Every number is a mean with its 95 % confidence interval in "
             f"brackets: Wilson intervals for rates, Student-t for means. *n* is the number of runs a metric applies "
             f"to when that isn't every run.*\n")
    L.append("This answers the research's top priority (`india-delivery-robots.md` §4, item 1): a steel-manned "
             "baseline-vs-adapted comparison over 100+ seeded episodes with confidence intervals and an ablation. The "
             "film's runs are single, fixed streets; here the street, the dogs, the auto-rickshaw and the thief are "
             "drawn at random from the ranges in §5 for every run.\n")

    # ---- summary
    L.append("## Summary\n")
    L.append(f"- **Full delivery: Bharat-Bot delivered on {pct(b['success'])} of {n_seeds} random streets.** The "
             f"standard robot from the film managed {pct(bl['success'])}; a steel-manned version with the most "
             f"generous §5 specs, a siren-locked lid and predictive obstacle stopping managed {pct(sm['success'])}. "
             f"On the same streets Bharat-Bot is {pts(d_bl)} ahead of the film's robot and {pts(d_sm)} ahead of the "
             f"steel-manned one.")
    L.append(f"- **How the standard robot fails on the full route:** {outcome_text(bl, pct_=True)} (film's robot); "
             f"{outcome_text(sm, pct_=True)} (steel-manned). It can't see holes or judge water depth, and with no "
             f"dog policy a pack either gets run into or never loses interest.")
    hz = [f"{title.lower()} {pct(stats[(scen, 'baseline')]['success'])} / {pct(stats[(scen, 'steelman')]['success'])}"
          f" / {pct(stats[(scen, 'bharat')]['success'])}" for scen, _, title, _, _ in SCENARIOS[1:]]
    L.append("- **One hazard at a time** (success for the film's robot / steel-manned / Bharat-Bot): " + "; ".join(hz) +
             ". A siren-locked lid is enough against the thief, which any robot can have; the dogs and the wet, broken "
             "road are where the India-specific design pays off.")
    ranking = "; ".join(f"{VARIANTS[v][0].replace('without ', '')} {pts(loss[v])}" for v in ranked)
    L.append(f"- **Which adaptation matters most** (change in full-delivery success when it is removed): {ranking}. "
             f"The tamper alarm's weight depends on how often a thief shows up (half the streets here); per attempt, "
             f"theft success goes from {pct(b['theft'])} with the alarm to {pct(stats[(full, 'no_alarm')]['theft'])} "
             f"without it. The rocker-bogie never decided a run here: with perception it isn't needed, and without "
             f"perception it only spares a few runs (stuck {pct(stats[(full, 'no_perception')]['stuck'])} without "
             f"perception, {pct(stats[(full, 'no_perception_bogie')]['stuck'])} without both), because §5's holes are "
             f"mostly small and shallow next to its 18 cm climb.")
    bf = []
    for scen, _, title, _, _ in SCENARIOS:
        st = stats[(scen, "bharat")]
        for o, k in sorted(st["outcomes"].items(), key=lambda kv: -kv[1]):
            if o not in ("delivered", "reached"):
                bf.append(f"{OUTCOMES[o]} on {k} of {st['n']} {title.lower()} runs")
    L.append("- **Where Bharat-Bot still fails:** " + ("; ".join(bf) if bf else "no failures in these runs") +
             f". It is also far from hole-free: a wheel went over at least 3 cm of hole on {pct(b['holed'])} of full "
             f"deliveries ({num(b['holes'])} holes per 100 m against {num(bl['holes'])} for the blind standard robot), "
             f"and its suspension, not its planner, is what makes that harmless. Details and seeds to replay are below.")
    sens = stats[("baseline_dogs", "steelman_still")]
    L.append(f"- **Biggest caveat:** the dog result rests on the film's hypothesis that a still, silent robot makes a "
             f"pack lose interest about five times faster than one that has merely stopped (§4 item 3: label it a "
             f"hypothesis). If any still robot calmed dogs that well, the steel-manned robot would get past the pack in "
             f"{pct(sens['success'])} of runs instead of {pct(stats[('baseline_dogs', 'steelman')]['success'])}. "
             f"No value here was measured on a real street.\n")

    # ---- results per scenario
    L.append("## Results by scenario\n")
    L.append("Robots: **standard robot (as in the film)**: 9 cm wheels that climb 6 cm, wades 3 cm, lid locked but no "
             "alarm, no dog or traffic policy. **Steel-manned**: the same robot with the best case of §5 (climbs 12 cm, "
             "wades 5 cm), a siren on the lid and predictive obstacle stopping for dogs. **Bharat-Bot**: the film's "
             "India-adapted robot.\n")
    for scen, _, title, about, variants in SCENARIOS:
        L.append(f"### {title}\n")
        L.append(f"{about[0].upper() + about[1:]}; {stats[(scen, 'bharat')]['n']} seeds; time budget = route at "
                 f"{S.EVAL_MIN_SPEED} m/s + {S.EVAL_SLACK:.0f} s.\n")
        L.append(scenario_table(stats, scen, [v for v in variants if v in ROBOTS3 + ["steelman_still"]]))
        if scen in ("bharat_full", "baseline_pothole"):
            ws = {v: by_street(stats, scen, v) for v in ROBOTS3}
            L.append("\n| Success by street | " + " | ".join(VARIANTS[v][0] for v in ROBOTS3) + " |")
            L.append("|---|" + "---|" * len(ROBOTS3))
            for w, name in ((False, "dry"), (True, "just after rain (potholes hold water)")):
                L.append(f"| {name} | " + " | ".join(pct(ws[v][w], n=True) for v in ROBOTS3) + " |")
        L.append("")

    # ---- ablation
    L.append("## Ablation: which adaptation matters most\n")
    L.append("The full delivery again, on the same streets with the same agents, with one Bharat-Bot feature removed. "
             "*Change* is the paired per-seed difference in success from the complete robot. Without the dog protocol "
             "it still stops for dogs the way the steel-manned robot does (predictive obstacle stopping) but has no "
             "calm mode and no slow pass; without the rocker-bogie it is a rigid chassis that climbs "
             f"{RIGID_STEP * 100:.1f} cm; without perception it plans as if the road were smooth.\n")
    L.append("| Bharat-Bot … | Success | Change | Stuck | Into deep water | Ran into a dog | Theft per attempt | "
             "Traffic conflict | What goes wrong instead |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for v in ["bharat"] + ABLATIONS:
        st = stats[(full, v)]
        L.append(f"| {'complete' if v == 'bharat' else VARIANTS[v][0]} | {pct(st['success'])} | "
                 f"{'—' if v == 'bharat' else pts(loss[v])} | " +
                 " | ".join(pct(st[c]) for c in ("stuck", "flooded", "dog_hit", "theft", "conflict")) +
                 f" | {'—' if v == 'bharat' else new_failure(st, stats[(full, 'bharat')])} |")
    ny = stats[(full, "no_yield")]
    L.append("\n*What goes wrong instead* is the failure that grew most compared with the complete robot on the same "
             f"streets. Without traffic yield the delivery rate changes by {pts(loss['no_yield'])} (the robot and "
             f"the auto touch beside the cow), but the bigger effect is on traffic: a conflict on "
             f"{pct(ny['conflict'])} of the auto's passes against {pct(b['conflict'])}.\n")

    # ---- Bharat-Bot failures
    L.append("## Where Bharat-Bot still fails\n")
    seen = set()
    for scen, _, title, _, _ in SCENARIOS:
        st = stats[(scen, "bharat")]
        fails = {}
        for s, r in st["seeds"].items():
            if not r["success"]:
                fails.setdefault(r["outcome"], []).append((s, r["note"]))
        if not fails:
            L.append(f"- **{title}:** no failures in {st['n']} runs.")
            continue
        for o, lst in sorted(fails.items(), key=lambda kv: -len(kv[1])):
            seen.add(o)
            ex = ", ".join(f"`--seed {s}`" for s, _ in lst[:3])
            L.append(f"- **{title}, {OUTCOMES[o]}:** {len(lst)} of {st['n']} runs, e.g. {lst[0][1]}. Replay with "
                     f"`python sim/simulate.py {scen} --robot bharat` and {ex}.")
    mix = b["hole_mix"]
    ph = stats[("baseline_pothole", "bharat")]["holes"], stats[("baseline_pothole", "baseline")]["holes"]
    if mix["holes"]:
        wet, small = mix["holes_wet"] / mix["holes"], mix["holes_small"] / mix["holes"]
        L.append(f"- **Holes it doesn't avoid (not a failure):** on {pct(b['holed'])} of full deliveries a wheel went "
                 f"over at least 3 cm of hole, {num(b['holes'])} per 100 m against {num(bl['holes'])} for the blind "
                 f"standard robot; on the 12 m pothole stretch it was {num(ph[0])} against {num(ph[1])}, no better. Of "
                 f"the holes it drove over on the full route, {100 * wet:.0f}% held water it waded on purpose (below its "
                 f"8 cm limit), {100 * small:.0f}% were dry holes under 45 cm long that fall between its planner's "
                 f"sample points (every 0.5 m along the road, every 0.18-0.22 m across its footprint), and "
                 f"{100 * (1 - wet - small):.0f}% were larger dry holes it clipped or couldn't steer round (the planner "
                 f"checks ±0.36 m either side but the wheels reach ±0.39 m, and the planned line is smoothed "
                 f"afterwards). The "
                 f"rocker-bogie climbs 18 cm, so none of them stopped it; a finer planning grid and a wider margin "
                 f"would keep its wheels out of most of them.")
    L.append(f"- **Traffic:** Bharat-Bot only yields to traffic before the cow; when it swerves into the lane round a "
             f"pothole it doesn't check behind, so it forced the auto-rickshaw to brake or pass close on "
             f"{pct(b['conflict'], n=True)} of the runs where the auto came by.")
    if seen:
        L.append("\nWhat these mean: " + "; ".join(MEANING[o] for o in sorted(seen) if o in MEANING) + ".\n")
    else:
        L.append("")

    # ---- what varies
    L.append("## What the runs vary\n")
    L.append("Each seeded run draws its street and agents from these ranges (min / typical / max; *typ –* = uniform). "
             "*§5* is `india-delivery-robots.md` section 5; *[E]* marks an estimate with no source.\n")
    L.append("| Parameter | min | typ | max | Source |")
    L.append("|---|---|---|---|---|")
    for table in (W.STREET_RANGES, S.AGENT_RANGES):
        for k, (lo, typ, hi, src) in table.items():
            L.append(f"| `{k}` | {lo:g} | {'–' if typ is None else f'{typ:g}'} | {hi:g} | {src} |")
    L.append(f"| wet street (potholes hold water) | | {W.P_MONSOON:g} | | [E] |")
    L.append(f"| waterlogged patch on a wet street | | {W.P_PATCH:g} | | [E] |")
    L.append("| thief turns up (full delivery) | | 0.5 | | [E] stress test; §5 puts real attempts at 0.2–3 % of "
             "deliveries |\n")
    L.append("Fixed in every run: the route, the cow, the garbage heap and parked scooter, the dogs' resting spots, the "
             "customer and the robots' own specs (except the steel-manned and ablation changes above).\n")

    # ---- rules
    L.append("## Rules of a seeded run\n")
    L.append("The film's runs only show what happens; a seeded run also scores it. Differences from the film's rules "
             "(all in `simulate.py`, none of them active without a seed):\n")
    L.append("- **Success** = the parcel handed over at the gate (full delivery) or the end of the stretch reached, "
             f"within a time budget of the route at {S.EVAL_MIN_SPEED} m/s plus {S.EVAL_SLACK:.0f} s of waiting, with "
             "no failure on the way.")
    L.append("- **Run-ending failures:** stuck (the front wheels face a rise taller than the robot can climb; the film "
             "only checked the robot without pothole sensing, now every robot is checked); a wheel in water deeper "
             "than the robot's wading limit; stopped at water it can't wade or avoid (robots that see water refuse "
             "rather than wade in); stolen; footprints touching the auto-rickshaw.")
    L.append("- **Failures that don't end the run:** running into a dog or a person, i.e. footprints touching while "
             "the robot moves, the other is in front of it and the robot closes the gap at least as fast as they do. "
             "A dog or a person walking into a robot isn't counted against it.")
    L.append("- **Every robot plans its own lane** with the film's lattice planner (the film's standard robot drives a "
             "fixed straight line); robots that can't see potholes plan as if the road were smooth.")
    L.append("- **The auto-rickshaw driver isn't blind:** the film's auto follows a fixed line (in the film run its body "
             "overlaps the waiting robot by about 0.4 m). Here the driver moves right to pass the robot with 0.35 m to "
             "spare, using at most 0.5 m of the oncoming lane, and brakes behind it when there's no room. A *traffic "
             "conflict* is the robot forcing the auto to brake by more than 1 m/s or a pass closer than 0.2 m. The "
             "auto always turns in at least its stopping-sight distance behind the robot.")
    L.append("- **Dogs** keep the film's pack model (alert as a pack, chase to fixed spots around the robot, interest "
             "fades when the robot is still and silent) with §5's notice distance, chase speed and give-up time.")
    L.append("- **Metrics:** closest gaps are footprint to footprint (dogs 0.8 × 0.3 m, people 0.5 m discs, the auto "
             "2.66 × 1.30 m), to dogs and people while the robot moves, to the auto at all times. Dog-chase duration "
             "is the time any dog is in chase mode, counted to the end of the run.\n")

    # ---- limits
    L.append("## Limits\n")
    L.append("- These are simulated streets. The ranges come from §5, but most of §5's dog, theft and pothole numbers "
             "are themselves estimates; no value was measured on a real Indian street (§4 item 2).")
    L.append("- The agents are simple and deterministic given their parameters: dogs never bite, a thief always flees "
             "a siren (so 0 % theft for alarmed robots is an upper bound on the alarm's effect), there is one dog pack, "
             "one cow, one vehicle and no crowd, and nobody reacts to the robot except the auto driver.")
    L.append("- The dog-protocol advantage leans on the calm-mode hypothesis above; the robot-vs-dog behaviour has never "
             "been tested (research §1.5).")
    L.append("- Physics is kinematic: no wheel slip, tipping, battery, heat or sensor noise. Perception is perfect for "
             "robots that have it (they see every hole and know every water depth); the standard robot sees none.")
    L.append("- Confidence intervals cover the randomness of the streets, not the uncertainty in the model.")
    with open(MD_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def tri(s, d=3, scale=1.0):
    """[mean, lo, hi] rounded, for the JSON (None when the metric doesn't apply)."""
    if s["mean"] is None:
        return None
    r = lambda v: None if v is None else round(v * scale, d)  # noqa: E731
    return [r(s["mean"]), r(s["lo"]), r(s["hi"])]


def write_json(stats, n_seeds, first_seed):
    full = "bharat_full"
    keys = [("success", "success", 3), ("timeToGoalS", "t_goal", 1), ("stuck", "stuck", 3),
            ("deepWater", "flooded", 3), ("floodRefusal", "refused", 3), ("holesPer100m", "holes", 1),
            ("dogChaseS", "chase_s", 1), ("dogContact", "dog_hit", 3), ("theftPerAttempt", "theft", 3),
            ("minGapDogM", "min_dog", 2), ("minGapPersonM", "min_person", 2), ("minGapVehicleM", "min_vehicle", 2),
            ("trafficConflict", "conflict", 3)]
    data = dict(
        version=1, generated=datetime.date.today().isoformat(), seeds=n_seeds, firstSeed=first_seed,
        ci="95% (Wilson for rates, Student t for means); values are [mean, low, high]",
        robots={v: VARIANTS[v][0] for v in ROBOTS3 + ABLATIONS + ["steelman_still"]},
        scenarios=[],
        ablation=[],
    )
    for scen, sid, title, about, variants in SCENARIOS:
        res = {}
        for v in [v for v in variants if v in ROBOTS3 + ["steelman_still"]]:
            st = stats[(scen, v)]
            res[v] = dict(n=st["n"], **{k: tri(st[s], d) for k, s, d in keys if st[s]["n"]},
                          outcomes=st["outcomes"])
            if scen in ("bharat_full", "baseline_pothole") and v in ROBOTS3:
                ws = by_street(stats, scen, v)
                res[v]["successDry"], res[v]["successWet"] = tri(ws[False]), tri(ws[True])
        data["scenarios"].append(dict(id=sid, scenario=scen, title=title, about=about, results=res,
                                      bharatVsBaselinePts=tri(paired(stats, scen, "bharat", "baseline"), 1, 100),
                                      bharatVsSteelmanPts=tri(paired(stats, scen, "bharat", "steelman"), 1, 100)))
    for v in ABLATIONS:
        st = stats[(full, v)]
        data["ablation"].append(dict(id=v, label=VARIANTS[v][0], success=tri(st["success"]),
                                     changePts=tri(paired(stats, full, v, "bharat"), 1, 100),
                                     outcomes=st["outcomes"]))
    with open(JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seeds", type=int, default=200, help="runs per scenario and robot (default 200)")
    ap.add_argument("--first-seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    a = ap.parse_args()
    t0 = time.time()
    n_var = sum(len(s[4]) for s in SCENARIOS)
    print(f"Evaluating {a.seeds} seeds x {n_var} scenario-robot combinations on {a.workers} workers")
    rows = run_all(a.seeds, a.workers, a.first_seed)
    secs = time.time() - t0
    stats = summarise(rows)
    write_md(stats, a.seeds, a.first_seed, secs, a.workers)
    write_json(stats, a.seeds, a.first_seed)
    for scen, sid, title, _, variants in SCENARIOS:
        print(f"\n{title}")
        for v in variants:
            st = stats[(scen, v)]
            print(f"  {VARIANTS[v][0]:45s} success {pct(st['success'])}")
    print(f"\n{len(rows)} runs in {secs:.0f} s. Wrote {os.path.relpath(MD_PATH, ROOT)} and {os.path.relpath(JSON_PATH, ROOT)}")
