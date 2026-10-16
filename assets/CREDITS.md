# Asset credits & licences

## What the published work uses

Checked 2026-10-16 against the code that loads assets (`sim/environment.py`, `sim/bpy_utils.py`, `sim/characters.py`) and the licence on each asset's own page. The Blender scenes, the videos and the project page use only these eight downloaded assets, all **CC0 1.0** (public domain). No attribution is required, but the artists deserve it:

| Asset | Author | Licence | Used for | Page |
|---|---|---|---|---|
| Asphalt 02 (texture) | Rob Tuytel | CC0 1.0 | the road | <https://polyhaven.com/a/asphalt_02> |
| Road Damaged 2 (texture) | Dimitrios Savva | CC0 1.0 | dust and patches on the road | <https://polyhaven.com/a/road_damaged_2> |
| Red Laterite Soil Stones (texture) | Amal Kumar | CC0 1.0 | dirt shoulders | <https://polyhaven.com/a/red_laterite_soil_stones> |
| Red Dirt Mud 01 (texture) | Rob Tuytel | CC0 1.0 | mud in the potholes | <https://polyhaven.com/a/red_dirt_mud_01> |
| Painted Plaster Wall (texture) | Amal Kumar | CC0 1.0 | building walls | <https://polyhaven.com/a/painted_plaster_wall> |
| Husky (animated model) | Quaternius | CC0 1.0 | one street dog | <https://poly.pizza/m/wcWiuEqwzq> |
| Shiba Inu (animated model) | Quaternius | CC0 1.0 | two street dogs | <https://poly.pizza/m/y4wdQpg767> |
| Cow (animated model) | Quaternius | CC0 1.0 | the cow in the lane | <https://poly.pizza/m/26zM1outCr> |

Everything else on screen is procedural (`sim/characters.py`, `sim/environment.py`): both robots, the people, the auto-rickshaw, the shops, poles and wires. Lettering inside the Blender scenes uses Windows system fonts (Impact, Bahnschrift, Nirmala UI, Segoe UI), which are not redistributed here; the film's fonts are Rajdhani and JetBrains Mono (SIL Open Font License, via Google Fonts). The music and sound effects are synthesised by `video/scripts/make_audio.py`. Made with Blender 5.2, Remotion 4 (free licence for individuals: [LICENSE.md](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)) and Claude Code.

None of the downloaded files are in the git repository (see `.gitignore`); the sections below say where to get each one again. Licence texts: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) · [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).

## Everything that was downloaded

Downloaded 2026-10-14/15 for the street simulation. Every file below is **CC0 1.0** (public domain, no attribution needed) except five **CC BY 3.0** models, which need credit wherever they appear. None of the five is in any scene or video, so no credit line is needed today. If you add one, credit it like this:

> 3D models: Vespa by Jasmine Roberts, Motorcycle / Bicycle / Bus by jeremy, Street Vendor Cart by Alan Zimmerman (CC BY 3.0, via poly.pizza). Free assets from Quaternius, Kay Lousberg and Poly Haven (CC0).

Nothing else was kept: anything that was not CC0 or CC BY was skipped, and no executables were downloaded.

## Where the files came from

