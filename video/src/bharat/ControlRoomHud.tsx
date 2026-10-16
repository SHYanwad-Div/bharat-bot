import React, { useMemo } from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { eventsUntil, frameAt, type SimTelemetry } from "./data";
import { colors, fonts, levelColors, modeColor, panel } from "./theme";
import { DesignCanvas } from "./ui";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const CHAIN = ["SENSE", "AI", "SAFETY", "ACT", "OK"] as const;
const STRIP = { x: 640, y: 944, w: 1240, h: 96 };

type Props = { tel: SimTelemetry; trimBefore?: number; playbackRate?: number };

/** Frame-synced HUD for the India-adapted run: decision chain, control-room log, speed/state and a route strip. */
export const ControlRoomHud: React.FC<Props> = ({ tel, trimBefore = 0, playbackRate = 1 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const seconds = (trimBefore + frame * playbackRate) / fps;
  const cur = frameAt(tel, seconds);
  const idx = cur.f;
  const past = eventsUntil(tel, seconds);
  const latest = past[past.length - 1];
  const sinceLatest = latest ? seconds - latest.frame / tel.fps : 99;
  const active = sinceLatest < 2.2 ? (latest.level === "INFO" ? "SENSE" : latest.level) : null;
  const geo = useMemo(() => {
    const m = tel.map;
    if (!m) return null;
    const sx = (x: number) => STRIP.x + ((x - m.xMin) / (m.xMax - m.xMin)) * STRIP.w;
    const sy = (y: number) => STRIP.y + STRIP.h / 2 - (y / 6.8) * (STRIP.h / 2);
    const dist = [0];
    for (let i = 1; i < tel.frames.length; i++) {
      const a = tel.frames[i - 1];
      const b = tel.frames[i];
      dist.push(dist[i - 1] + Math.hypot(b.x - a.x, b.y - a.y));
    }
    const route = m.route.x.map((x, i) => `${sx(x).toFixed(1)},${sy(m.route.y[i]).toFixed(1)}`).join(" ");
    return { m, sx, sy, dist, route };
  }, [tel]);
  const recDot = 0.45 + 0.55 * (0.5 + 0.5 * Math.sin(frame / 5));
  const ring = 2 * Math.PI * 64;
  const stateCol = modeColor(cur.state);
  const remaining = geo ? geo.dist[geo.dist.length - 1] - geo.dist[idx] : 0;
  const rows = past.slice(-5).reverse();
  return (
    <DesignCanvas>
      {/* badge + clock */}
      <div style={{ ...panel, position: "absolute", left: 40, top: 30, padding: "12px 22px", display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ width: 14, height: 14, borderRadius: 7, background: colors.red, opacity: recDot }} />
        <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: 2 }}>BHARAT-BOT · LIVE SIM</div>
        <div style={{ fontFamily: fonts.mono, fontSize: 24, color: colors.saffron }}>{seconds.toFixed(1).padStart(5, "0")} s</div>
      </div>
      {/* decision chain */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 34, display: "flex", justifyContent: "center", gap: 8 }}>
        {CHAIN.map((lv, i) => {
          const lit = active === lv || (active === "ALARM" && lv === "OK");
          const label = active === "ALARM" && lv === "OK" ? "ALARM" : lv;
          const col = levelColors[label];
          return (
            <React.Fragment key={lv}>
              <div style={{ padding: "9px 16px", borderRadius: 10, fontSize: 21, fontWeight: 700, letterSpacing: 2,
                background: lit ? col : "rgba(8,14,26,0.72)", color: lit ? "#08101c" : colors.muted,
                boxShadow: lit ? `0 0 22px ${col}` : "none", border: "1.5px solid rgba(255,255,255,0.14)" }}>
                {label === "ACT" ? "ACTUATORS" : label}
              </div>
              {i < CHAIN.length - 1 ? <div style={{ alignSelf: "center", color: colors.muted, fontSize: 22 }}>›</div> : null}
            </React.Fragment>
          );
        })}
      </div>
      {/* control-room log */}
      <div style={{ ...panel, position: "absolute", right: 40, top: 110, width: 500, padding: "14px 16px 10px" }}>
        <div style={{ fontSize: 19, fontWeight: 700, letterSpacing: 3, color: colors.muted }}>CONTROL ROOM</div>
        <div style={{ fontSize: 17, color: colors.muted, marginBottom: 8 }}>AI suggests · safety decides · hardware protects</div>
        {rows.map((e, i) => {
          const age = seconds - e.frame / tel.fps;
          const k = i === 0 ? spring({ frame: age * fps, fps, config: { damping: 200 }, durationInFrames: Math.round(0.4 * fps) }) : 1;
          const col = levelColors[e.level] ?? colors.muted;
          return (
            <div key={`${e.frame}-${e.label}`} style={{ display: "grid", gridTemplateColumns: "62px 92px 1fr", gap: 8, padding: "7px 6px",
              borderRadius: 8, marginBottom: 4, opacity: (i === 0 ? k : 1) * (1 - i * 0.12), translate: `${(1 - k) * 40}px 0px`,
              background: e.level === "ALARM" ? "rgba(239,68,68,0.18)" : "rgba(255,255,255,0.035)" }}>
              <div style={{ fontFamily: fonts.mono, fontSize: 17, color: colors.muted }}>{(e.frame / tel.fps).toFixed(1)}s</div>
              <div style={{ fontFamily: fonts.mono, fontSize: 17, fontWeight: 700, color: col }}>{e.level}</div>
              <div>
                <div style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.1 }}>{e.label}</div>
                <div style={{ fontSize: 17, color: colors.muted, lineHeight: 1.15 }}>{e.detail}</div>
              </div>
            </div>
          );
        })}
      </div>
      {/* speed + state */}
      <div style={{ ...panel, position: "absolute", left: 40, top: 846, width: 560, height: 194, padding: 14, display: "flex", gap: 18, alignItems: "center" }}>
        <svg width={160} height={160} viewBox="0 0 160 160">
          <circle cx={80} cy={80} r={64} fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth={12}
            strokeDasharray={`${ring * 0.75} ${ring}`} transform="rotate(135 80 80)" strokeLinecap="round" />
          <circle cx={80} cy={80} r={64} fill="none" stroke={stateCol} strokeWidth={12} strokeLinecap="round"
            strokeDasharray={`${Math.max(0.5, ring * 0.75 * Math.min(1, cur.speed / 2))} ${ring}`} transform="rotate(135 80 80)" />
          <text x={80} y={88} textAnchor="middle" fontFamily={fonts.mono} fontSize={38} fontWeight={700} fill={colors.text}>{cur.speed.toFixed(1)}</text>
          <text x={80} y={114} textAnchor="middle" fontSize={18} fill={colors.muted}>m/s</text>
        </svg>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 18, letterSpacing: 3, color: colors.muted }}>STATE</div>
          <div style={{ fontSize: 40, fontWeight: 700, color: stateCol, lineHeight: 1.05 }}>{cur.state}</div>
          <div style={{ display: "flex", gap: 22, marginTop: 10, fontFamily: fonts.mono, fontSize: 20, color: colors.muted }}>
            <span>TO GATE <b style={{ color: colors.text }}>{Math.max(0, remaining).toFixed(0)} m</b></span>
            <span>BATT <b style={{ color: colors.text }}>{Math.round(cur.battery * 100)}%</b></span>
          </div>
        </div>
      </div>
      {/* route strip */}
      {geo ? (
        <div style={{ ...panel, position: "absolute", left: STRIP.x - 16, top: STRIP.y - 26, width: STRIP.w + 32, height: STRIP.h + 40 }} />
      ) : null}
      {geo ? (
        <svg style={{ position: "absolute", left: 0, top: 0 }} width={1920} height={1080}>
          <rect x={STRIP.x} y={geo.sy(3.5)} width={STRIP.w} height={geo.sy(-3.5) - geo.sy(3.5)} fill="rgba(70,76,88,0.9)" rx={4} />
          <line x1={STRIP.x} x2={STRIP.x + STRIP.w} y1={geo.sy(0)} y2={geo.sy(0)} stroke="rgba(255,255,255,0.35)" strokeDasharray="10 14" strokeWidth={2} />
          {geo.m.potholes.map((p) => (
            <circle key={`${p.x}-${p.y}`} cx={geo.sx(p.x)} cy={geo.sy(p.y)} r={3 + p.r * 4}
              fill={p.water > 0 ? "rgba(56,189,248,0.85)" : "rgba(239,68,68,0.85)"} />
          ))}
          {geo.m.places.map((pl) => (
            <g key={pl.kind}>
              <circle cx={geo.sx(pl.x)} cy={geo.sy(pl.y)} r={6} fill={pl.kind === "gate" ? colors.greenBright : colors.amber} />
              <text x={geo.sx(pl.x)} y={STRIP.y - 6} textAnchor="middle" fontSize={15} fontWeight={700} fill={colors.muted}
                fontFamily={fonts.display} letterSpacing={1}>
                {{ start: "BIRYANI HOUSE", gate: "GATE", dogs: "DOGS", cow: "COW", thief: "THIEF", breaker: "BREAKER" }[pl.kind] ?? pl.kind.toUpperCase()}
              </text>
            </g>
          ))}
          <polyline points={geo.route} fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth={3} />
          <polyline points={tel.frames.slice(0, idx + 1).filter((_, i) => i % 3 === 0 || i === idx)
            .map((f) => `${geo.sx(f.x).toFixed(1)},${geo.sy(f.y).toFixed(1)}`).join(" ")}
            fill="none" stroke={colors.saffron} strokeWidth={4} strokeLinecap="round" />
          <circle cx={geo.sx(cur.x)} cy={geo.sy(cur.y)} r={9} fill="#ffffff" stroke={stateCol} strokeWidth={4} />
        </svg>
      ) : null}
      <div style={{ position: "absolute", left: STRIP.x, top: STRIP.y + STRIP.h + 2, fontSize: 15, color: colors.muted,
        opacity: interpolate(frame, [0, 20], [0, 1], clamp) }}>
        ROUTE · red = pothole · blue = water
      </div>
    </DesignCanvas>
  );
};
