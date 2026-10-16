# Delivery robots on Indian streets — research brief for "Bharat-Bot"

*Compiled 2026-10-15 from web research only; nothing here was measured on a real Indian street. Section map: brief item 1 = §1 · item 2 = §2 · item 3 = §3 · item 5 (top-10) = §4 · item 4 (JSON numbers) = §5, placed after the prose as requested · sources = §6.*

**Evidence grades:** **[A]** official/primary document, or ≥2 independent sources · **[B]** one credible secondary source (news, journal abstract) · **[C]** vendor claim, blog, aggregator or anecdote · **[E]** my estimate / engineering judgement (no source found). "(snippet)" = taken from a search-result summary of a page I could not open. Ids like [S9] point to §6.

---

## Executive summary (10 lines)

1. **The India gap is real, but no vendor has quantified it.** Starship (6 wheels + bogie, ~38 kg, ~6.4 km/h, ~10 kg payload), Serve, Avride and Coco are built for smooth US/EU sidewalks; none publishes a pothole depth, a wading depth or (Starship) an IP rating, so the argument has to come from Indian road data plus geometry. [S36–S39]
2. **Roads:** potholes were linked to 1,856 deaths in 2022 and 2,385 in 2024 (9,438 over 2020–24, Parliament reply); in a Chennai audit 156 of 201 speed breakers exceeded IRC's 10 cm limit; ~44% of Delhi's roads have no footpath; monsoon water hides both potholes and open manholes. [S1, S10, S13, S16]
3. **Dogs:** ~1.53 crore strays (2019 census, likely an undercount) and 37.2 lakh bites in 2024; urban dogs sit in groups (mean 3, up to 12; ~100 m home-range radius). Expert advice when chased is *don't run — stop or slow and let the dog lose interest*, and a 6 km/h robot cannot outrun a 24–32 km/h dog sprint, so the policy is freeze-and-yield. Ultrasonic repellers have no demonstrated effect. Never harm dogs (PCA Act, ABC Rules 2023). [S18–S27]
4. **Theft/vandalism** is well documented abroad (robots kicked/toppled in Los Angeles and Philadelphia, food stolen, Sheffield robots defaced, 1 in 10 Mobike cycles lost in Manchester) yet fleets keep running (Serve claims 99.9% of deliveries complete). App/OTP-locked lid, siren, 12 cameras, tracking and remote assist are cheap to copy; there is no India robot-theft data, but Bengaluru's public bike-share was crippled by vandalism. [S32–S35]
5. **India pilots are tiny and on private property:** Ottonomy×Snapdeal (Delhi-NCR, 2020), Dheera (Hyderabad gated community, 2022, OTP release, 16 parcels), Skye Air drone→mailbox→rover (Gurugram). I found no verified open-street sidewalk-robot service, no Swiggy/Zomato robot pilot, and no AIS standard for sidewalk bots. [S42–S45]
6. **Economics are the weak spot:** a courier costs "often under ₹50" per delivery vs ₹8–12 lakh landed for a Starship-class import; a paper BOM for Bharat-Bot is ₹1.4–3.1 lakh, and my back-of-envelope gives ~₹20–31/delivery at 20–30 deliveries/day but ~₹76 at 8/day. Pitch niches (gated societies, campuses, hospitals, night/monsoon), not "replace riders". [S45, E]
7. **Engineering:** a rocker-bogie clears roughly one wheel diameter, at rover speeds (~10 cm/s); for 10–15 cm potholes use ≥25 cm wheels, ≥15 cm clearance and ≤1 m/s. Holes ("negative obstacles") and water are the hardest things to perceive, so rely on slow speed, flood/pothole maps and refusal rules rather than perception alone. [S48–S50]
8. **Numbers:** §5 is a JSON block where every value is tagged sourced / derived / estimate; most dog, theft and pothole-depth values are estimates because no measured Indian data exists.
9. **What makes it excellent (§4):** a steel-manned baseline-vs-adapted comparison (same seeds, CIs, ablation), every parameter traceable to a source or flagged as an estimate, one real street used for calibration, honest limits, INR BOM and cost per delivery, and a visible safety architecture ("AI suggests, controller decides, hard cut-offs protect").
10. **Caveats:** most figures come through news/aggregator summaries; Factly, Serve's investor PDF, an MDPI paper and a Deccan Herald page returned 403, and anything unverified is marked [C], [E] or (snippet).

---

## 1. Indian street problems (with numbers)

### 1.1 Potholes and broken roads

| Fact | Value | Grade | Src |
|---|---|---|---|
| Deaths attributed to potholes (MoRTH data, Parliament reply) | 2020: 1,555 · 2021: 1,481 · **2022: 1,856** · 2023: 2,161 · **2024: 2,385**; total 9,438 | B (→A if the PQ is checked) | S1, S2 |
| Pothole accidents / injuries 2020–24 | 23,056 accidents; 19,956 injured (9,670 grievous) | B | S1 |
| Concentration | Uttar Pradesh 5,127 deaths (>54%); MP 969; TN 612; Punjab 414. Andhra, Bihar and Goa report zero — implausible, so assume under-reporting | B / E | S1 |
| Older MoRTH series (conflicts with 2020 above) | 2018: 2,015 · 2019: 2,140 · 2020: 1,471 → 5,626 in 2018–20 | C (snippet) | S3 |
| Severity trend | Factly: fatality rate on potholed roads rose 0.27 (2013) → 0.42 (2022) while pothole accidents fell; metric definition not verified | C (snippet; page 403) | S4 |
| National context 2022 | 4,61,312 accidents, 1,68,491 deaths, 4,43,366 injured. Two-wheeler riders 44.5% of deaths (74,897); pedestrians 19.5% (32,825). Curved + pothole + steep-grade roads together = 13.8% of accidents | B | S5, S6 |
| What is a pothole? | No IRC/municipal numeric threshold found. A UK TRL/CEDR draft: depth ≥ ~30 mm, equivalent diameter 100 mm–1 m | B (snippet) | S7 |
| Indian depth data | Only anecdotes: rider says "at least 1 foot" (Mumbai, citizen report); cars/people fall into potholes hidden under rainwater (Bhopal 2026, Pune–Bengaluru highway) | C | S8, S16 |
| Scale | Mumbai: >59,000 potholes recorded in 2023; 6,758 reported in six weeks of Jun–Jul | C | S8 |

→ **Sim:** depth 3–15 cm (typical ~6), diameter 10–100 cm [E]; on "broken" segments put a pothole every 5–15 m; hide most of them under water in flooded patches.

### 1.2 Speed breakers

- **The standard (primary, IRC:99-2018 [A], S9):** circular hump rise **10 cm** (rises above 10 cm "may cause damage"); radius 11–113 m and chord 3.0–9.5 m for 20–50 km/h design speeds (25 km/h → R 15 m, chord 3.5 m; 30 km/h → R 20 m, chord 4.0 m); trapezoidal humps 50–100 mm with ramps; **rumble strips 20–30 mm high, 200–300 mm wide, ~1 m centre-to-centre, ~6 per set**; thermoplastic transverse bars 5 mm and 15 mm.
- **Reality [B, S10]:** Chennai audit (Arappor Iyakkam, Aug 2024): all 201 speed breakers violated IRC; **156 (78%) were higher than 10 cm**; 80 (40%) narrower than the 12 ft design width (so steeper); 190 had no warning sign; 32 had no paint and 64 only moderately visible paint; of 205 manholes, every one sat above or below road level; 61 dangerous silt pits. Maximum measured height was not reported.
- **Harm [C, S11]:** a Lok Sabha reply cites 11,084 deaths "due to speed breakers" in 2015 (11,008 in 2014); another outlet says 3,409 for 2015; I found no 2021–22 figure. Treat as "thousands a year, imprecise".
- → **Sim:** height 8–20 cm (typ ~12), chord 1.5–4 m (the short/steep variant is the dangerous one), ~half unmarked or poorly visible, plus 2–3 cm rumble strips in sets of 6.

### 1.3 Monsoon waterlogging

- Bengaluru, Sept 2022: knee-deep water on the Outer Ring Road; **more than 3 ft (~0.9 m)** in railway underbridges [B, S16].
- Chennai, Cyclone Michaung, Dec 2023: **waist-deep** water, >40 cm of rain in ~48 h, cars floating [B, S16].
- Mumbai, Jul 2026: a pedestrian died after stepping into an **uncovered manhole** in a waterlogged street (grill removed before the rain) [B, S16].
- Depth is invisible: car swallowed by a rainwater-hidden pothole (Bhopal, 2026) [C, S8].
- IMD 24-h classes: heavy 64.5–115.5 mm, very heavy 115.6–204.4 mm, extremely heavy ≥204.5 mm [A, S17]. I found no official "road closed" depth threshold.
- → **Sim:** classes puddle ≤10 cm, knee 30–50 cm, underpass/waist ≥90 cm; open manholes (~60 cm) appear only in flooded stretches [E].

### 1.4 Missing or encroached footpaths

- **~44% of Delhi's roads have no footpath** (IIT Delhi + UCL, 426 pedestrians, 8 south-Delhi wards, 2022) [B, S13]; a researcher says the bigger issue is footpath *condition* [B].
- Delhi Police issued 4,30,202 parking challans in Jan–Mar 2026; pedestrians were 43% of 1,461 fatal crashes in 2022; 649 pedestrians killed in 2025 [B, S13]. Chennai: pedestrian share of fatalities 11% (2019) → 43% (2022) [B, S13].
- **Supreme Court (Narasimha & Chandurkar JJ., reported Jun 2026):** the right to walk on footpaths is part of Art. 19(1)(d) and Art. 21; pedestrians have the first claim over footpaths [B, S13]. A robot must never push people off them.
- **Standards (IRC:103-2012 via ITDP) [B, S12]:** clear width ≥1.8 m residential, ≥2.5 m commercial, kept free of obstructions; kerb ≤150 mm; kerb ramps ≤1:10 per a 2015 MoRTH circular (1.2 m wide), ≤1:12 per another IRC summary — sources conflict.
- **No footpath?** IRC SP:44 advice for pedestrians: walk near the *right* edge facing oncoming traffic (traffic keeps left) [B, S14]. Rule 11 of the Rules of the Road Regulations 1989 bars motor vehicles from footpaths unless permitted — a robot's status is unclear [C, S14].
- Walking speed: IRC design 1.2 m/s; a 5-city study found ~1.19 m/s on sidewalks (71 m/min), ~1.07 m/s with baggage, ~16% lower in shopping areas [B, S15].
- → **Sim:** 40–50% of route length has no usable footpath (blocked by hawkers/parked vehicles/broken slabs); two-wheelers occasionally ride on footpaths.

