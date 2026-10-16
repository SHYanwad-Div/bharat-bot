import { Audio, Video } from "@remotion/media";
import React from "react";
import { AbsoluteFill, Easing, Img, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import evaluation from "../data/evaluation.json";
import { ControlRoomHud } from "./ControlRoomHud";
import { firstEvent, shots } from "./data";
import { FailOverlay } from "./FailOverlay";
import { colors, fonts, panel } from "./theme";
import { CaptionCard, CardBackground, DesignCanvas, Kicker, PopIn, SourceChip, useInOut } from "./ui";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const fill: React.CSSProperties = { position: "absolute", width: "100%", height: "100%" };

// ------------------------------------------------------------------------------------------------ title
export const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const k = useInOut(18, 14);
  return (
    <AbsoluteFill style={{ background: colors.bg }}>
      <Img src={staticFile("stills/title.jpg")} style={{ ...fill, objectFit: "cover",
        scale: String(interpolate(frame, [0, durationInFrames], [1.0, 1.07])) }} />
      <AbsoluteFill style={{ background: "linear-gradient(90deg, rgba(7,11,20,0.92) 0%, rgba(7,11,20,0.65) 45%, rgba(7,11,20,0.1) 100%)" }} />
      <DesignCanvas>
        <div style={{ position: "absolute", left: 120, top: 300, opacity: k, translate: `${(1 - k) * -40}px 0px` }}>
          <Kicker>Sidewalk delivery robot · India edition</Kicker>
          <div style={{ fontSize: 170, fontWeight: 700, lineHeight: 1, marginTop: 10 }}>
            <span style={{ color: colors.saffron }}>BHARAT</span><span>-</span><span style={{ color: colors.greenBright }}>BOT</span>
          </div>
          <div style={{ fontSize: 48, fontWeight: 600, marginTop: 14 }}>Built for potholes, street dogs, cows and thieves</div>
          <div style={{ display: "flex", gap: 12, marginTop: 34, opacity: interpolate(frame, [fps, 1.6 * fps], [0, 1], clamp) }}>
            <SourceChip>simulated in Blender 5.2</SourceChip>
            <SourceChip>physics + agents in Python</SourceChip>
            <SourceChip>66 research sources</SourceChip>
          </div>
        </div>
      </DesignCanvas>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------------------------------------ US vs India
export const UsScene: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: colors.bg }}>
      <Video src={staticFile("clips/us_sidewalk.mp4")} muted objectFit="cover" premountFor={fps} style={fill} />
      <DesignCanvas>
        <div style={{ ...panel, position: "absolute", left: 40, top: 30, padding: "12px 22px" }}>
          <div style={{ fontSize: 22, letterSpacing: 5, color: colors.blue }}>MEANWHILE IN THE US</div>
          <div style={{ fontSize: 34, fontWeight: 700 }}>Smooth sidewalks, kerb ramps, no strays</div>
        </div>
      </DesignCanvas>
      <Sequence from={Math.round(0.6 * fps)} durationInFrames={Math.round(5.2 * fps)} premountFor={fps}>
        <CaptionCard top={820} accent={colors.blue} maxWidth={1300}
          text="Robots like Starship have made 10M+ deliveries on sidewalks like this." />
      </Sequence>
    </AbsoluteFill>
  );
};

const Stat: React.FC<{ big: string; label: string; src: string; delay: number; color: string }> = ({ big, label, src, delay, color }) => (
  <PopIn delay={delay}>
    <div style={{ ...panel, width: 780, padding: "20px 28px", borderLeft: `8px solid ${color}` }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 18 }}>
        <div style={{ fontSize: 76, fontWeight: 700, color, lineHeight: 1 }}>{big}</div>
        <div style={{ fontSize: 32, fontWeight: 600, lineHeight: 1.1 }}>{label}</div>
      </div>
      <div style={{ marginTop: 10 }}><SourceChip>{src}</SourceChip></div>
    </div>
  </PopIn>
);

