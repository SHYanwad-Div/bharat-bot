import { useMemo } from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts, severityColors, stateColors } from "../theme";
import {
  activeEventsAt,
  DEFAULT_EVENT_FRAMES,
  telemetryIndexAt,
  type Telemetry,
} from "../lib/telemetry";

export type HudProps = {
  telemetry: Telemetry;
  /**
   * Offset into the source clip (in composition frames, same unit as the
   * clip's `trimBefore`) that sits at frame 0 of the enclosing <Sequence>.
   */
  trimBefore?: number;
  /** Mirror the clip's `playbackRate` so HUD and clip stay in sync. */
  playbackRate?: number;
  /** Full scale of the speed ring in m/s. */
  maxSpeed?: number;
  showMiniMap?: boolean;
  /** Prints the telemetry frame index; compare it with a burned-in frame counter to check sync. */
  debug?: boolean;
};

// The HUD is laid out for 1920x1080 and scaled to whatever the composition is.
const DESIGN_WIDTH = 1920;
const DESIGN_HEIGHT = 1080;

const RING_RADIUS = 78;
const RING_STROKE = 14;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;
const RING_SWEEP = 0.75;

const MAP_WIDTH = 360;
const MAP_HEIGHT = 240;
const MAP_PADDING = 28;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const panelStyle: React.CSSProperties = {
  position: "absolute",
  background: colors.panel,
  border: `2px solid ${colors.panelBorder}`,
  borderRadius: 20,
  boxShadow: "0 12px 40px rgba(0, 0, 0, 0.45)",
};

const formatClock = (seconds: number): string => {
  const whole = Math.max(0, seconds);
  const minutes = Math.floor(whole / 60);
  const rest = whole - minutes * 60;
  return `${String(minutes).padStart(2, "0")}:${rest.toFixed(2).padStart(5, "0")}`;
};