### 1.5 Street dogs

- **Population [B, S18]:** 1.53 crore in the 2019 Livestock Census (widely seen as an undercount); a pet-homelessness report says ~6 crore free-roaming; an unpublished Thinkpaws estimate is ~550 dogs/km² for NCR (Delhi ~825,313 vs 55,462 in the census). 2024 census delayed.
- **Bites (Health Ministry) [B, S18]:** 2,189,909 (2022) → 3,052,521 (2023) → **3,715,713 (2024)**. Rabies: WHO says India has 36% of world rabies deaths; official counts (21/50/54 in 2022–24) are widely doubted; a Lancet estimate is 5,726/yr, one epidemiologist says ~10,000.
- **How they live [A/B, S19]:** in Panchkula (urban), median home range 3.7 ha (max 40.6 ha) → ~108 m radius if circular (my derivation); **74% of urban sightings were in groups, mean group 3.03, up to 12; packs of ≥4 in 32% of sightings.**
- **Crashes [B, S20]:** in a trauma-centre series of 185 animal-related crashes, stray dogs were 69% and cattle 21%; two-wheelers 92%; peak 4–8 pm. A central-India head-injury series (n=50): two-wheelers 95%. Many injuries come from swerving/falling, not contact. The Supreme Court has remarked that dogs chasing cyclists and two-wheelers cause falls.
- **Delivery workers:** conflict arises when outsiders (delivery workers, rickshaw pullers) enter a pack's territory (Thinkpaws' Nishant Kumar) [B, S18]; a Swiggy rider died in Hyderabad (Jan 2023) after jumping from a third floor to escape a customer's pet dog [B, S29].
- **Chase behaviour:** motivation is debated — predatory sequence (trainers, a vet behaviourist) vs fear/frustration/arousal (Pet Professional Guild / CCPDT webinar) [C, S25]; "territorial dogs stop at their boundary" is cycling-forum lore with no controlled data [C, S26]. Typical sprint 15–20 mph (24–32 km/h) in short bursts; fastest mixed breed clocked 32.3 mph over 100 yd [C/B, S24].
- **Expert guidance when chased [B, S21, S22]:** Four Paws — don't run; walk away slowly or stop and wait; cyclists and motorcyclists slow to a halt; don't speed up; stand sideways; avoid staring. USPS — stay still until the dog leaves, then back away slowly. Delhi University circular — stand still, no eye contact, don't scream or run. (Some cycling blogs say sprint if you can outpace the dog [C, S26] — irrelevant for a 6 km/h robot.)
- **Law [B, S18, S27]:** ABC Rules 2023 (G.S.R. 193(E), 10 Mar 2023): catch–sterilise–vaccinate–**return**, no relocation. Supreme Court, 11 Aug 2025: shelters for NCR strays; **22 Aug 2025** (3 judges) modified it: sterilise, vaccinate, return (rabid/aggressive excluded), feeding only in designated spots. PCA Act s.11 bars cruelty. → The robot must never hurt, trap or spray a dog.
- **Dog-vs-robot evidence:** I found no report of a dog attacking a Starship/Serve/Kiwibot/Coco robot; the one dog incident is a Starship robot hitting a dog in the UK (Co-op, 2023) [C, S28].

### 1.6 Theft and vandalism

| Where / who | What happened | Src |
|---|---|---|
| Los Angeles (Serve, Starship) | Robots kicked over, contents stolen; Serve says 99.9% of deliveries still complete; Starship: robots locked at all times, siren if tampered, 12 cameras | S32 [B] |
| Philadelphia, Mar 2026 (Avride/Uber Eats) | Robot kicked and toppled 18 days after launch; another sat on, graffiti; police not investigating; ~$10,000 per robot | S33 [B] |
| Sheffield, UK, 2026 (Starship) | Robots sprayed "off our streets", flags snapped; Starship paused after 5 months, saying the decision was commercial, not vandalism | S34 [B] |
| Finland (Starship, grocery-store partner) | Robots kicked and spat at; alarm triggers if picked up; recordings go to Starship, not the store | S34 [B] |
| North Carolina (ECU, 2023) | Robots flipped into streams; police threatened charges | S34 [B] |
| Starship co-founder (2018) | Says people kick robots a bit and the robot just keeps driving | S34 [C] |
| Analogues | Mobike left Manchester after 1 in 10 bikes were stolen/vandalised; Bengaluru's public bike-share (Bounce/Ofo/Yulu) hit by "widespread vandalism", per an official; Ofo quit India within 6 months | S35 [B/C] |
| India robot data | **None found.** Dheera's pitch is that gated communities don't want outsiders inside — security is a selling point, not a threat | S43 |

→ **Sim:** model kick/tip, lid break-in and whole-robot theft as separate low-probability events, and sweep the rates (§5). Serve's 99.9% and Mobike's 10% bracket the possibilities, but neither is from India.

### 1.7 Stray cattle

- 2019 census: **50.21 lakh** stray cattle (52.88 lakh in 2012); Rajasthan 12.7 lakh (25.4%), UP 11.84 lakh (23.6%) [A/B, S30].
- The Supreme Court (Jul 2025) voiced concern over fatal accidents from stray cattle on highways; animal-related deaths cited rose from 1,130 (2018) to 1,305 (2020), and the Wire's table (all stray animals) gives 1,128 / 1,422 / 1,303 for 2018/19/20 [B, S30]. In the trauma-centre series cattle were 21% of animal crashes [B, S20].
- Behaviour: cows standing or lying on the road at night are a frequent cause of fatal crashes (Goa editorial) [C]. Size: Indian Sahiwal cows average ~124 cm at the withers and ~327 kg [B, S31].
- Cultural: shoving or bumping a cow can cause community backlash [E] — the robot yields and never touches.

### 1.8 Chaotic mixed traffic

- Traffic keeps left; two-wheelers are ~75% of the vehicle fleet (FY2020) and 44.5% of 2022 road deaths [B, S6].
- Speeds (TomTom 2025): Bengaluru rush-hour average **13.9 km/h**, 10 km takes 36 min 9 s, congestion 74.4% (2nd worst globally); Mumbai average 20.8 km/h; Delhi congestion 60.2% [B, S52].
- Perception: Indian roads are "unstructured" and Western datasets are geographically biased; IIIT-H's IDD-3D has 12k annotated LiDAR frames; DriveIndia (2025) has 66,986 images in 24 classes with YOLO baselines at 78.7% mAP50 — I found no head-to-head "Western model drops X%" number [B, S51].
- Auto-rickshaw: ~2.64 × 1.30 × 1.70 m, ~700 kg, ~60 km/h top speed on petrol/CNG [C, S65]. IIT Delhi respondents rated "two-wheelers and cars on footpaths" unsafe [B, S13].

### 1.9 Heat, dust, crowds, connectivity

- **Heat [B, S54]:** Delhi hit 49.9 °C at two stations on 28 May 2024 (official Safdarjung 45.8 °C); road surfaces routinely exceed 60 °C, with 64 °C thermal readings on Delhi streets. Serve Gen3 is quoted at −20…+45 °C [B, S38] — below Indian extremes. Li-ion charging should derate above ~45 °C (JEITA) [B, S55].
- **Dust [B, S56]:** Delhi PM2.5 ≈ 92 µg/m³ (IQAir 2024, most polluted capital), PM10 ≈ 206 µg/m³ (FY24–25). Expect lens fouling and filter clogging; Coco 2 added an "air blade" that clears water from sensors [C, S39].
- **Crowds:** no quantitative Indian crowd data found. Starship's behaviour is to wait, politely ask people to move, and sound a siren if tampered with [B, S36].
- **Connectivity [B, S53]:** 5G reaches ~86% of the population and 99.9% of districts (minister, 5 Oct 2026); median mobile download 131.77 Mbps (Ookla, Aug 2025; 96.38 a year earlier), Delhi 168 Mbps (H1 2025); indoor/basement coverage is weak; no latency figure found. Starship runs critical safety functions on-device even if the internet drops [B, S36].

---

## 2. What real robots and companies do

### 2.1 Sidewalk robots (US/EU)

| Robot | Drive / size | Speed | Mass / payload | Sensing & compute | Weather / IP | Cost | Src |
|---|---|---|---|---|---|---|---|
| **Starship** | 6 wheels + bogie, climbs kerbs (height unpublished); 697×569×571 mm, cargo box 400×320×340 mm (~43 L) | ~4 mph / 6.4 km/h (FAQ); 6 km/h (Wevolver); in-service average ~3–4 km/h | ~38 kg empty (35 kg in Wevolver); ~10 kg / "three shopping bags" | 12 cameras, radar, ultrasonics, GPS; neural nets classify pedestrians, cyclists, animals; sees objects to 200 ft (~61 m); 1,260 Wh, "18 h" | "All weather"; **no IP rating or wading depth published** (a third party lists IP54, unsourced) | ~$5,500 (unverified) | S36, S37 [B/C] |
| **Serve Gen3** (Oct 2024) | Larger wheels, new suspension | up to 11 mph (was 7) | cargo ≈ four 16" pizzas | Nvidia Jetson Orin, Ouster REV7 lidar; 48 mi / 14 h | −20…+45 °C, heavy rain; no IP published | unpublished; manufacturing cost halved | S38 [B] (snippet) |
| **Avride / Uber Eats** | "multi-wheeled" | 5 mph | 55 lb | cameras, ultrasonics, lidar; ~12 h | n/a | **~$10,000** | S33 [B] |
| **Coco 2** (Feb 2026) | swappable terrain tyres, zero-turn | up to 13 mph on roads/bike lanes | n/a | solid-state lidar, Nvidia; air-blade sensor cleaning; quick-swap battery; ~300 units | n/a | $8–15k (unverified) | S39, S47 [C] |
| **Kiwibot v4** | n/a | 6 km/h | ~15 kg | early supervisors watched up to 3 robots; operators in Medellín ≈ $2/h (2019–20 reports) | n/a | $2.5–5k (unverified) | S40 [C] |
| **Ottonomy Ottobot 2.0/3.0** | 4 driven + steered wheels ("crab mode"); QR-unlock modular cabin; **made in Noida** | n/a | n/a | lidar + cameras, not GPS-dependent | n/a | RaaS subscription, ~$2.5–4k/month (reported) | S41 [B] |

Cross-check numbers (my reading): Starship's ~38 kg and ~6.4 km/h come from its own FAQ; Wevolver's 35 kg / 6 km/h is a third-party sheet; one older page lists a 4-mile radius, while Starship says ~2 miles. Starship claims Level-4 autonomy with >99% of operation autonomous, 15-minute average delivery, 10M+ deliveries, 300+ cities and sites [S36].