export const IndiaScene: React.FC = () => {
  const { fps } = useVideoConfig();
  const k = useInOut(12, 12);
  return (
    <AbsoluteFill>
      <CardBackground />
      <DesignCanvas>
        <div style={{ position: "absolute", left: 120, top: 90, opacity: k }}>
          <Kicker>Meanwhile in India</Kicker>
          <div style={{ fontSize: 76, fontWeight: 700 }}>Our streets are a different game</div>
        </div>
        <div style={{ position: "absolute", left: 120, top: 330, display: "grid", gridTemplateColumns: "780px 780px", gap: 32, opacity: k }}>
          <Stat delay={Math.round(0.4 * fps)} color={colors.red} big="2,385" label="deaths linked to potholes in 2024" src="MoRTH data · Parliament reply" />
          <Stat delay={Math.round(0.8 * fps)} color={colors.amber} big="37 lakh" label="dog bites in 2024 · 1.5 crore strays" src="Health Ministry · Livestock Census 2019" />
          <Stat delay={Math.round(1.2 * fps)} color={colors.saffron} big="44%" label="of Delhi roads have no footpath" src="IIT Delhi + UCL study, 2022" />
          <Stat delay={Math.round(1.6 * fps)} color={colors.violet} big="78%" label="of audited speed breakers break the 10 cm rule" src="Arappor Iyakkam audit, Chennai 2024" />
        </div>
      </DesignCanvas>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------------------------------------ baseline failures
type FailProps = { clip: string; shot: "baselinePothole" | "baselineDogs" | "baselineTheft"; trimBefore: number;
  playbackRate: number; stamp: string; why: string; scenario: string; intro?: string };

export const FailScene: React.FC<FailProps> = ({ clip, shot, trimBefore, playbackRate, stamp, why, scenario, intro }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: colors.bg }}>
      <Video src={staticFile(clip)} muted objectFit="cover" trimBefore={trimBefore} playbackRate={playbackRate}
        premountFor={fps} style={fill} />
      <FailOverlay tel={shots[shot]} trimBefore={trimBefore} playbackRate={playbackRate} stamp={stamp} why={why} scenario={scenario} />
      {intro ? (
        <Sequence from={0} durationInFrames={Math.round(2.6 * fps)} premountFor={fps}>
          <CaptionCard top={150} accent={colors.red} text={intro} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------------------------------------ features
const FEATURES: [string, string][] = [
  ["32 cm wheels on a rocker-bogie", "keeps all 6 wheels down · climbs ~18 cm"],
  ["Depth camera + LiDAR", "sees holes and standing water, not just obstacles"],
  ["Freeze protocol for street dogs", "stop, go quiet, let them lose interest · no ultrasonics"],
  ["OTP lid + tamper alarm", "lift or tilt → siren, photo, live GPS to ops"],
  ["Traffic-aware planner", "keeps left, yields before stepping into the lane"],
  ["Sealed for the monsoon", "IP67 motors · wades up to 8 cm, refuses deeper water"],
];

export const FeaturesScene: React.FC = () => {
  const { fps } = useVideoConfig();
  const k = useInOut(12, 12);
  return (
    <AbsoluteFill style={{ background: colors.bg }}>
      <Video src={staticFile("clips/bharat_full.mp4")} muted objectFit="cover" trimBefore={640} playbackRate={0.7}
        premountFor={fps} style={fill} />
      <AbsoluteFill style={{ background: "linear-gradient(90deg, rgba(7,11,20,0.94) 0%, rgba(7,11,20,0.82) 46%, rgba(7,11,20,0.0) 78%)" }} />
      <DesignCanvas>
        <div style={{ position: "absolute", left: 110, top: 90, opacity: k }}>
          <Kicker color={colors.greenBright}>The India-adapted design</Kicker>
          <div style={{ fontSize: 80, fontWeight: 700 }}>Meet Bharat-Bot</div>
          <div style={{ height: 26 }} />
          {FEATURES.map(([a, b], i) => (
            <PopIn key={a} delay={Math.round((0.5 + 0.35 * i) * fps)}>
              <div style={{ display: "flex", gap: 18, alignItems: "baseline", marginBottom: 16 }}>
                <div style={{ width: 14, height: 14, borderRadius: 7, background: i % 2 ? colors.greenBright : colors.saffron }} />
                <div>
                  <div style={{ fontSize: 38, fontWeight: 700, lineHeight: 1.05 }}>{a}</div>
                  <div style={{ fontSize: 26, color: colors.muted }}>{b}</div>
                </div>
              </div>
            </PopIn>
          ))}
        </div>
      </DesignCanvas>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------------------------------------ the hero run
const CAPTIONS: { at: string; text: string; accent: string; dur?: number }[] = [
  { at: "Pothole 11 cm", text: "Potholes: the depth camera sees them, the planner steers round", accent: colors.saffron },
  { at: "Speed breaker", text: "Unmarked 12 cm speed breaker: slow to 0.6 m/s, all six wheels stay down", accent: colors.amber },
  { at: "Waterlogged patch", text: "3.5 cm of water: under the 8 cm limit, so it wades, slowly", accent: colors.blue },
  { at: "3 street dogs", text: "Street dogs: it freezes. Nothing moving = nothing to chase", accent: colors.amber, dur: 5.5 },
  { at: "Cow standing", text: "Cow in the lane, auto-rickshaw behind: wait, then pass", accent: colors.blue, dur: 5 },
  { at: "Lid pulled", text: "Theft attempt: the lid only opens with the customer's OTP", accent: colors.red },
  { at: "THEFT ALARM", text: "Lifted? 110 dB siren, photo and live GPS to the ops centre", accent: colors.red },
  { at: "OTP 4819", text: "Delivered: OTP at the gate, food upright and sealed", accent: colors.greenBright, dur: 5 },
];

/** Bharat-Bot's run with the control-room HUD. `trimBefore` starts it at any moment; HUD, captions and sounds follow. */
export const HeroScene: React.FC<{ trimBefore?: number }> = ({ trimBefore = 0 }) => {
  const { fps, durationInFrames } = useVideoConfig();
  const tel = shots.bharatFull;
  const at = (title: string) => {
    const e = firstEvent(tel, title);
    if (!e) return null;
    const f = Math.round((e.frame / tel.fps) * fps) - trimBefore;
    return f >= -6 && f < durationInFrames ? Math.max(0, f) : null;
  };
  const senses = tel.events
    .map((e) => ({ e, f: Math.round((e.frame / tel.fps) * fps) - trimBefore }))
    .filter(({ e, f }) => e.level === "SENSE" && f >= 0 && f < durationInFrames);
  const alarm = at("THEFT ALARM");
  const dogs = at("3 street dogs");
  const done = at("DELIVERED");
  return (
    <AbsoluteFill style={{ background: colors.bg }}>
      <Video src={staticFile("clips/bharat_full.mp4")} muted objectFit="cover" trimBefore={trimBefore} premountFor={fps} style={fill} />
      <ControlRoomHud tel={tel} trimBefore={trimBefore} />
      {CAPTIONS.map((c) => {
        const from = at(c.at);
        return from === null ? null : (
          <Sequence key={c.at} from={from} durationInFrames={Math.round((c.dur ?? 4) * fps)} premountFor={fps}>
            <CaptionCard text={c.text} accent={c.accent} top={118} maxWidth={820} />
          </Sequence>
        );
      })}
      {senses.map(({ e, f }) => (
        <Sequence key={`ping-${e.frame}-${e.label}`} from={f} durationInFrames={Math.round(0.8 * fps)} premountFor={fps}>
          <Audio src={staticFile("audio/ping.wav")} volume={0.22} />
        </Sequence>
      ))}
      {dogs !== null ? (
        <Sequence from={dogs} durationInFrames={Math.round(0.6 * fps)} premountFor={fps}>
          <Audio src={staticFile("audio/alert.wav")} volume={0.45} />
        </Sequence>
      ) : null}
      {alarm !== null ? (
        <Sequence from={alarm} durationInFrames={Math.round(3.0 * fps)} premountFor={fps}>
          <Audio src={staticFile("audio/siren.wav")} volume={0.42} />
        </Sequence>
      ) : null}
      {done !== null ? (
        <Sequence from={done} durationInFrames={Math.round(1.0 * fps)} premountFor={fps}>
          <Audio src={staticFile("audio/success.wav")} volume={0.6} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};

/** One highlight from the full run, starting a little before the event that defines it. */
const MOMENTS = {
  potholes: { title: "Pothole 11 cm", before: 0.4 },
  dogs: { title: "3 street dogs", before: 1.2 },
  cow: { title: "Cow standing", before: 1.0 },
  theft: { title: "Lid pulled", before: 1.5 },
  delivery: { title: "OTP 4819", before: 2.0 },
} as const;

export const HeroMoment: React.FC<{ moment: keyof typeof MOMENTS }> = ({ moment }) => {
  const { fps } = useVideoConfig();
  const tel = shots.bharatFull;
  const m = MOMENTS[moment];
  const e = firstEvent(tel, m.title);
  const start = e ? Math.max(0, Math.round((e.frame / tel.fps - m.before) * fps)) : 0;
  return <HeroScene trimBefore={start} />;
};

// ------------------------------------------------------------------------------------------------ results / safety / cost / limits / outro
/** [mean, low, high] from sim/evaluate.py: success as a fraction, ablation change in percentage points. */
type Ci = number[];
const ev = evaluation as unknown as {
  seeds: number;
  scenarios: { id: string; results: Record<string, { success: Ci }> }[];
  ablation: { id: string; changePts: Ci }[];
};
const results = (id: string) => {
  const s = ev.scenarios.find((x) => x.id === id);
  if (!s) throw new Error(`evaluation.json has no scenario "${id}"`);
  return s.results;
};
const changePts = (id: string) => {
  const a = ev.ablation.find((x) => x.id === id);
  if (!a) throw new Error(`evaluation.json has no ablation "${id}"`);
  return a.changePts;
};

/** Rounds like Python (half to even) so the numbers match research/evaluation.md: 92.5 -> 92, -7.5 -> -8. */
const roundHalfEven = (x: number) => {
  const r = Math.round(x * 10) / 10;
  const f = Math.floor(r);
  return r - f === 0.5 ? (f % 2 === 0 ? f : f + 1) : Math.round(r);
};
const pct = (v: number) => roundHalfEven(v * 100);

const ROBOTS = [
  { key: "baseline", name: "Standard robot (from the film)", color: colors.red },
  { key: "steelman", name: "Upgraded standard robot*", color: colors.violet },
  { key: "bharat", name: "Bharat-Bot", color: colors.greenBright },
];
const TESTS = [
  { id: "full", name: "Full delivery", sub: "all of it on one 70 m trip" },
  { id: "pothole", name: "Broken road", sub: "potholes and puddles" },
  { id: "dogs", name: "Street dogs", sub: "a pack of three" },
  { id: "theft", name: "Thief", sub: "tries to lift the robot" },
];
const REMOVED: { id: string; name: string; note?: string }[] = [
  { id: "no_dog_freeze", name: "Freezing for street dogs", note: "assumes stillness calms dogs (not yet tested)" },
  { id: "no_alarm", name: "Tamper alarm on the lid", note: "a thief tried on half the streets" },
  { id: "no_perception", name: "Seeing potholes and water" },
  { id: "no_yield", name: "Yielding to traffic" },
  { id: "no_bogie", name: "Rocker-bogie suspension", note: "a plain chassis coped with these holes too" },
];
const BAR = 22;
const LABEL_W = 250;
const RATE_W = 600; // px for 100 %
const LOSS_W = 380; // px for 60 points

/** The 95% confidence range: a thin line with end caps. */
const Whisker: React.FC<{ x0: number; x1: number; opacity: number }> = ({ x0, x1, opacity }) => (
  <div style={{ position: "absolute", left: x0, width: x1 - x0, top: BAR / 2 - 1, height: 2, background: colors.text, opacity,
    filter: "drop-shadow(0 0 2px rgba(7,11,20,0.9))" }}>
    <div style={{ position: "absolute", left: -1, top: -7, width: 2, height: 16, background: colors.text }} />
    <div style={{ position: "absolute", right: -1, top: -7, width: 2, height: 16, background: colors.text }} />
  </div>
);

/** A bar that grows from the baseline; its whisker and the value at the tip land with it. */
const CiBar: React.FC<{ ci: Ci; pxPerUnit: number; color: string; delay: number; label: string; extra?: string; baseline?: boolean }> = ({
  ci, pxPerUnit, color, delay, label, extra, baseline,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const grow = interpolate(frame, [delay, delay + 0.8 * fps], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const land = interpolate(frame, [delay + 0.55 * fps, delay + 0.9 * fps], [0, 1], clamp);
  const [m, lo, hi] = ci.map((v) => v * pxPerUnit);
  return (
    <div style={{ position: "relative", height: BAR }}>
      {baseline ? <div style={{ position: "absolute", left: 0, top: -4, width: 1, height: BAR + 8, background: "rgba(255,255,255,0.35)" }} /> : null}
      <div style={{ position: "absolute", left: 0, top: 0, height: BAR, width: Math.max(m, 4) * grow, background: color, borderRadius: "0 4px 4px 0" }} />
      {hi - lo >= 1 ? <Whisker x0={lo} x1={hi} opacity={land} /> : null}
      <div style={{ position: "absolute", left: Math.max(m, hi) + 14, top: -6, height: BAR + 12, display: "flex", alignItems: "center", gap: 12,
        whiteSpace: "nowrap", opacity: land }}>
        <span style={{ fontFamily: fonts.mono, fontSize: 26, fontWeight: 700 }}>{label}</span>
        {extra ? <span style={{ fontFamily: fonts.mono, fontSize: 20, color: colors.muted }}>{extra}</span> : null}
      </div>
    </div>
  );
};

export const ResultsScene: React.FC = () => {
  const { fps } = useVideoConfig();
  const k = useInOut(12, 12);
  const at = (s: number) => Math.round(s * fps);
  const removed = REMOVED.map((f) => ({ ...f, c: changePts(f.id) })).sort((a, b) => a.c[0] - b.c[0]);
  return (
    <AbsoluteFill>
      <CardBackground />
      <DesignCanvas>
        <div style={{ position: "absolute", left: 120, top: 60, opacity: k }}>
          <Kicker>{ev.seeds} random streets for every test</Kicker>
          <div style={{ fontSize: 72, fontWeight: 700 }}>Not just one lucky run</div>
        </div>
        <div style={{ ...panel, position: "absolute", left: 120, top: 210, width: 1070, height: 700, padding: "24px 34px", boxSizing: "border-box",
          opacity: k }}>
          <div style={{ fontSize: 26, letterSpacing: 3, color: colors.muted }}>SUCCESS RATE</div>
          <div style={{ display: "flex", gap: 30, marginTop: 8 }}>
            {ROBOTS.map((r) => (
              <div key={r.key} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 26, fontWeight: 600 }}>
                <div style={{ width: 22, height: 22, borderRadius: 4, background: r.color }} />
                {r.name}
              </div>
            ))}
          </div>
          <div style={{ position: "relative", marginTop: 30, display: "flex", flexDirection: "column", gap: 30 }}>
            <div style={{ position: "absolute", left: LABEL_W, top: -12, bottom: -12, width: RATE_W }}>
              {[0, 0.25, 0.5, 0.75, 1].map((p) => (
                <div key={p} style={{ position: "absolute", left: p * RATE_W, top: 0, bottom: 0, width: 1,
                  background: p === 0 ? "rgba(255,255,255,0.35)" : "rgba(255,255,255,0.1)" }}>
                  {p === 0 || p === 0.5 || p === 1 ? (
                    <div style={{ position: "absolute", top: "100%", marginTop: 6, translate: "-50% 0px", fontFamily: fonts.mono, fontSize: 20,
                      color: colors.muted }}>{p * 100}%</div>
                  ) : null}
                </div>
              ))}
            </div>
            {TESTS.map((t, i) => {
              const res = results(t.id);
              return (
                <PopIn key={t.id} delay={at(0.35 + 0.25 * i)}>
                  <div style={{ display: "flex", alignItems: "center", ...(i === 0 ? {
                    background: "rgba(255,255,255,0.05)", borderRadius: 12, margin: "0 -14px", padding: "10px 14px" } : {}) }}>
                    <div style={{ width: LABEL_W }}>
                      <div style={{ fontSize: i === 0 ? 34 : 30, fontWeight: 700, lineHeight: 1.05 }}>{t.name}</div>
                      <div style={{ fontSize: 22, color: colors.muted }}>{t.sub}</div>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6, width: RATE_W }}>
                      {ROBOTS.map((r) => {
                        const ci = res[r.key].success;
                        return (
                          <CiBar key={r.key} ci={ci} pxPerUnit={RATE_W} color={r.color} delay={at(0.45 + 0.25 * i)} label={`${pct(ci[0])}%`}
                            extra={i === 0 ? `${pct(ci[1])}–${pct(ci[2])}` : undefined} />
                        );
                      })}
                    </div>
                  </div>
                </PopIn>
              );
            })}
          </div>
          <div style={{ position: "absolute", left: 34, right: 34, bottom: 20, fontSize: 22, color: colors.muted, lineHeight: 1.4 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ position: "relative", width: 46, height: BAR, translate: "0px -2px" }}><Whisker x0={2} x1={44} opacity={1} /></div>
              Thin line: the range we're 95% sure the true rate is in
            </div>
            <div>* Upgraded: climbs and wades better, has a lid siren and brakes for dogs</div>
          </div>
        </div>
        <div style={{ position: "absolute", left: 1220, top: 210, opacity: k }}>
          <PopIn delay={at(1.4)} style={{ ...panel, width: 580, height: 700, padding: "24px 34px", boxSizing: "border-box" }}>
            <div style={{ fontSize: 26, letterSpacing: 3, color: colors.muted }}>WHICH FEATURE MATTERS MOST?</div>
            <div style={{ fontSize: 28, fontWeight: 600, lineHeight: 1.15, marginTop: 6 }}>Take one away from Bharat-Bot: deliveries lost out of every 100</div>
            <div style={{ marginTop: 24 }}>
              {removed.map((f, i) => (
                <PopIn key={f.id} delay={at(1.8 + 0.15 * i)}>
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 6 }}>{f.name}</div>
                    <CiBar ci={[-f.c[0], -f.c[2], -f.c[1]]} pxPerUnit={LOSS_W / 60} color={colors.saffron} delay={at(1.9 + 0.15 * i)} baseline
                      label={f.c[0] < 0 ? `−${-roundHalfEven(f.c[0])}` : "0"} />
                    {f.note ? <div style={{ fontSize: 22, color: colors.muted, marginTop: 6 }}>{f.note}</div> : null}
                  </div>
                </PopIn>
              ))}
            </div>
          </PopIn>
        </div>
        <div style={{ position: "absolute", left: 120, top: 932, width: 1680, opacity: k }}>
          <PopIn delay={at(3.2)}>
            <div style={{ fontSize: 30, fontWeight: 600 }}>
              A siren on the lid is enough to stop a thief. Dogs and broken, flooded roads are where Bharat-Bot's design wins.
            </div>
            <div style={{ marginTop: 8 }}>
              <SourceChip>sim/evaluate.py · {ev.seeds} random streets per robot and test · 95% intervals (Wilson) · research/evaluation.md</SourceChip>
            </div>
          </PopIn>
        </div>
      </DesignCanvas>
    </AbsoluteFill>
  );
};

const TIERS: [string, string, string, string[]][] = [
  ["1", "AI suggests", colors.violet, ["Detects dogs, cows, potholes, water, people, autos", "Proposes a path and a speed"]],
  ["2", "Safety controller decides", colors.amber, ["Dog within 6 m → stop", "Unknown water → no-go", "Person within 1.2 m → hold", "Link lost > 2 s → hold"]],
  ["3", "Hard-wired cut-offs protect", colors.red, ["Bumper switches · e-stop", "Tilt > 25° cuts the drive", "Battery over-temperature cut-off", "Mechanical lid lock"]],
];

export const SafetyScene: React.FC = () => {
  const { fps } = useVideoConfig();
  const k = useInOut(12, 12);
  return (
    <AbsoluteFill>
      <CardBackground />
      <DesignCanvas>
        <div style={{ position: "absolute", left: 120, top: 80, opacity: k }}>
          <Kicker>Safety architecture</Kicker>
          <div style={{ fontSize: 72, fontWeight: 700 }}>AI suggests. Safety decides. Hardware protects.</div>
          <div style={{ fontSize: 28, color: colors.muted }}>The same rule as GH-01, Sumith Shridhar's greenhouse digital twin</div>
        </div>
        <div style={{ position: "absolute", left: 120, top: 330, display: "flex", gap: 28, opacity: k }}>
          {TIERS.map(([n, t, c, items], i) => (
            <PopIn key={t} delay={Math.round((0.3 + 0.4 * i) * fps)}>
              <div style={{ ...panel, width: 540, minHeight: 470, padding: "26px 30px", borderTop: `10px solid ${c}` }}>
                <div style={{ fontFamily: fonts.mono, fontSize: 30, color: c }}>{n}</div>
                <div style={{ fontSize: 44, fontWeight: 700, marginBottom: 16 }}>{t}</div>
                {items.map((s) => <div key={s} style={{ fontSize: 30, color: colors.text, marginBottom: 10 }}>• {s}</div>)}
              </div>
            </PopIn>
          ))}
        </div>
      </DesignCanvas>
    </AbsoluteFill>
  );
};

const BARS: [string, number][] = [["8 / day", 76], ["15 / day", 41], ["20 / day", 31], ["30 / day", 20]];

export const CostScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const k = useInOut(12, 12);
  const grow = interpolate(frame, [0.5 * fps, 1.8 * fps], [0, 1], clamp);
  const px = (rs: number) => rs * 4.4;
  const barColor = (rs: number) => (rs < 40 ? colors.greenBright : rs <= 60 ? colors.amber : colors.red);
  return (
    <AbsoluteFill>
      <CardBackground />
      <DesignCanvas>
        <div style={{ position: "absolute", left: 120, top: 80, opacity: k }}>
          <Kicker>Honest economics</Kicker>
          <div style={{ fontSize: 72, fontWeight: 700 }}>Can it pay for itself?</div>
        </div>
        <div style={{ position: "absolute", left: 120, top: 300, width: 640, opacity: k }}>
          <div style={{ ...panel, padding: "26px 30px", marginBottom: 22 }}>
            <div style={{ fontSize: 26, color: colors.muted, letterSpacing: 3 }}>PARTS (PAPER BOM)</div>
            <div style={{ fontSize: 64, fontWeight: 700, color: colors.greenBright }}>₹1.4–3.1 lakh</div>
            <div style={{ fontSize: 28 }}>vs ₹8–12 lakh for an imported Starship-class robot</div>
          </div>
          <div style={{ ...panel, padding: "26px 30px" }}>
            <div style={{ fontSize: 34, fontWeight: 700 }}>Wins only when it's busy</div>
            <div style={{ fontSize: 28, color: colors.muted }}>Gated societies · campuses · hospitals · night and monsoon hours, not open streets</div>
          </div>
        </div>
        <div style={{ position: "absolute", left: 860, top: 300, width: 940, height: 620, ...panel, padding: "26px 34px", opacity: k }}>
          <div style={{ fontSize: 26, color: colors.muted, letterSpacing: 3 }}>COST PER DELIVERY (₹2.5 LAKH ROBOT)</div>
          <div style={{ position: "relative", height: 420, marginTop: 60 }}>
            <div style={{ position: "absolute", left: 0, right: 0, bottom: px(40), height: px(40), background: "rgba(245,179,1,0.14)",
              borderTop: `2px dashed ${colors.amber}`, borderBottom: `2px dashed ${colors.amber}` }} />
            <div style={{ position: "absolute", right: 0, bottom: px(80) + 6, fontSize: 24, color: colors.amber }}>courier ₹40–80</div>
            <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, display: "flex", alignItems: "flex-end", gap: 50, paddingLeft: 30 }}>
              {BARS.map(([lbl, rs]) => (
                <div key={lbl} style={{ width: 150, textAlign: "center" }}>
                  <div style={{ fontFamily: fonts.mono, fontSize: 30, fontWeight: 700, marginBottom: 6 }}>₹{rs}</div>
                  <div style={{ height: px(rs) * grow, background: barColor(rs), borderRadius: "10px 10px 0 0" }} />
                </div>
              ))}
            </div>
          </div>
          <div style={{ display: "flex", gap: 50, paddingLeft: 30, marginTop: 10 }}>
            {BARS.map(([lbl]) => <div key={lbl} style={{ width: 150, textAlign: "center", fontSize: 26, color: colors.muted }}>{lbl}</div>)}
          </div>
          <div style={{ marginTop: 14 }}><SourceChip>estimates · 3-yr life · 1 operator per 6 robots · research §3.5</SourceChip></div>
        </div>
      </DesignCanvas>
    </AbsoluteFill>
  );
};

const LIMITS = [
  "No verified open-street sidewalk-robot pilot exists in India yet",
  "Ultrasonic dog repellers show no proven effect, so Bharat-Bot doesn't rely on them",
  "No robot maker publishes a wading depth; knee-deep floods are a no-go",
  "Packs of 3+ dogs or dense crowds: hold and call a remote operator",
  "All these numbers come from simulated streets, not real ones",
];

export const LimitsScene: React.FC = () => {
  const { fps } = useVideoConfig();
  const k = useInOut(12, 12);
  return (
    <AbsoluteFill>
      <CardBackground />
      <DesignCanvas>
        <div style={{ position: "absolute", left: 120, top: 80, opacity: k }}>
          <Kicker color={colors.amber}>Honest limits</Kicker>
          <div style={{ fontSize: 72, fontWeight: 700 }}>What we don't know yet</div>
        </div>
        <div style={{ position: "absolute", left: 120, top: 280, width: 1680, opacity: k }}>
          {LIMITS.map((s, i) => (
            <PopIn key={s} delay={Math.round((0.3 + 0.3 * i) * fps)}>
              <div style={{ fontSize: 38, marginBottom: 20 }}><span style={{ color: colors.amber }}>?</span> {s}</div>
            </PopIn>
          ))}
          <PopIn delay={Math.round(2.2 * fps)}>
            <div style={{ ...panel, marginTop: 26, padding: "22px 28px", borderLeft: `8px solid ${colors.greenBright}` }}>
              <div style={{ fontSize: 26, letterSpacing: 3, color: colors.greenBright }}>NEXT REAL-WORLD TEST</div>
              <div style={{ fontSize: 36, fontWeight: 700 }}>A one-week pilot in one gated community: success rate, interventions per km, dog encounters, tamper events, ₹ per delivery</div>
            </div>
          </PopIn>
        </div>
      </DesignCanvas>
    </AbsoluteFill>
  );
};

export const OutroScene: React.FC = () => {
  const k = useInOut(14, 20);
  return (
    <AbsoluteFill>
      <CardBackground />
      <DesignCanvas>
        <div style={{ position: "absolute", left: 0, right: 0, top: 250, textAlign: "center", opacity: k }}>
          <div style={{ fontSize: 140, fontWeight: 700 }}>
            <span style={{ color: colors.saffron }}>BHARAT</span>-<span style={{ color: colors.greenBright }}>BOT</span>
          </div>
          <div style={{ fontSize: 40, color: colors.muted }}>Ready for potholes, street dogs, cows and thieves</div>
          <div style={{ fontSize: 30, color: colors.muted, marginTop: 40, lineHeight: 1.6 }}>
            Simulation: Python + Blender 5.2 (EEVEE) · Film: Remotion<br />
            Textures: Poly Haven (CC0) · Dogs and cow: Quaternius (CC0) · Music: synthesised tanpura drone<br />
            Research: 66 sources, see research/india-delivery-robots.md · Inspired by GH-01 by Sumith Shridhar
          </div>
        </div>
      </DesignCanvas>
    </AbsoluteFill>
  );
};