| Source | What | How it was fetched | Licence statement checked |
|---|---|---|---|
| [Poly Haven](https://polyhaven.com) | HDRIs, PBR textures, props (`assets/polyhaven/`) | public API `api.polyhaven.com/files/<id>`, every file md5-verified against the API | [polyhaven.com/license](https://polyhaven.com/license): "Our assets are all licensed as CC0"; API use falls under their API Terms (identified User-Agent, a few dozen small requests) |
| [poly.pizza](https://poly.pizza) | GLB mirror of Quaternius / Kay Lousberg (CC0) and a few CC BY models (`assets/polypizza/`) | each model page was read first (`Licence`, `Creator`, `Animated` come from the page's embedded JSON) and only `CC0 1.0` / `CC-BY 3.0` models were downloaded from `static.poly.pizza`; SHA-256 per file in `assets/polypizza/manifest.json` | per-model licence on its page; Quaternius' own site ([quaternius.com/faq.html](https://quaternius.com/faq.html)): "All models are under the CC0 License", credit appreciated |
| [Blender Foundation / blender.org](https://docs.blender.org/api/current/) | API docs and release notes used for `research/blender.md` | read-only | - |
| [ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender) | Blender MCP add-on (`assets/tools/blender_mcp.py`) | pinned commit, SHA-256 in `assets/tools/README.md` | MIT |

## Poly Haven (CC0)

Author names are from the Poly Haven API. Attribution is not required but the artists deserve it: **Amal Kumar** shot the laterite soil, blue plaster, painted plaster, damaged plaster and checkered pavement tiles.

### HDRIs (`assets/polyhaven/hdri/`)

| File | Title | Author | Page |
|---|---|---|---|
| `hdri/wide_street_01_2k.hdr` | Wide Street 01 | Sergej Majboroda | <https://polyhaven.com/a/wide_street_01> |
| `hdri/kloofendal_43d_clear_puresky_2k.hdr` | Kloofendal 43d Clear (Pure Sky) | Greg Zaal | <https://polyhaven.com/a/kloofendal_43d_clear_puresky> |

### Textures (`assets/polyhaven/textures/<id>/`, JPG maps: `_diff`, `_nor_gl`, `_rough`, plus `_disp` for the road/soil sets)

| Folder | Title | Author | Res | Page |
|---|---|---|---|---|
| `road_damaged_2/` | Road Damaged 2 | Dimitrios Savva | 2K | <https://polyhaven.com/a/road_damaged_2> |
| `road_damaged/` | Road Damaged | Dimitrios Savva | 1K | <https://polyhaven.com/a/road_damaged> |
| `asphalt_02/` | Asphalt 02 | Rob Tuytel | 1K | <https://polyhaven.com/a/asphalt_02> |
| `red_laterite_soil_stones/` | Red Laterite Soil Stones | Amal Kumar | 1K | <https://polyhaven.com/a/red_laterite_soil_stones> |
| `red_dirt_mud_01/` | Red Dirt Mud 01 | Rob Tuytel | 1K | <https://polyhaven.com/a/red_dirt_mud_01> |
| `concrete_pavement_02/` | Concrete Pavement 02 | Charlotte Baglioni | 1K | <https://polyhaven.com/a/concrete_pavement_02> |
| `checkered_pavement_tiles/` | Checkered Pavement Tiles | Amal Kumar | 1K | <https://polyhaven.com/a/checkered_pavement_tiles> |
| `painted_plaster_wall/` | Painted Plaster Wall | Amal Kumar | 1K | <https://polyhaven.com/a/painted_plaster_wall> |
| `blue_plaster_weathered/` | Blue Plaster Weathered | Amal Kumar | 1K | <https://polyhaven.com/a/blue_plaster_weathered> |
| `red_brick/` | Red Brick | Rob Tuytel | 1K | <https://polyhaven.com/a/red_brick> |
| `damaged_plaster/` | Damaged Plaster | Amal Kumar | 1K | <https://polyhaven.com/a/damaged_plaster> |

### Models (`assets/polyhaven/models/<id>/`, glTF + textures, 1K)

| Folder | Title | Author | Page |
|---|---|---|---|
| `modular_electricity_poles/` | Modular Electricity Poles | James Ray Cock | <https://polyhaven.com/a/modular_electricity_poles> |
| `metal_trash_can/` | Metal Trash Can | GurJas Studios | <https://polyhaven.com/a/metal_trash_can> |
| `trashbag/` | Trashbag | Benny Weimer | <https://polyhaven.com/a/trashbag> |
| `utility_box_02/` | Utility Box 02 | James Ray Cock | <https://polyhaven.com/a/utility_box_02> |
| `water_manhole_cover/` | Water Manhole Cover | Raunox | <https://polyhaven.com/a/water_manhole_cover> |
| `old_tyre/` | Old Tyre | MP | <https://polyhaven.com/a/old_tyre> |
| `plastic_crate_01/` | Plastic Crate 01 | PierreB3D | <https://polyhaven.com/a/plastic_crate_01> |

## poly.pizza models (`assets/polypizza/`)

Original authors are listed (Quaternius' packs are at <https://quaternius.com>, Kay Lousberg at <https://poly.pizza/u/Kay%20Lousberg>). **Bold licence = attribution required.**

| File | Title | Author | Licence | Page |
|---|---|---|---|---|
| `animals/quaternius_bull.glb` | Bull | Quaternius | CC0 1.0 | <https://poly.pizza/m/a8PIIYwF7r> |
| `animals/quaternius_cow.glb` | Cow | Quaternius | CC0 1.0 | <https://poly.pizza/m/26zM1outCr> |
| `animals/quaternius_donkey.glb` | Donkey | Quaternius | CC0 1.0 | <https://poly.pizza/m/qmX6nhnvp7> |
| `animals/quaternius_horse.glb` | Horse | Quaternius | CC0 1.0 | <https://poly.pizza/m/qvTrSG9pZF> |
| `animals/quaternius_husky.glb` | Husky | Quaternius | CC0 1.0 | <https://poly.pizza/m/wcWiuEqwzq> |
| `animals/quaternius_shiba_inu.glb` | Shiba Inu | Quaternius | CC0 1.0 | <https://poly.pizza/m/y4wdQpg767> |
| `humans/quaternius_animated_woman.glb` | Animated Woman | Quaternius | CC0 1.0 | <https://poly.pizza/m/qJ2gsTUBHL> |
| `humans/quaternius_casual_character.glb` | Casual Character | Quaternius | CC0 1.0 | <https://poly.pizza/m/kZ3DmIoGip> |
| `humans/quaternius_man.glb` | Man | Quaternius | CC0 1.0 | <https://poly.pizza/m/HMnuH5geEG> |
| `humans/quaternius_woman_casual.glb` | Woman Casual | Quaternius | CC0 1.0 | <https://poly.pizza/m/jpKRgGDxhk> |
| `humans/quaternius_woman_in_dress.glb` | Woman in Dress | Quaternius | CC0 1.0 | <https://poly.pizza/m/zMyPlQXBzq> |
| `humans/quaternius_worker.glb` | Worker | Quaternius | CC0 1.0 | <https://poly.pizza/m/Yg2bQZO6Hj> |
| `props/quaternius_barrier_large.glb` | Barrier Large | Quaternius | CC0 1.0 | <https://poly.pizza/m/gLbBiYwt7l> |
| `props/quaternius_bench.glb` | Bench | Quaternius | CC0 1.0 | <https://poly.pizza/m/jLxjFxFRpw> |
| `props/quaternius_broken_cart.glb` | Broken Cart | Quaternius | CC0 1.0 | <https://poly.pizza/m/NBDHe8J7f9> |
| `props/quaternius_cart.glb` | Cart | Quaternius | CC0 1.0 | <https://poly.pizza/m/l7bDe7ak6j> |
| `props/quaternius_dumpster.glb` | Dumpster | Quaternius | CC0 1.0 | <https://poly.pizza/m/PKsbolkZSr> |
| `props/quaternius_market_stand.glb` | Market Stand | Quaternius | CC0 1.0 | <https://poly.pizza/m/DGIM5HGISb> |
| `props/quaternius_street_light_a.glb` | Street Light | Quaternius | CC0 1.0 | <https://poly.pizza/m/nFwrlcLvM5> |
| `props/quaternius_street_light_b.glb` | Streetlight | Quaternius | CC0 1.0 | <https://poly.pizza/m/Wp6Eh4r9VX> |
| `props/quaternius_traffic_barrier.glb` | Traffic Barrier | Quaternius | CC0 1.0 | <https://poly.pizza/m/cM3aJPU9NS> |
| `props/quaternius_traffic_cone.glb` | Traffic Cone | Quaternius | CC0 1.0 | <https://poly.pizza/m/lAx8JytxGD> |
| `props/quaternius_trash_bags.glb` | Trash Bags | Quaternius | CC0 1.0 | <https://poly.pizza/m/eitNk4I4R1> |
| `props/quaternius_trashcan_large.glb` | Trashcan Large | Quaternius | CC0 1.0 | <https://poly.pizza/m/eYNKnGlhon> |
| `props/street_vendor_cart_alan_zimmerman.glb` | Street Vendor Cart | Alan Zimmerman | **CC BY 3.0** | <https://poly.pizza/m/f_LuAcP2_Yh> |
| `trees/quaternius_bush.glb` | Bush | Quaternius | CC0 1.0 | <https://poly.pizza/m/ooG6CkLyE8> |
| `trees/quaternius_palm_tree_a.glb` | Palm Tree | Quaternius | CC0 1.0 | <https://poly.pizza/m/A6cKJYFsIb> |
| `trees/quaternius_palm_tree_b.glb` | Palm Tree | Quaternius | CC0 1.0 | <https://poly.pizza/m/P0tgwyXBgr> |
| `trees/quaternius_tree.glb` | Tree | Quaternius | CC0 1.0 | <https://poly.pizza/m/qZtx0AHhcy> |
| `vehicles/bicycle_jeremy.glb` | Bicycle | jeremy | **CC BY 3.0** | <https://poly.pizza/m/axc03j3xKfz> |
| `vehicles/bus_jeremy.glb` | Bus | jeremy | **CC BY 3.0** | <https://poly.pizza/m/bsvS0E1eo4R> |
| `vehicles/kaylousberg_car_hatchback.glb` | Car Hatchback | Kay Lousberg | CC0 1.0 | <https://poly.pizza/m/BG0KAhmGDt> |
| `vehicles/kaylousberg_stationwagon.glb` | Stationwagon | Kay Lousberg | CC0 1.0 | <https://poly.pizza/m/vTTTjDoxhV> |
| `vehicles/motorcycle_jeremy.glb` | Motorcycle | jeremy | **CC BY 3.0** | <https://poly.pizza/m/0lBe-ApqJs4> |
| `vehicles/quaternius_pickup_truck.glb` | Pickup Truck | Quaternius | CC0 1.0 | <https://poly.pizza/m/qn4grQgHm8> |
| `vehicles/quaternius_suv.glb` | SUV | Quaternius | CC0 1.0 | <https://poly.pizza/m/xsMtZhBkxL> |
| `vehicles/quaternius_taxi.glb` | Taxi | Quaternius | CC0 1.0 | <https://poly.pizza/m/x43lOScTpN> |
| `vehicles/quaternius_truck.glb` | Truck | Quaternius | CC0 1.0 | <https://poly.pizza/m/cXw6oiFtZ8> |
| `vehicles/vespa_scooter_jasmine_roberts.glb` | Vespa | Jasmine Roberts | **CC BY 3.0** | <https://poly.pizza/m/blGLclvvdEM> |

## Looked for but not obtained

* **Auto-rickshaw / tuk-tuk, CC0:** none exists on Poly Haven, poly.pizza, Quaternius, Kenney or OpenGameArt as far as the searches reached; every rickshaw / tuk-tuk model found was paid or under a marketplace licence (CGTrader, Free3D, Unity, Superhive, RenderHub...). Stand-in shipped: `props/street_vendor_cart_alan_zimmerman.glb` (CC BY 3.0 three-wheeled motorbike food cart). Otherwise build one procedurally.
* **Indian-specific scooters/motorbikes under CC0:** poly.pizza has none (all are CC BY, mostly "Poly by Google" with no named author, which were skipped). The Vespa (Jasmine Roberts) and the dirt-bike / road-bike / bus (jeremy) are the named-author CC BY picks.
* **Kenney:** nothing downloaded; poly.pizza's Kenney items did not include the vehicles needed and the Quaternius/Kay Lousberg equivalents were already CC0.

## Removed after inspection

`quaternius_animated_human` (untextured white mesh in a mid-run pose), `scooter_jeremy` (it is a kick scooter), `quaternius_barrel` and `quaternius_crate` (medieval look) were downloaded, inspected and deleted again. `concrete_road_barrier` (Poly Haven, 61 K triangles) was dropped for weight.