### 2.2 India: what actually exists

| Who / where | What | Status / evidence | Src |
|---|---|---|---|
| Ottonomy × Snapdeal, Delhi-NCR | Robots stationed at residential-society entrances for last-mile tests | Pilot, 2020; Ottonomy manufactures in Noida (~40% domestic supply chain, lidar/semiconductors imported) | S41, S42 [B] |
| **Dheera** (Express TechnoLogistics, Hyderabad) | Gated-community robot: courier hands parcels over at the gate, robot goes to the flat (lift via chip), OTP released at the door; **16 parcels per trip** | 2 robots in Narsingi, announced Jun 2022; no later news found | S43 [B] |
| Skye Air (Gurugram) | Drone → smart mailbox → rover trial; BigBasket drone pilot at a Bengaluru apartment complex (7 kg payload) | Early rollout; scale unknown | S44 [B] |
| Others | Rovera (Hyderabad, agri/delivery rovers); student ROS campus robots; **Dunzo dissolved Jan 2025** | — | S44 [C] |
| Swiggy / Zomato | **No sidewalk-robot pilot found** (Swiggy has tested an EV three-wheeler fleet in Delhi-NCR; Zomato did drone tests via TechEagle, 2018–19 reports) | Absence of evidence only; I did not check company newsrooms | search (snippet) |
| Analyst view (RobotWale) | Legal grey zone, **no AIS standard**, landed cost **₹8–12 lakh/unit** (20–40% import duty), human courier "often under ₹50", ROI negative unless labour costs rise; recommends pilots | One publication | S45 [C] |

**Sector reality check:** Amazon Scout was shut in 2022 (~400 people had worked on it; most were reassigned) [S46]; Starship paused Sheffield after 5 months [S34]; Barclays/Reuters put autonomous delivery at $5–7 per drop today, $1 long-term [S47].

### 2.3 Anti-theft features in practice

| Feature | Starship | Others | Fit for India |
|---|---|---|---|
| Lid | Locks automatically; opens only via the customer's app (or the merchant) | Ottonomy QR; Dheera keypad + OTP | OTP unlock matches Swiggy/Zomato habits [E] |
| Tamper alarm | Siren if picked up, kicked, opened; incidents reported | Avride alerts a remote operator | Keep, but cap duration (noise rules, §3) |
| Cameras | 12 cameras; audio alerts let staff respond | Serve/Avride record | DPDP duties apply (§4) |
| Tracking | Computer vision + GPS, "to about an inch" | — | Add an independent LTE beacon [E] |
| Remote humans | Remote assistants watch every robot, can take control when it stops | Kiwibot ~1:3 early; Coco remote edge-case help | Cheap in India; link quality matters |
| When blocked | Steers around, politely asks, then siren if it escalates | — | Crowds will test this daily |

**Dogs:** no vendor publishes a dog policy. Starship classifies "animals" and treats them as obstacles (stop or steer around) [S36].

---

## 3. Engineering fixes and honest evidence

### 3.1 Master table

| Problem | Fix | Evidence it works | Strength |
|---|---|---|---|
| Potholes, kerbs, broken slabs | 6-wheel rocker-bogie, wheels ≥25 cm, clearance ≥15 cm, belly skid plate, speed cap by "ground confidence", fleet-learned pothole map | Rocker-bogie clears ≈1 wheel diameter (Kapvik/JBIS; NASA rovers) but at ~10 cm/s [B]; hole geometry (table below) [E]; holes are "nearly impossible" for lidar and hard for cameras at range (CMU) [B] | Medium (geometry solid, untested in the field) |
| Speed breakers | ≤0.8 m/s approach, ≥25 cm wheels, cargo tray damping, camera + map for unmarked humps | IRC hump = 10 cm rise over 3.5–4 m chord (≈10% grade) [A]; 78% of audited ones are taller, 40% narrower [B] | Medium–high (geometry), low (detecting unmarked humps) |
| Waterlogging | IP67 electronics + sealed hub motors, wade limit below axle (~10 cm), refuse unknown water, flood map + IMD-alert gating, hydrophobic lenses/air-blade, shelter when "very heavy" | **No vendor publishes wading depth**; IP67 means static immersion (1 m / 30 min), not driving through floods [C]; lidar and cameras both mis-read water, depth is not observable [B] | Low evidence, strong logic |
| Missing/encroached footpaths | Ride the road-edge "pedestrian lane" facing traffic, flag + lights + reflectors, cross only at mapped points, follow pedestrians across, keep legs short | IRC SP:44 pedestrian advice [B]; Starship crosses only at mapped crossings [B]; no Indian trial | Low — a 6 km/h object among 14–21 km/h traffic is a hazard |
| Street dogs | Detect → slow at ~15 m → **stop** at ~6 m, stay quiet, lid locked, let the dog sniff and leave; pack ≥3 or persistent → hold or retreat slowly along the path just travelled, call operator; avoid fleet-learned hotspots; **no harmful deterrents** | Consistent expert guidance (Four Paws, USPS, DU) [B]; a robot cannot outrun a 24–32 km/h sprint [E]; no robot-vs-dog trial exists | Medium for freeze-and-yield; very low for ultrasonics |
| Theft / vandalism | OTP/app lid + mechanical lock, IMU lift/tilt/kick sensing, siren (~105 dB at 1 m, ≤30–60 s), 360° recording, independent LTE+GNSS beacon, motor-brake immobiliser, remote voice, geofence, low-value cargo | Starship/Avride/Serve run these and keep operating [B]; Sheffield and Philadelphia show acceptance risk [B] | Medium (global practice), India unknown |
| Stray cattle | Classify large animals; keep ≥1.5 m; yield and wait ~30 s, then reroute; never push or honk; thermal/lidar at dusk | Cows at night cause fatal crashes for fast vehicles [C]; no robot data | Medium by logic |
| Mixed-traffic perception | Fine-tune on IDD-3D / DriveIndia, conservative time-to-collision, yield by default, cross with groups, safety controller separate from the AI | Datasets exist; no public cross-domain drop figure [B] | Medium |
| Heat and dust | Derate above 45 °C, shaded charging, reflective shell, passive cooling, IP6x, filters, pause 12–4 pm in May–Jun | Serve spec stops at 45 °C; Delhi 49.9 °C; JEITA charge limit [B] | Medium by logic |
| Connectivity | Safety stack on-device, dual-SIM, offline maps, hold/crawl/lock timers | Starship on-device safety [B]; 86% 5G coverage but weak indoors [B] | High |

### 3.2 Direct answers to your questions

- **Do ultrasonic dog deterrents work?** There is no good evidence. The only controlled study I found (Moxon, Allison & England, 2010; guide dogs, n=29 and n=24, cross-over) says dogs *noticed* two ultrasonic devices but behaviour was not adversely affected — i.e. no deterrent effect was shown [B, S23]. Typical devices emit ≥20 kHz, outside dogs' most sensitive 4–10 kHz band (patent text) [C], habituation is likely in noisy cities [C], and manufacturer claims are unverified. Treat as optional and unproven; default effect 0 in the sim, sweep 0–15%.
- **What do experts say about stopping vs moving?** For people, cyclists and motorcyclists: don't run or speed up; stop or slow to a crawl and wait; stand sideways; avoid staring [S21, S22]. Cycling forums add "sprint if you can outpace it" [S26], which cannot apply to a robot (max ~1.7 m/s vs a dog's 6.7–8.9 m/s burst). No study tests robots, so label this a *hypothesis from expert guidance*. Video angle: the baseline robot flees and is chased; Bharat-Bot freezes and the dog loses interest.
- **Which suspension handles 10–15 cm potholes?** The only proven passive architecture at this scale is six wheels on a rocker-bogie (NASA rovers) with big wheels; scale it so the pothole depth is ≲0.6 × wheel diameter and drive slowly, because rovers do this at ~10 cm/s. Four-wheel swerve ("crab mode", Ottonomy) improves manoeuvring around holes but not step height. Starship's own patent uses lever-and-wheel kerb climbing [C]. Table below shows why a ~20 cm wheel struggles.
- **How deep can these robots wade?** Nobody publishes it. For a ~26 cm wheel the axle is ~13 cm high, so ~10 cm with sealed hub motors is a defensible limit and anything above axle height or of unknown depth is a no-go [E]. Baseline (20 cm wheel, 6 cm clearance): ~3–5 cm [E].

### 3.3 Hole geometry (my calculation, [E])

A wheel of radius r crossing a hole of width w drops `r − √(r² − (w/2)²)`; if w ≥ 2r it can fall to the hole's full depth, and exiting then needs a step-up equal to that depth.

| Wheel Ø | hole 10 cm wide | 15 cm | 20 cm | 25 cm | ≥ Ø wide |
|---|---|---|---|---|---|
| 16 cm | 1.8 cm | 5.2 cm | full depth | full | full |
| 20 cm | 1.3 cm | 3.4 cm | full (axle level, 10 cm) | full | full |
| 26 cm | 1.0 cm | 2.4 cm | 4.7 cm | 9.4 cm | full |
| 30 cm | 0.9 cm | 2.0 cm | 3.8 cm | 6.7 cm | full at ≥30 |