export const Hud: React.FC<HudProps> = ({
  telemetry,
  trimBefore = 0,
  playbackRate = 1,
  maxSpeed = 2,
  showMiniMap = true,
  debug = false,
}) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();

  // Seconds into the *source clip* -> telemetry index. Time based on purpose,
  // so composition fps and sim fps may differ.
  const seconds = (trimBefore + frame * playbackRate) / fps;
  const index = telemetryIndexAt(telemetry, seconds);
  const current = telemetry.frames[index];
  const stateColor = stateColors[current.state] ?? colors.muted;

  // Mini-map geometry is computed once per telemetry file, not per frame.
  const map = useMemo(() => {
    const points = telemetry.frames.filter((f) => f.x !== undefined && f.y !== undefined);
    if (points.length < 2) {
      return null;
    }
    const xs = points.map((p) => p.x as number);
    const ys = points.map((p) => p.y as number);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const scale = Math.min(
      (MAP_WIDTH - 2 * MAP_PADDING) / Math.max(maxX - minX, 0.001),
      (MAP_HEIGHT - 2 * MAP_PADDING) / Math.max(maxY - minY, 0.001),
    );
    const sx = (x: number) => MAP_PADDING + (x - minX) * scale;
    // Sim y points "up" on the map, SVG y points down.
    const sy = (y: number) => MAP_HEIGHT - MAP_PADDING - (y - minY) * scale;
    const projected = telemetry.frames.map((f) => ({ x: sx(f.x ?? minX), y: sy(f.y ?? minY) }));
    return {
      projected,
      route: projected.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" "),
    };
  }, [telemetry]);

  const events = activeEventsAt(telemetry, index);

  const ringValue = RING_CIRCUMFERENCE * RING_SWEEP * Math.min(1, current.speed / maxSpeed);
  const ringTrack = RING_CIRCUMFERENCE * RING_SWEEP;
  const recDot = 0.45 + 0.55 * (0.5 + 0.5 * Math.sin(frame / 5));

  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          width: DESIGN_WIDTH,
          height: DESIGN_HEIGHT,
          transform: `scale(${width / DESIGN_WIDTH})`,
          transformOrigin: "0 0",
          fontFamily: fonts.display,
          color: colors.text,
        }}
      >
        {/* Top-left: source badge + clock */}
        <div style={{ ...panelStyle, left: 48, top: 40, padding: "14px 24px", display: "flex", alignItems: "center", gap: 18 }}>
          <div style={{ width: 16, height: 16, borderRadius: 8, background: colors.red, opacity: recDot }} />
          <div style={{ fontSize: 30, fontWeight: 700, letterSpacing: 2 }}>BHARAT-BOT SIM</div>
          <div style={{ fontSize: 26, color: colors.muted, textTransform: "uppercase" }}>{telemetry.scene}</div>
          <div style={{ fontFamily: fonts.mono, fontSize: 26, color: colors.saffron }}>{formatClock(seconds)}</div>
        </div>

        {debug ? (
          <div style={{ ...panelStyle, left: 760, top: 40, padding: "10px 20px", fontFamily: fonts.mono, fontSize: 26 }}>
            TELEMETRY f={String(index).padStart(3, "0")}
          </div>
        ) : null}

        {/* Bottom-left: speed ring, state, battery */}
        <div style={{ ...panelStyle, left: 48, bottom: 48, width: 660, height: 236, padding: 18, display: "flex", alignItems: "center", gap: 24 }}>
          <svg width={200} height={200} viewBox="0 0 200 200">
            <circle
              cx={100}
              cy={100}
              r={RING_RADIUS}
              fill="none"
              stroke="rgba(255, 255, 255, 0.12)"
              strokeWidth={RING_STROKE}
              strokeLinecap="round"
              strokeDasharray={`${ringTrack} ${RING_CIRCUMFERENCE}`}
              transform="rotate(135 100 100)"
            />
            {ringValue > 1 ? (
              <circle
                cx={100}
                cy={100}
                r={RING_RADIUS}
                fill="none"
                stroke={stateColor}
                strokeWidth={RING_STROKE}
                strokeLinecap="round"
                strokeDasharray={`${ringValue} ${RING_CIRCUMFERENCE}`}
                transform="rotate(135 100 100)"
              />
            ) : null}
            <text x={100} y={110} textAnchor="middle" fontFamily={fonts.mono} fontSize={46} fontWeight={700} fill={colors.text}>
              {current.speed.toFixed(1)}
            </text>
            <text x={100} y={138} textAnchor="middle" fontFamily={fonts.display} fontSize={22} fill={colors.muted}>
              m/s
            </text>
          </svg>

          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ fontSize: 20, color: colors.muted, letterSpacing: 3 }}>STATE</div>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ width: 18, height: 18, borderRadius: 9, background: stateColor }} />
              <div style={{ fontSize: 46, fontWeight: 700, color: stateColor, lineHeight: 1 }}>{current.state}</div>
            </div>
            {current.battery !== undefined ? (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 20, color: colors.muted, letterSpacing: 3 }}>
                  <span>BATTERY</span>
                  <span style={{ fontFamily: fonts.mono, color: colors.text }}>{Math.round(current.battery * 100)}%</span>
                </div>
                <div style={{ marginTop: 6, height: 12, borderRadius: 6, background: "rgba(255, 255, 255, 0.12)" }}>
                  <div
                    style={{
                      width: `${Math.max(0, Math.min(1, current.battery)) * 100}%`,
                      height: "100%",
                      borderRadius: 6,
                      background: current.battery > 0.2 ? colors.greenBright : colors.red,
                    }}
                  />
                </div>
              </div>
            ) : null}
            {current.heading !== undefined ? (
              <div style={{ fontFamily: fonts.mono, fontSize: 22, color: colors.muted }}>
                HDG {current.heading.toFixed(0).padStart(3, " ")}°
                {current.x !== undefined && current.y !== undefined
                  ? `   X ${current.x.toFixed(1)}  Y ${current.y.toFixed(1)}`
                  : ""}
              </div>
            ) : null}
          </div>
        </div>

        {/* Top-right: event toasts */}
        <div style={{ position: "absolute", right: 48, top: 40, width: 620, display: "flex", flexDirection: "column", gap: 14 }}>
          {events.map((event) => {
            const lengthFrames = event.durationFrames ?? DEFAULT_EVENT_FRAMES;
            const elapsed = seconds - event.frame / telemetry.fps;
            const remaining = (event.frame + lengthFrames) / telemetry.fps - seconds;
            const pop = spring({ frame: elapsed * fps, fps, config: { damping: 200 }, durationInFrames: Math.round(0.45 * fps) });
            const fade = interpolate(remaining, [0, 0.3], [0, 1], clamp);
            const color = severityColors[event.severity ?? "info"];
            return (
              <div
                key={`${event.type}-${event.frame}`}
                style={{
                  ...panelStyle,
                  position: "relative",
                  padding: "16px 24px 16px 28px",
                  borderLeft: `8px solid ${color}`,
                  opacity: pop * fade,
                  translate: `${(1 - pop) * 90}px 0px`,
                }}
              >
                <div style={{ fontSize: 18, color, letterSpacing: 3, textTransform: "uppercase" }}>{event.severity ?? "info"} · {event.type.replace(/_/g, " ")}</div>
                <div style={{ fontSize: 38, fontWeight: 600, lineHeight: 1.1 }}>{event.label}</div>
              </div>
            );
          })}
        </div>

        {/* Bottom-right: mini-map */}
        {showMiniMap && map ? (
          <div style={{ ...panelStyle, right: 48, bottom: 48, width: MAP_WIDTH, height: MAP_HEIGHT, overflow: "hidden" }}>
            <svg width={MAP_WIDTH} height={MAP_HEIGHT} viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}>
              <polyline points={map.route} fill="none" stroke="rgba(255, 255, 255, 0.22)" strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" />
              <polyline
                points={map.projected
                  .slice(0, index + 1)
                  .map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`)
                  .join(" ")}
                fill="none"
                stroke={colors.saffron}
                strokeWidth={6}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              {telemetry.events.map((event) => {
                const p = map.projected[Math.min(event.frame, map.projected.length - 1)];
                return <circle key={`${event.type}-${event.frame}`} cx={p.x} cy={p.y} r={7} fill={severityColors[event.severity ?? "info"]} stroke={colors.bg} strokeWidth={2} />;
              })}
              <circle cx={map.projected[index].x} cy={map.projected[index].y} r={11} fill={colors.white} stroke={stateColor} strokeWidth={5} />
            </svg>
          </div>
        ) : null}
      </div>
    </div>
  );
};