*Rule of thumb for the sim:* a 15 cm-deep, 40 cm-wide pothole is a 0.75 × Ø step for a 20 cm baseline wheel (stuck or tipping) but 0.58 × Ø for a 26 cm wheel (inside rocker-bogie's nominal ≈1 × Ø, at the edge of what hub motors can pull).

### 3.4 Safety architecture to show on screen (GH-01 rule)

"Edge AI suggests, a safety controller decides, hard-wired cut-offs protect":

1. **AI layer (suggests):** detectors for dog / cow / pothole / water / person / rickshaw propose paths and speeds.
2. **Safety controller (decides):** deterministic rules the AI cannot override — speed caps by zone, dog within ~6 m → stop, low ground confidence → ≤0.5 m/s, unknown water → no-go, link lost > 2 s → hold, > 30 s → crawl to safe spot, > 120 s → lock + beacon.
3. **Hard-wired cut-offs (protect):** bumper switches, tilt > ~25° cuts drive, current/BMS and battery over-temperature cut-offs, hardware e-stop, watchdog, mechanical lid lock — all independent of software.

Make one scene where the AI proposes a dash across the road and the controller vetoes it.

### 3.5 Cost: paper BOM and cost per delivery (INR)

Prices are snapshot listings seen in Oct 2026 and may be stale; US-dollar items at an assumed ~₹88–90/$ (not verified).

| Part | Qty | INR | Basis |
|---|---|---|---|
| Jetson Orin Nano Super 8 GB dev kit | 1 | 30,000–55,000 | listing ₹54,999 incl. GST (US list $249) [S64] |
| 2D lidar (RPLIDAR A1 class) | 1 | 9,300–16,300 | Robu ₹9,298 (stale), Robocraze ₹11,315 (sold out), Amazon.in ₹16,313 [S64] |
| Stereo/depth cameras | 2 | 20,000–50,000 | [E] |
| 360° surround cameras | 4 | 6,000–15,000 | [E] |
| RTK GNSS (ZED-F9P board + antenna) | 1 | 18,000–23,000 | Robocraze ₹17,982–19,352; Amazon.in ₹22,999 [S64] |
| IMU + 6 ultrasonics | — | 1,400–5,000 | [E] |
| 6.5–8" hub motors (hoverboard class) | 6 | 9,000–24,000 | complete 6.5" boards ₹6,500–17,000 [S64]; per motor [E] |
| Motor drivers | 3 | 6,000–20,000 | [E] |
| Rocker-bogie frame, fabrication | 1 | 15,000–40,000 | [E] |
| Sealed shell, lockable lid, insulation | 1 | 8,000–25,000 | [E] |
| 36 V 10–20 Ah Li-ion + BMS (BIS-registered) | 1 | 3,600–10,000 | Amazon.in packs ₹3,599–8,499 [S64] |
| 4G/5G modem + dual SIM | 1 | 3,000–9,000 | [E] |
| e-stop, bumpers, tilt cut-off, siren, flag, lights | — | 3,000–8,000 | [E] |
| Wiring, DC-DC, fuses, glands | — | 5,000–12,000 | [E] |
| **Total (parts only)** | | **≈ ₹1.4–3.1 lakh** | derived; reference: landed Starship-class import ₹8–12 lakh [S45], Avride ~$10,000 ≈ ₹9 lakh [S33] |

**Cost per delivery (my model, all inputs [E]):** life 3 yr × 330 days; maintenance 10%/yr of capex; loss/theft reserve 5%/yr; power + SIM + cloud ₹60/day; one remote operator at ₹25,000/month supervises 6 robots (8 robot-hours/day → ₹185/day).

| Capex | 8/day | 15/day | 20/day | 30/day |
|---|---|---|---|---|
| ₹2.5 lakh (prototype-grade) | ₹76 | ₹41 | ₹31 | ₹20 |
| ₹4.0 lakh (pilot-grade, certified) | ₹104 | ₹55 | ₹42 | ₹28 |

Versus a courier: "often under ₹50" [S45]; ~₹40–80 (lender blog, rough) [S59]; Zomato says its partners averaged ₹102/hour excluding tips in 2025 [S59]. → The robot only wins at high utilisation and a low teleop ratio — a gated community or campus, not open streets. Say so on screen.

---

## 4. What is most important to make this excellent (top 10, prioritised)

1. **A fair baseline-vs-adapted comparison (steel-man the baseline).** Starship really does climb kerbs, lock its lid, sound a siren and run >99% autonomously; give the baseline all of that and let it fail only where physics or data say it should (≈20 cm wheels vs 15 cm holes, no wading rating, no dog policy, no footpath). Run ≥100 seeded episodes per scenario with identical seeds for both robots, report mean ± 95% CI, and add an **ablation** (remove one Bharat-Bot feature at a time) to show which adaptation matters most. Show cases where Bharat-Bot also fails.
2. **Traceable numbers + one real street.** Every parameter gets a source chip or an "estimate" badge (§5 does this). Spend an afternoon on one real street: measure ten potholes with a ruler, photograph speed breakers and footpath width, count dogs/cows/hawkers per 100 m, time a walk. Use those as the demo scene ("calibrated to <your street>"). This is the cheapest way to turn "synthetic" into "grounded".
3. **Get the dog behaviour right and label it a hypothesis.** It is the most distinctive Indian problem and the best-evidenced behaviour change: freeze-and-yield instead of flee, pack ≥3 → slow retreat + operator, never touch or spray a dog. Use the Panchkula group-size/home-range data for the dog agents. Show ultrasonics as "tested, unproven".
4. **Be candid about where it does not work and where it might.** No verified open-street pilot exists in India; labour is cheap (courier "under ₹50"); knee-deep floods are a no-go; packs and dense crowds stop it; connectivity is weak indoors. Position it for gated societies, campuses, hospitals, night and monsoon hours. A "what we don't know" slide builds more trust than a clean sweep.
5. **Show the safety architecture** (§3.4): AI suggests → controller decides → hard cut-offs protect, with on-device safety if the network drops. Include one veto scene and list the hard-wired cut-offs.
6. **INR BOM and cost per delivery with sensitivity** (§3.5): show the break-even curve vs a ₹40–80 courier and name what must be true (utilisation, teleop ratio, loss rate).
7. **Anti-theft and social acceptance in Indian terms.** OTP lid (familiar from Swiggy/Zomato), lift/tilt alarm, camera, tracking; partner with resident welfare associations and gate security; give the robot a name and a helpline. Frame riders as partners, not casualties: India had ~7.7 million gig workers in 2020–21 (NITI Aayog, projected 23.5 million by 2029–30) and Karnataka (2025) and Rajasthan (2023) now levy welfare fees on platforms [S58]. Respect the Supreme Court's pedestrians-first footpath ruling; never touch cows or dogs; expect kids to climb on it.
8. **Show you checked the rules** (table below) and propose "private property first".
9. **Video storytelling.** One 90–120 s hero cut plus short clips per problem. Beat structure: *baseline fails* (≤10 s) → *the number on screen with source* → *Bharat-Bot adaptation* → *same-seed result with CI* → *honest limit*. Split-screen same-seed runs, a live metrics HUD, source chips in captions, English + Hindi subtitles, calm treatment of dogs and cows (never hurt on screen), and an end card with the next real-world test.
10. **Reproducibility and a field-test plan.** Publish scripts, seeds and the §5 JSON with a one-command run; close with a credible next step — a one-week pilot in one gated community logging success rate, interventions per km, dog encounters, tamper events and cost per delivery.

**Metrics worth reporting:** delivery success %, time-to-door, stuck events/km, wheel-drop and high-centre events, peak vertical acceleration at the cargo (spill proxy), min distance to dog/cow/person/vehicle (contact = fail), dog-chase duration and distance, flood refusals and wade violations, theft/tamper attempts vs successes, autonomy ratio (Starship claims >99%), interventions/hour, energy Wh/km, battery temperature, cost per delivery (₹), safety-controller vetoes and hard cut-off trips.

### Regulatory and policy map (as far as I could verify)

| Topic | What I found | Grade | Src |
|---|---|---|---|
| Sidewalk-robot standard | No AIS/standard; legal status a grey zone; AV pilots allowed only in test zones (Haryana, Delhi) | C | S45 |
| Motor Vehicles law | Low-power electric cycles (≤250 W, ≤25 km/h) fall outside "motor vehicle" under CMVR per secondary sources; a robot is not a cycle, so ask a lawyer | C | S63 |
| Footpaths | Rule 11 (Rules of the Road 1989) bars motor vehicles from footpaths; SC 2026 ruling gives pedestrians first claim | B/C | S13, S14 |
| Dogs | ABC Rules 2023; PCA Act s.11; SC orders Aug 2025 (return after sterilisation; no harm) | B | S18, S27 |
| Cameras / data | DPDP Act 2023; Rules notified 14 Nov 2025, most duties apply ~18 months later (~mid-2027); government says AI-enabled CCTV is covered — blur faces/plates, state retention | B | S61 |
| Battery | BIS Compulsory Registration (IS 16046 Part 2:2018 ≈ IEC 62133-2) covers lithium cells/batteries; new rated-capacity order from Feb 2026 | C | S62 |
| Noise | Ambient limits: residential 55/45 dB(A) day/night, commercial 65/55, silence zone 50/40; keep the alarm short and tamper-only | B | S57 |
| Radio modules | WPC/ETA approvals likely needed for LTE/Wi-Fi modules — **not verified here** | E | — |

### Gaps in this research (so nobody over-claims)

No published wading depth or IP rating for any sidewalk robot; no official pothole size threshold or Indian depth distribution; no speed-breaker death count after 2016 and no measured heights beyond the Chennai counts; no robot-vs-dog incident reports; only one controlled ultrasonic study (guide dogs); no India robot-theft data; no Swiggy/Zomato sidewalk pilots; Starship wheel size and kerb height, and Coco/Kiwibot specs, are unpublished or third-party; no 4G/5G latency figures; the 2024 Indian consumer-acceptance paper (n=194) has no number in its abstract [S66]. Blocked pages: Factly, Serve investor PDF, an MDPI curb-climbing paper, Deccan Herald's Supreme Court dog-chase article.

---

## 5. Numbers for the simulation (JSON)

How to use: `typ` = default; `min`/`max` = range to randomise; `basis` = sourced / derived / estimate; `src` ids point to §6. Treat every `estimate` as a hypothesis and sweep it.

```json
{
  "_meta": {
    "project": "Bharat-Bot (India-adapted sidewalk delivery robot) - simulation parameters",
    "compiled_on": "2026-10-15",
    "units": "SI (m, s, m/s, kg, degC, dB) unless the key says otherwise; money in INR",
    "basis_legend": {
      "sourced": "value appears in a cited source",
      "derived": "arithmetic or geometry on sourced values or a standard; see note",
      "estimate": "engineering judgement, no measured or published value found"
    },
    "warning": "No value was measured on a real Indian street. Sweep every estimate in sensitivity runs."
  },

  "baseline_us_robot": {
    "label": "Starship-class US/EU sidewalk robot (steel-manned baseline)",
    "wheel_count": {"typ": 6, "unit": "count", "basis": "sourced", "src": ["S36"]},
    "wheel_diameter_m": {"typ": 0.20, "min": 0.16, "max": 0.22, "unit": "m", "basis": "estimate", "src": [], "note": "unpublished; scaled from 0.57 m body width"},
    "ground_clearance_m": {"typ": 0.06, "min": 0.04, "max": 0.08, "unit": "m", "basis": "estimate", "src": [], "note": "unpublished"},
    "max_step_m": {"typ": 0.10, "min": 0.08, "max": 0.12, "unit": "m", "basis": "derived", "src": ["S36", "S48"], "note": "climbs kerbs (height unpublished); about 0.5 x wheel diameter"},
    "cruise_speed_mps": {"typ": 1.1, "max": 1.78, "unit": "m/s", "basis": "sourced", "src": ["S36", "S37"], "note": "6.4 km/h (4 mph) FAQ; 6 km/h Wevolver; in-service average about 3-4 km/h"},
    "mass_kg": {"typ": 38, "min": 35, "max": 38, "unit": "kg", "basis": "sourced", "src": ["S36", "S37"]},
    "payload_kg": {"typ": 10, "min": 9, "max": 10, "unit": "kg", "basis": "sourced", "src": ["S37"]},
    "body_size_m": {"typ": [0.697, 0.569, 0.571], "unit": "m (L,W,H without flag)", "basis": "sourced", "src": ["S37"]},
    "cargo_box_m": {"typ": [0.40, 0.32, 0.34], "unit": "m", "basis": "sourced", "src": ["S37"]},
    "battery_Wh": {"typ": 1260, "unit": "Wh", "basis": "sourced", "src": ["S37"]},
    "detection_range_m": {"typ": 61, "unit": "m", "basis": "sourced", "src": ["S36"], "note": "200 ft for objects; says nothing about holes or water"},
    "safe_wading_depth_m": {"typ": 0.03, "min": 0.0, "max": 0.05, "unit": "m", "basis": "estimate", "src": [], "note": "no vendor publishes wading depth"},
    "ip_rating": {"typ": "unpublished (a third party lists IP54, unsourced)", "basis": "sourced", "src": ["S36"]},
    "alarm_dB_at_1m": {"typ": 100, "min": 90, "max": 110, "unit": "dB", "basis": "estimate", "src": ["S57"], "note": "siren exists, loudness unpublished"},
    "dog_behaviour": {"typ": "animals detected as obstacles (stop or steer around); no dog-specific policy", "basis": "sourced", "src": ["S36"]},
    "lid_lock": {"typ": "app-unlocked lid, siren on tamper, 12 cameras, tracked, remote assistants", "basis": "sourced", "src": ["S36"]}
  },

  "bharat_bot": {
    "label": "Bharat-Bot design targets (engineering judgement)",
    "wheel_count": {"typ": 6, "unit": "count", "basis": "estimate", "src": ["S48"], "note": "rocker-bogie"},
    "wheel_diameter_m": {"typ": 0.26, "min": 0.24, "max": 0.30, "unit": "m", "basis": "estimate", "src": []},
    "ground_clearance_m": {"typ": 0.15, "min": 0.12, "max": 0.18, "unit": "m", "basis": "estimate", "src": []},
    "max_step_m_safe": {"typ": 0.15, "min": 0.12, "max": 0.18, "unit": "m", "basis": "derived", "src": ["S48"], "note": "about 0.6 x wheel diameter at <=0.5 m/s"},
    "max_step_m_static_limit": {"typ": 0.26, "unit": "m", "basis": "derived", "src": ["S48"], "note": "rocker-bogie about 1 x wheel diameter at rover speeds (~0.1 m/s)"},
    "speed_open_pavement_mps": {"typ": 1.1, "max": 1.4, "unit": "m/s", "basis": "derived", "src": ["S15", "S36"], "note": "pedestrian walking speed 1.05-1.2 m/s; Starship in-service 3-4 km/h"},
    "speed_max_mps": {"typ": 1.7, "unit": "m/s", "basis": "derived", "src": ["S36"], "note": "6 km/h cap"},
    "speed_crowd_mps": {"typ": 0.6, "unit": "m/s", "basis": "estimate", "src": []},
    "speed_rough_ground_mps": {"typ": 0.5, "unit": "m/s", "basis": "estimate", "src": ["S48"]},
    "speed_speed_breaker_mps": {"typ": 0.8, "unit": "m/s", "basis": "estimate", "src": ["S9"]},
    "max_decel_mps2": {"typ": 1.5, "min": 1.0, "max": 2.5, "unit": "m/s^2", "basis": "estimate", "src": [], "note": "stops from 1.1 m/s in about 0.4 m"},
    "mass_kg": {"typ": 45, "min": 40, "max": 55, "unit": "kg", "basis": "estimate", "src": ["S36"]},
    "payload_kg": {"typ": 10, "max": 15, "unit": "kg", "basis": "estimate", "src": ["S37", "S40"]},
    "battery_Wh": {"typ": 720, "unit": "Wh", "basis": "estimate", "src": ["S64"], "note": "36 V x 20 Ah, about 8-10 h"},
    "wade_limit_m": {"typ": 0.10, "min": 0.08, "max": 0.12, "unit": "m", "basis": "estimate", "src": [], "note": "below axle height (0.13 m); refuse unknown-depth water"},
    "ip_target": {"typ": "IP67 electronics + sealed hub motors", "basis": "estimate", "src": []},
    "alarm_dB_at_1m": {"typ": 105, "min": 95, "max": 115, "unit": "dB", "basis": "estimate", "src": ["S57"], "note": "car alarms 100-125 dB, personal alarms up to 130 dB, pain threshold about 120 dB"},
    "alarm_timeout_s": {"typ": 30, "min": 15, "max": 60, "unit": "s", "basis": "estimate", "src": ["S57"], "note": "residential ambient limit is 55/45 dB(A) day/night"},
    "teleop_robots_per_operator": {"typ": 6, "min": 3, "max": 10, "unit": "robots", "basis": "estimate", "src": ["S36", "S40"], "note": "Kiwibot early 1:3; Starship >99% autonomous"},
    "dog_slow_distance_m": {"typ": 15, "unit": "m", "basis": "estimate", "src": []},
    "dog_stop_distance_m": {"typ": 6, "unit": "m", "basis": "estimate", "src": ["S21"]},
    "cow_keep_clear_m": {"typ": 1.5, "unit": "m", "basis": "estimate", "src": []},
    "cow_wait_before_reroute_s": {"typ": 30, "unit": "s", "basis": "estimate", "src": []},
    "link_loss_hold_s": {"typ": 2, "unit": "s", "basis": "estimate", "src": ["S36"]},
    "link_loss_crawl_s": {"typ": 30, "unit": "s", "basis": "estimate", "src": []},
    "link_loss_lock_s": {"typ": 120, "unit": "s", "basis": "estimate", "src": []},
    "bom_inr_parts_only": {"typ": 225000, "min": 137000, "max": 312000, "unit": "INR", "basis": "derived", "src": ["S64"], "note": "sum of section 3.5 table"}
  },

  "terrain": {
    "pothole_depth_m": {"typ": 0.06, "min": 0.03, "max": 0.15, "unit": "m", "basis": "estimate", "src": ["S7", "S8"], "note": "TRL definition >=0.03 m; 0.30 m anecdote (1 ft) is an outlier"},
    "pothole_diameter_m": {"typ": 0.40, "min": 0.10, "max": 1.00, "unit": "m", "basis": "estimate", "src": ["S7"], "note": "TRL: equivalent diameter 0.1-1 m"},
    "pothole_spacing_broken_road_m": {"typ": 8, "min": 5, "max": 15, "unit": "m", "basis": "estimate", "src": []},
    "pothole_hidden_in_flooded_patch_fraction": {"typ": 0.8, "min": 0.5, "max": 1.0, "basis": "estimate", "src": ["S8", "S16"]},
    "speed_breaker_height_m": {"typ": 0.12, "min": 0.08, "max": 0.20, "unit": "m", "basis": "estimate", "src": ["S9", "S10"], "note": "IRC design 0.10 m; 156 of 201 audited were taller"},
    "speed_breaker_height_design_m": {"typ": 0.10, "unit": "m", "basis": "sourced", "src": ["S9"]},
    "speed_breaker_share_taller_than_design": {"typ": 0.78, "basis": "derived", "src": ["S10"], "note": "156/201"},
    "speed_breaker_chord_m": {"typ": 3.7, "min": 1.5, "max": 4.0, "unit": "m", "basis": "derived", "src": ["S9", "S10"], "note": "IRC 3.5-4.0 m for 25-30 km/h; 80 of 201 narrower than 12 ft (3.66 m)"},
    "speed_breaker_share_narrower_than_design": {"typ": 0.40, "basis": "derived", "src": ["S10"], "note": "80/201"},
    "speed_breaker_unmarked_or_faint_fraction": {"typ": 0.48, "basis": "derived", "src": ["S10"], "note": "(32 no paint + 64 moderately visible)/201"},
    "speed_breaker_no_sign_fraction": {"typ": 0.95, "basis": "derived", "src": ["S10"], "note": "190/201"},
    "rumble_strip": {"typ": {"height_m": 0.025, "width_m": 0.25, "pitch_m": 1.0, "count": 6}, "basis": "sourced", "src": ["S9"], "note": "IRC: 20-30 mm high, 200-300 mm wide, about 1 m c/c"},
    "kerb_height_m": {"typ": 0.15, "min": 0.10, "max": 0.25, "unit": "m", "basis": "estimate", "src": ["S12"], "note": "IRC:103 maximum 0.15 m; real kerbs often taller"},
    "kerb_ramp_present_fraction": {"typ": 0.3, "min": 0.1, "max": 0.6, "basis": "estimate", "src": ["S12"]},
    "footpath_clear_width_standard_m": {"typ": 1.8, "max": 2.5, "unit": "m", "basis": "sourced", "src": ["S12"], "note": "1.8 residential, 2.5 commercial"},
    "footpath_usable_width_actual_m": {"typ": 0.8, "min": 0.0, "max": 1.8, "unit": "m", "basis": "estimate", "src": ["S13"]},
    "route_fraction_without_usable_footpath": {"typ": 0.45, "min": 0.3, "max": 0.6, "basis": "derived", "src": ["S13"], "note": "44% of Delhi roads have no footpath; encroachment adds more"},
    "manhole_diameter_m": {"typ": 0.6, "unit": "m", "basis": "estimate", "src": []},
    "manhole_level_mismatch_m": {"typ": 0.03, "min": 0.01, "max": 0.08, "unit": "m", "basis": "estimate", "src": ["S10"], "note": "all 205 audited manholes sat above or below road level"},
    "open_manhole_per_km_flooded": {"typ": 0.1, "min": 0.0, "max": 0.5, "basis": "estimate", "src": ["S16"]}
  },

  "water": {
    "puddle_depth_m": {"typ": 0.08, "min": 0.03, "max": 0.10, "unit": "m", "basis": "estimate", "src": []},
    "knee_deep_m": {"typ": 0.40, "min": 0.30, "max": 0.50, "unit": "m", "basis": "estimate", "src": ["S16"], "note": "Bengaluru ORR 2022 'knee-deep'"},
    "underpass_or_waist_deep_m": {"typ": 0.95, "min": 0.9, "max": 1.2, "unit": "m", "basis": "estimate", "src": ["S16"], "note": ">3 ft Bengaluru underbridges; waist-deep Chennai 2023"},
    "imd_heavy_rain_mm_24h": {"typ": 64.5, "unit": "mm", "basis": "sourced", "src": ["S17"], "note": "very heavy 115.6; extremely heavy 204.5"},
    "service_suspend_rule": {"typ": "suspend at IMD orange/red alert or any unknown-depth water", "basis": "estimate", "src": ["S17"]}
  },

  "dogs": {
    "stray_dog_population_india_2019": {"typ": 15300000, "unit": "dogs", "basis": "sourced", "src": ["S18"], "note": "census, probably an undercount"},
    "bites_per_year_2024": {"typ": 3715713, "unit": "bites", "basis": "sourced", "src": ["S18"]},
    "group_size_mean": {"typ": 3.03, "min": 1, "max": 12, "unit": "dogs", "basis": "sourced", "src": ["S19"], "note": "urban Panchkula"},
    "fraction_sighted_in_groups": {"typ": 0.74, "basis": "sourced", "src": ["S19"]},
    "fraction_packs_of_4_plus": {"typ": 0.32, "basis": "sourced", "src": ["S19"]},
    "home_range_median_ha": {"typ": 3.7, "max": 40.6, "unit": "ha", "basis": "sourced", "src": ["S19"]},
    "territory_radius_m": {"typ": 108, "min": 30, "max": 357, "unit": "m", "basis": "derived", "src": ["S19"], "note": "radius of circle with the median (3.7 ha) and max (40.6 ha) areas"},
    "notice_distance_m": {"typ": 10, "min": 6, "max": 15, "unit": "m", "basis": "estimate", "src": []},
    "approach_speed_mps": {"typ": 1.5, "min": 1.0, "max": 2.5, "unit": "m/s", "basis": "estimate", "src": []},
    "chase_speed_mps": {"typ": 6.0, "min": 4.5, "max": 8.9, "unit": "m/s", "basis": "derived", "src": ["S24"], "note": "typical 15-20 mph sprint = 6.7-8.9 m/s; street dogs leaner, short bursts"},
    "chase_burst_duration_s": {"typ": 6, "min": 3, "max": 12, "unit": "s", "basis": "estimate", "src": []},
    "chase_max_distance_m": {"typ": 40, "min": 15, "max": 120, "unit": "m", "basis": "estimate", "src": ["S19"], "note": "bounded by territory radius"},
    "p_chase_if_robot_flees": {"typ": 0.8, "min": 0.6, "max": 0.95, "basis": "estimate", "src": ["S21", "S22"], "note": "qualitative expert guidance only"},
    "p_chase_if_robot_stops": {"typ": 0.25, "min": 0.1, "max": 0.4, "basis": "estimate", "src": ["S21", "S22"]},
    "give_up_time_if_robot_stationary_s": {"typ": 12, "min": 5, "max": 30, "unit": "s", "basis": "estimate", "src": []},
    "aggressive_fraction": {"typ": 0.10, "min": 0.05, "max": 0.20, "basis": "estimate", "src": [], "note": "no data"},
    "ultrasonic_deterrent_effect": {"typ": 0.0, "min": 0.0, "max": 0.15, "basis": "estimate", "src": ["S23"], "note": "no demonstrated deterrence"},
    "body_size_m": {"typ": [0.8, 0.3, 0.5], "unit": "m (L,W,shoulder H)", "basis": "estimate", "src": []},
    "never_harm_rule": {"typ": "robot never contacts, sprays or traps dogs; contact counts as failure", "basis": "sourced", "src": ["S27"]}
  },

  "cattle": {
    "stray_cattle_india_2019": {"typ": 5021000, "unit": "animals", "basis": "sourced", "src": ["S30"]},
    "withers_height_m": {"typ": 1.24, "min": 1.1, "max": 1.4, "unit": "m", "basis": "sourced", "src": ["S31"], "note": "Indian Sahiwal cow average; others estimated"},
    "body_length_m": {"typ": 1.8, "min": 1.5, "max": 2.1, "unit": "m", "basis": "estimate", "src": []},
    "body_width_m": {"typ": 0.55, "unit": "m", "basis": "estimate", "src": []},
    "mass_kg": {"typ": 327, "min": 250, "max": 450, "unit": "kg", "basis": "sourced", "src": ["S31"]},
    "walk_speed_mps": {"typ": 0.8, "min": 0.0, "max": 1.3, "unit": "m/s", "basis": "estimate", "src": []},
    "p_stationary_on_road_per_100m": {"typ": 0.10, "min": 0.0, "max": 0.30, "basis": "estimate", "src": ["S30"], "note": "higher at night and dusk"}
  },

  "people_and_traffic": {
    "driving_side": {"typ": "left", "basis": "sourced", "src": ["S14"]},
    "pedestrian_walk_speed_mps": {"typ": 1.2, "min": 1.05, "max": 1.2, "unit": "m/s", "basis": "sourced", "src": ["S15"], "note": "IRC design 1.2; measured 1.05-1.19"},
    "pedestrian_density_market_per_m2": {"typ": 0.5, "min": 0.1, "max": 1.5, "unit": "people/m^2", "basis": "estimate", "src": []},
    "two_wheeler_share_of_fleet": {"typ": 0.75, "basis": "sourced", "src": ["S6"], "note": "FY2020"},
    "two_wheeler_share_of_road_deaths_2022": {"typ": 0.445, "basis": "sourced", "src": ["S6"]},
    "pedestrian_share_of_road_deaths_2022": {"typ": 0.195, "basis": "sourced", "src": ["S6"]},
    "urban_traffic_speed_kmh": {"typ": 20, "min": 10, "max": 35, "unit": "km/h", "basis": "derived", "src": ["S52"], "note": "Bengaluru rush hour 13.9; Mumbai average 20.8"},
    "autorickshaw_size_m": {"typ": [2.635, 1.30, 1.70], "unit": "m (L,W,H)", "basis": "sourced", "src": ["S65"]},
    "autorickshaw_speed_kmh": {"typ": 20, "min": 10, "max": 55, "unit": "km/h", "basis": "estimate", "src": ["S65"], "note": "top speed about 55-60"},
    "two_wheeler_size_m": {"typ": [1.9, 0.75, 1.1], "unit": "m (L,W,H)", "basis": "estimate", "src": []},
    "two_wheeler_speed_kmh": {"typ": 25, "min": 10, "max": 45, "unit": "km/h", "basis": "estimate", "src": ["S52"]},
    "p_two_wheeler_on_footpath_per_100m": {"typ": 0.1, "min": 0.0, "max": 0.4, "basis": "estimate", "src": ["S13"]},
    "road_crossing_width_m": {"typ": 7.0, "min": 3.5, "max": 14.0, "unit": "m", "basis": "estimate", "src": []},
    "robot_crossing_time_s": {"typ": 6.4, "unit": "s", "basis": "derived", "src": ["S15"], "note": "7 m at 1.1 m/s; pedestrians need 5.8 s at 1.2 m/s"}
  },

  "theft_and_vandalism": {
    "p_kick_or_tip_attempt_per_km_crowded": {"typ": 0.02, "min": 0.005, "max": 0.10, "basis": "estimate", "src": ["S32", "S33"], "note": "no India data"},
    "p_lid_break_in_attempt_per_delivery": {"typ": 0.01, "min": 0.002, "max": 0.03, "basis": "estimate", "src": ["S32"]},
    "p_whole_robot_theft_attempt_per_1000_robot_hours": {"typ": 0.5, "min": 0.1, "max": 3.0, "basis": "estimate", "src": ["S35"]},
    "reported_delivery_success_rate_serve": {"typ": 0.999, "basis": "sourced", "src": ["S32"], "note": "company claim, LA"},
    "unprotected_asset_loss_upper_bound": {"typ": 0.10, "basis": "sourced", "src": ["S35"], "note": "Mobike Manchester, 1 in 10 bikes; not comparable, unattended bikes"},
    "alarm_trigger_lift_cm": {"typ": 2, "unit": "cm", "basis": "estimate", "src": ["S36"]},
    "alarm_trigger_tilt_deg": {"typ": 15, "unit": "deg", "basis": "estimate", "src": ["S36"]},
    "operator_response_s": {"typ": 20, "min": 10, "max": 60, "unit": "s", "basis": "estimate", "src": ["S36"]},
    "cameras_count": {"typ": 12, "basis": "sourced", "src": ["S36"], "note": "Starship; Bharat-Bot could use 6-8"}
  },

  "environment_and_comms": {
    "ambient_temp_max_C": {"typ": 49.9, "unit": "degC", "basis": "sourced", "src": ["S54"], "note": "Delhi, 28 May 2024"},
    "road_surface_temp_C": {"typ": 60, "min": 55, "max": 64, "unit": "degC", "basis": "sourced", "src": ["S54"]},
    "battery_charge_derate_above_C": {"typ": 45, "unit": "degC", "basis": "sourced", "src": ["S55"]},
    "serve_gen3_rated_temp_C": {"typ": [-20, 45], "unit": "degC", "basis": "sourced", "src": ["S38"]},
    "pm25_delhi_ugm3": {"typ": 91.8, "unit": "ug/m3", "basis": "sourced", "src": ["S56"]},
    "pm10_delhi_ugm3": {"typ": 206, "unit": "ug/m3", "basis": "sourced", "src": ["S56"]},
    "noise_limit_residential_dBA": {"typ": [55, 45], "unit": "dB(A) day/night", "basis": "sourced", "src": ["S57"]},
    "noise_limit_commercial_dBA": {"typ": [65, 55], "unit": "dB(A) day/night", "basis": "sourced", "src": ["S57"]},
    "noise_limit_silence_zone_dBA": {"typ": [50, 40], "unit": "dB(A) day/night", "basis": "sourced", "src": ["S57"]},
    "5g_population_coverage": {"typ": 0.86, "basis": "sourced", "src": ["S53"], "note": "minister, 5 Oct 2026"},
    "median_mobile_download_mbps": {"typ": 131.77, "unit": "Mbps", "basis": "sourced", "src": ["S53"], "note": "Ookla Aug 2025"},
    "p_link_dropout_per_hour_outdoors": {"typ": 0.5, "min": 0.1, "max": 3.0, "basis": "estimate", "src": ["S53"]}
  },

  "mission": {
    "delivery_distance_m": {"typ": 800, "min": 300, "max": 1500, "unit": "m", "basis": "estimate", "src": ["S36", "S60"], "note": "Starship radius about 2 miles; quick-commerce radius 2-3 km"},
    "delivery_time_min": {"typ": 18, "min": 8, "max": 30, "unit": "min", "basis": "derived", "src": ["S36"], "note": "Starship claims 15 min average; 0.8 km at ~3.5 km/h effective is about 14 min plus waits"},
    "effective_speed_kmh": {"typ": 3.5, "min": 2.5, "max": 4.5, "unit": "km/h", "basis": "derived", "src": ["S36"]},
    "order_weight_kg": {"typ": 3, "min": 1, "max": 8, "unit": "kg", "basis": "estimate", "src": []},
    "deliveries_per_robot_per_day": {"typ": 20, "min": 8, "max": 30, "basis": "estimate", "src": []},
    "operating_days_per_year": {"typ": 330, "unit": "days", "basis": "estimate", "src": []}
  },

  "economics_inr": {
    "courier_cost_per_delivery": {"typ": 45, "min": 40, "max": 80, "unit": "INR", "basis": "sourced", "src": ["S45", "S59"], "note": "'often under 50' vs lender blog 40-80"},
    "zomato_partner_earning_per_hour_2025": {"typ": 102, "unit": "INR", "basis": "sourced", "src": ["S59"], "note": "excludes tips; company-sourced"},
    "starship_class_landed_cost": {"typ": 1000000, "min": 800000, "max": 1200000, "unit": "INR", "basis": "sourced", "src": ["S45"], "note": "excl. GST; import duty 20-40%"},
    "avride_unit_cost_usd": {"typ": 10000, "unit": "USD", "basis": "sourced", "src": ["S33"], "note": "about INR 9 lakh at an assumed 88-90 INR/USD"},
    "capex_prototype_inr": {"typ": 250000, "unit": "INR", "basis": "derived", "src": ["S64"], "note": "BOM mid-point plus assembly and test"},
    "capex_pilot_grade_inr": {"typ": 400000, "unit": "INR", "basis": "estimate", "src": []},
    "life_years": {"typ": 3, "unit": "years", "basis": "estimate", "src": []},
    "maintenance_fraction_per_year": {"typ": 0.10, "basis": "estimate", "src": []},
    "loss_reserve_fraction_per_year": {"typ": 0.05, "basis": "estimate", "src": []},
    "operator_cost_inr_per_month": {"typ": 25000, "unit": "INR", "basis": "estimate", "src": []},
    "power_sim_cloud_inr_per_day": {"typ": 60, "unit": "INR", "basis": "estimate", "src": []},
    "cost_per_delivery_inr_capex_250k": {"typ": {"8_per_day": 76, "15_per_day": 41, "20_per_day": 31, "30_per_day": 20}, "unit": "INR", "basis": "derived", "src": [], "note": "section 3.5 model"},
    "cost_per_delivery_inr_capex_400k": {"typ": {"8_per_day": 104, "15_per_day": 55, "20_per_day": 42, "30_per_day": 28}, "unit": "INR", "basis": "derived", "src": [], "note": "section 3.5 model"}
  }
}
```

---

## 6. Sources

*(opened) = I read the page or extracted the PDF; (snippet) = search-result summary only.*

**Roads, potholes, footpaths, water**
- [S1] Pothole deaths 2020–24, Parliament reply, via Siasat (opened) — https://www.siasat.com/pothole-related-road-deaths-surge-53-in-5-yrs-9438-killed-nationwide-3348935/
- [S2] Rajya Sabha PQ 267, 12 Mar 2025 (surfaced, not opened) — https://rsdebate.nic.in/bitstream/123456789/757521/1/PQ_267_12032025_U1533_p371_p376.pdf
- [S3] Tribune, pothole deaths 2018–20 (snippet) — https://www.tribuneindia.com/news/nation/accidents-caused-by-potholes-killed-5626-people-during-2018-2020-424252/amp
- [S4] Factly, fatality rate on potholed roads (page 403; snippet) — https://factly.in/data-fatality-rate-in-accidents-on-potholed-roads-increased-from-0-27-in-2013-to-0-42-in-2022
- [S5] MoRTH 2022 totals (snippet) — https://www.outlookbusiness.com/news/168-lakh-people-died-in-461-lakh-road-accidents-in-2022-road-ministry-report · https://opencity.in/analysing-the-morth-road-accidents-report-for-2022/
- [S6] 2022 road-user shares and fleet share (snippet) — https://www.deccanherald.com/india/in-2022-most-accidents-reported-from-6-pm-9-pm-2753697 · https://savelifefoundation.org/wp-content/uploads/2024/07/Indias-Road-Crash-Statistics_-2022-Overview.pdf · https://www.ceicdata.com/ko/node/2046
- [S7] CEDR/TRL pothole definition (snippet) — https://www.cedr.eu/download/other_public_files/research_programme/eranet_road/call_2011/design/pothole/01_pothole_d1-european-definition-of-the-term-pothole.pdf
- [S8] Mumbai pothole counts; 1-ft anecdote (snippet) — https://www.freepressjournal.in/amp/analysis/mumbais-annual-pothole-crisis-a-deadly-mix-of-corruption-neglect-and-failed-promises · https://www.thequint.com/my-report/mumbai-rains-2019-pothole-accident-western-highway
- [S9] IRC:99-2018 Guidelines for Traffic Calming Measures (opened, text extracted) — https://law.resource.org/pub/in/bis/irc/irc.gov.in.099.2018.pdf
- [S10] Arappor Iyakkam audit of Chennai speed breakers and manholes (opened) — https://www.dtnext.in/news/chennai/several-speed-breakers-manholes-in-chennai-are-dangerous-arappor-iyakkam-report-798655
- [S11] Speed-breaker deaths (snippet) — https://www.governancenow.com/news/regular-story/speed-breakers-left-11000-people-dead-in-2015 · https://www.rushlane.com/speed-breaker-related-accidents-12244997.html
- [S12] IRC:103-2012 via ITDP; MoRTH 2015 circular (snippet) — https://www.itdp.org/wp-content/uploads/2014/07/Footpath-design-131030.pdf · https://morth.gov.in/sites/default/files/comprehensive_compendium_circular/302.22-17.06.2015.pdf
- [S13] Delhi footpaths + Supreme Court ruling (opened); Chennai pedestrians (snippet) — https://www.dtnext.in/news/national/right-to-walk-but-where-supreme-court-ruling-shines-light-on-delhis-footpaths · https://www.dtnext.in/amp/story/news/chennai/chennais-footpath-crisis-missing-pavements-put-pedestrians-in-peril-793031
- [S14] Pedestrians facing traffic (IRC SP:44); Rules of the Road Regulations 1989 (snippet) — https://www.dailyexcelsior.com/pedestrians-safety-always-walk-on-the-right-side-of-road/ · https://www.aptransport.org/html/pdf/rules_of_the_road_regulations_1989.pdf
- [S15] Indian walking speeds (snippet) — https://ascelibrary.com/doi/10.1061/%28ASCE%29TE.1943-5436.0000251 · https://doaj.org/article/52c42c6cb4984ad19298d32a51709227
- [S16] Waterlogging reports (snippet) — https://www.deccanherald.com/amp/story/india%2Fkarnataka%2Fbengaluru%2Froads-turn-into-rivers-as-rain-piles-misery-on-bengaluru-1140866.html · https://www.aljazeera.com/news/2023/12/5/cyclone-michaung-makes-landfall-in-indias-south-nine-killed-in-floods · https://www.republicworld.com/india/heavy-rain-exposes-india-s-fragile-urban-infrastructure-fatalities-cave-ins-and-submerged-roads-2026-07-02-130983 · https://www.freepressjournal.in/amp/pune/man-falls-into-waterlogged-pothole-on-pune-bengaluru-highway-service-road-viral-video-raises-safety-concerns
- [S17] IMD heavy-rain classes (snippet) — https://rsmcnewdelhi.imd.gov.in/uploads/archive/8/8_1566bc_8_f9822f_heavy%20rainfall%201606.pdf

**Dogs and cattle**
- [S18] Al Jazeera, "Does India have a stray dog epidemic?" (opened) — https://www.aljazeera.com/features/2025/8/30/does-india-have-a-stray-dog-epidemic
- [S19] Tiwari et al. 2019, free-roaming dog group size and home range in India (opened) — https://pmc.ncbi.nlm.nih.gov/articles/PMC6963394/
- [S20] Animal-related road crashes (snippet) — https://pmc.ncbi.nlm.nih.gov/articles/PMC8054802 · https://www.nepjol.info/index.php/AJMS/article/view/60145
- [S21] Four Paws, staying safe around street dogs (opened) — https://www.four-paws.org/our-stories/publications-guides/staying-safe-around-street-dogs
- [S22] USPS via UPU; Delhi University circular (snippet) — https://upu.int/en/news/2020/12/usps-steps-on-how-to-avoid-being-bitten · https://www.du.ac.in/uploads/2026/14012026-Annexure-I.pdf
- [S23] Moxon, Allison & England 2010, ultrasonic devices and guide dogs (opened); patent text on 20 kHz vs 4–10 kHz (snippet) — https://reference-global.com/article/10.21307/ijom-2010-003 · https://patents.google.com/patent/US10058089
- [S24] Dog sprint speeds (snippet) — https://rover.com/blog/how-fast-can-a-dog-run · https://www.nationalgeographic.com/animals/article/meet-phelan-rescue-now-americas-fastest-dog
- [S25] Why dogs chase (snippet) — https://www.mentalfloss.com/animals/dogs/why-dogs-chase-cars · https://www.petprofessionalguild.com/webinars-events/webinars/busting-the-herding-myth-car-chasing-in-border-collies-with-rachel-rodgers/
- [S26] Cycling-community advice (snippet) — https://terrycycling.com/blogs/peloton/how-to-prevent-dog-attacks-a-guide-for-cyclists · https://www.roadbikerider.com/?p=23965
- [S27] ABC Rules 2023; PCA Act (snippet) — https://en.vikaspedia.in/health/nrhm/national-health-policies/animal-birth-control-rules-2023-notified-by-central-government · https://www.iitk.ac.in/animalwelfare/data/Animal-Protection-Law-Summary-by-AWBI.pdf
- [S28] Starship robot hits dog, Co-op UK (snippet) — https://www.grocerygazette.co.uk/2023/06/19/dog-walker-attack-co-op-robot/
- [S29] Hyderabad delivery rider and dog (snippet) — https://www.thenewsminute.com/telangana/hyderabad-food-delivery-agent-jumps-3rd-floor-after-being-chased-dog-critical-171952
- [S30] Stray cattle census and Supreme Court (snippet) — https://factly.in/data-the-number-of-stray-cattle-decreased-at-the-national-level-while-it-increased-in-certain-states · https://thewire.in/rights/stray-cattle-are-an-invitation-to-death-supreme-court-orders-compensation-accountability · The Goan editorial on stationary cows at night (URL as surfaced, contains a hidden character; search its title if it fails): https://www.thegoan.net/prespective/tackling-the-growing-grave-stray-cattle-menace/96023.html
- [S31] Indian cattle size (snippet) — https://en.wikipedia.org/wiki/Sahiwal_cattle · https://ndri.res.in/NICRA/NICRALOV/breed.aspx

**Theft and vandalism**
- [S32] KTLA, robots under attack in LA (opened) — https://ktla.com/news/local-news/food-delivery-robots-under-attack-from-vandals-thieves-local-businesses-starting-to-be-affected/amp/
- [S33] Philadelphia Inquirer, Avride robot kicked (opened) — https://www.inquirer.com/news/philadelphia/uber-eats-delivery-robot-kicked-center-city-hitchbot-20260401.html
- [S34] Sheffield, Finland, ECU, Starship 2018 quote, Chicago (snippet) — https://www.retailgazette.co.uk/blog/2026/08/starship-technologies-delivery-robots-pulled-from-sheffield-after-five-month-trial/ · https://yle.fi/a/74-20136655 · https://www.witn.com/2023/02/21/ecu-food-delivery-robots-damaged-students-and-police-denounce-vandals · https://www.supermarketnews.com/grocery-technology/people-are-kicking-food-delivery-robots · https://www.popsci.com/technology/delivery-robots-crash-bus-shelters
- [S35] Bike-share analogues (snippet) — https://inc42.com/datalab/lessons-for-indias-bike-sharing-startups-from-ofos-failure/ · https://www.deccanherald.com/india/karnataka/bengaluru/three-years-after-govt-launched-pbs-bicycles-extinct-from-bengaluru-roads-977881.html · https://technode.com/2018/09/07/mobike-pulls-out-manchester/

**Robots and companies**
- [S36] Starship official pages (opened) — https://www.starship.xyz/faq/ · https://www.starship.xyz/our-robots/ · https://www.starship.xyz/autonomous-robots-accessibility/ · https://www.starship.xyz/
- [S37] Starship third-party specs (opened) — https://wevolver.com/specs/starship-technologies-starship-robot · https://www.dimensions.com/element/starship-robot · https://collection.sciencemuseumgroup.org.uk/objects/co8697500/starship-technologies-self-driving-delivery-robot
- [S38] Serve Gen3 (snippet; investor PDF 403) — https://electrek.co/?p=384471 · https://www.nasdaq.com/press-release/serve-robotics-rolls-out-third-generation-autonomous-delivery-robot-platform-upgrade
- [S39] Coco 2 (snippet) — https://www.semafor.com/article/02/25/2026/cocos-new-delivery-robot-is-hitting-the-streets-literally-and-without-a-human-driver · https://onshape.com/en/blog/coco-robotics-delivery-bot-reliable-cloud-native-cad-arena-plm
- [S40] Kiwibot (snippet; specs third-party) — https://thehustle.co/kiwibots-autonomous-food-delivery · https://electrek.co/?p=198524 · https://robotomated.com/explore/delivery/kiwibot-v4
- [S41] Ottonomy (opened/snippet) — https://thespoon.tech/ottonomy-debuts-a-swervy-customizable-delivery-robot-in-ottobot-2-0-as-it-closes-3-3m-seed-round/ · https://www.electronicsforu.com/india-corner/ottonomys-robots-worlds-service · https://inc42.com/startups/how-ottonomy-robots-are-mapping-last-mile-delivery-with-contextual-ai/
- [S42] Snapdeal × Ottonomy (snippet) — https://www.bloombergquint.com/technology/snapdeal-tests-last-mile-delivery-using-ottonomyios-robots · https://www.techradar.com/news/indian-ecommerce-player-snapdeal-uses-robots-for-last-mile-delivery
- [S43] Dheera, Hyderabad (opened) — https://etvbharat.com/english/state/telangana/dheera-robots-deliver-food-in-hyderabad/na20220624145016377377813
- [S44] Skye Air, BigBasket drones, Dunzo, Rovera (snippet) — https://www.cartoq.com/car-news/skye-air-autonomous-drone-doorstep-delivery/ · https://unlistedzone.com/bigbasket-launches-indias-first-drone-delivery-pilot-in-bengaluru-apartment-complex · https://en.wikipedia.org/wiki/Dunzo · https://www.rov-era.com/
- [S45] RobotWale India analysis (opened) — https://robotwale.com/article/last-mile-delivery-bots-starship-serve-3
- [S46] Amazon Scout shut down (snippet) — https://www.freightwaves.com/news/amazon-scraps-scout-home-delivery-robot
- [S47] Unit and per-order cost estimates (snippet) — https://grabarobot.com/blog/last-mile-delivery-robot-guide/ · https://finance.yahoo.com/news/robots-drones-could-slash-global-113404701.html

**Engineering**
- [S48] Rocker-bogie obstacle limits (snippet) — https://bis-space.com/shop/?p=9658 · https://robotix.in/tutorial/mechanical/rockerbogie
- [S49] Negative-obstacle detection (snippet) — https://www.ri.cmu.edu/project/negative-obstacle-detection · https://opus.lib.uts.edu.au/handle/10453/127018
- [S50] Water/puddle detection (snippet) — https://arxiv.org/pdf/1701.04175 · https://daniel.lawrence.lu/blog/2016-04-28-puddle-detection
- [S51] Indian driving datasets (snippet) — https://openaccess.thecvf.com/content/WACV2023/html/Dokania_IDD-3D_Indian_Driving_Dataset_for_3D_Unstructured_Road_Scenes_WACV_2023_paper.html · https://arxiv.org/pdf/2507.19912v1

**Traffic, climate, comms**
- [S52] TomTom Traffic Index (snippet) — https://www.tomtom.com/traffic-index/bengaluru-traffic · https://www.outlooktraveller.com/News/global-traffic-index-2025-indian-cities-among-the-most-congested-on-earth
- [S53] Ookla India speeds; 5G coverage (snippet) — https://www.fonearena.com/blog/tag/india-median-mobile-download-speeds-h1-2025-ookla · https://www.newkerala.com/news/a/indias-5g-network-reaches-86-population-target-set-647.htm
- [S54] Heat (snippet) — https://www.newsonair.gov.in/several-parts-of-country-continues-to-reel-under-severe-heat-wave-conditions-breaking-past-records · https://www.businesstoday.in/amp/world/story/roads-melt-in-europes-heatwave-why-indian-roads-withstand-temperatures-above-50degc-540231-2026-07-01
- [S55] Li-ion charging temperature, JEITA (snippet) — https://ira.lib.polyu.edu.hk/bitstream/10397/92265/1/Liang_Lithium-ion_Battery_JEITA.pdf
- [S56] Air quality (snippet) — https://www.deccanherald.com/amp/story/india/byrnihat-tops-global-pollution-list-delhi-most-polluted-capital-report-3441107 · https://www.autocarpro.in/news/delhi-tops-fy-2024%e2%80%9325-pm10-pollution-list-byrnihat-most-polluted-in-march-2025-125798
- [S57] Noise rules and alarm loudness (snippet) — https://eco-intelligent.com/2017/12/03/noise-pollution-regulation-and-control-rules-2000/ · https://engineerfix.com/how-many-decibels-is-a-car-alarm/ · https://www.mace.com/blogs/self-defense-training/how-do-personal-alarms-work · https://memtechacoustical.com/?p=535

**Economics, policy, hardware**
- [S58] Gig economy and labour law (snippet) — https://www.isb.edu/content/dam/sites/isb/research-thought-leadership/research-institute/iids/Gig-Economy-NITI-Aayog.pdf · https://thesouthfirst.com/karnataka/karnataka-passes-landmark-gig-workers-bill-to-provide-social-security-cover/ · https://www.outlookbusiness.com/news/gig-workers-secured-under-new-labour-codes-as-aggregators-must-pay-2-of-turnover
- [S59] Courier earnings (snippet) — https://www.businesstoday.in/amp/latest/corporate/story/look-at-the-full-picture-deepinder-goyal-breaks-down-delivery-partner-earnings-with-hard-facts-509252-2026-01-02 · https://www.shriramfinance.in/two-wheeler-loan/articles/monthly-earnings-with-bike-on-zomato-swiggy-blinkit
- [S60] Delivery distances (snippet) — https://www.restaurantindia.in/news/tag/food-delivery-business?page=19 · https://www.ithinklogistics.com/blog/quick-commerce-companies-in-india/ · https://gulfnews.com/amp/story/business%2Findia-delivery-apps-cash-in-across-countrys-congested-cities-1.500140298
- [S61] DPDP Act and Rules (snippet) — https://www.medianama.com/2026/04/223-govt-ai-enabled-cctv-cameras-dpdp-rules/ · https://www.india-briefing.com/news/india-draft-dpdp-rules-2025-key-provisions-updates-35697.html
- [S62] BIS CRS for lithium batteries (snippet; consultancy blogs) — https://www.nemko.com/en-in/product-certification/bis-compulsory-registration-scheme · https://www.agileregulatory.com/blogs/bis-registration-for-lithium-ion-batteries-under-crs
- [S63] Low-power e-vehicle threshold (snippet; secondary) — https://zbotic.in/e-bike-legal-limit-in-india-speed-power-and-registration-rules/
- [S64] India hardware listings, Oct 2026 (snippet) — https://varietyinfotech.com/product/nvidia-jetson-orin-nano-super-developer-kit/ · https://thinkrobotics.com/ar/blogs/product-reviews-buying-guides/jetson-orin-nano-price-complete-buying-guide-for-ai-robotics-development · https://robu.in/product/rp-lidar-a1m8-360-degrees-laser-range-finder/ · https://robocraze.com/products/rplidar-a1m8-360-degree-laser-range-finder · https://www.amazon.in/Slamtec-RPLIDAR-A1M8-Avoidance-Navigation/dp/B07TJW5SXF · https://robocraze.com/products/smartelex-gps-rtk-board-ufl-zed-f9p-04b · https://www.amazon.in/Rechargeable-Included-Electric-tricycles-Industrial/dp/B0GDS3TB6C · https://m.indiamart.com/radboards
- [S65] Bajaj RE auto-rickshaw dimensions (snippet) — https://www.91trucks.com/auto-rickshaws/bajaj/compact-re?amp=1
- [S66] Indian consumer acceptance of delivery robots, n=194 (snippet) — https://ideas.repec.org/a/ids/ijsoma/v48y2024i4p462-480.html · https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9521669/
