import { Circle } from "@remotion/shapes";
import { evolvePath } from "@remotion/paths";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts } from "./theme";

export type MainProps = {
  eyebrow: string;
  title: string;
  subtitle: string;
  tagline: string;
};

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const UNDERLINE_PATH = "M 0 8 L 760 8";
const RADAR_CENTER = { x: 1480, y: 540 };
const RADAR_RINGS = 3;
const RADAR_PERIOD = 60;

/** Placeholder title card. Replace the copy via defaultProps in Root.tsx or `--props`. */
export const Main: React.FC<MainProps> = ({ eyebrow, title, subtitle, tagline }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 12], [0, 1], clamp);
  const fadeOut = interpolate(frame, [durationInFrames - 15, durationInFrames - 1], [1, 0], clamp);

  const eyebrowIn = spring({ frame: frame - 4, fps, config: { damping: 200 } });
  const titleIn = spring({ frame: frame - 10, fps, config: { damping: 200 } });
  const subtitleIn = spring({ frame: frame - 34, fps, config: { damping: 200 } });
  const taglineIn = spring({ frame: frame - 52, fps, config: { damping: 200 } });

  const underline = evolvePath(
    interpolate(frame, [26, 70], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) }),
    UNDERLINE_PATH,
  );

  // Tricolour strip along the bottom edge grows from the left.
  const strip = interpolate(frame, [0, 36], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${colors.bg} 0%, #12213f 58%, ${colors.bg} 100%)`,
        fontFamily: fonts.display,
        color: colors.text,
        opacity: fadeIn * fadeOut,
      }}
    >
      {/* faint blueprint grid */}
      <AbsoluteFill
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.045) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,0.045) 2px, transparent 2px)",
          backgroundSize: "96px 96px",
        }}
      />

      {/* sensor "radar" pings around the robot */}
      {Array.from({ length: RADAR_RINGS }, (_, i) => {
        const progress = ((frame + i * (RADAR_PERIOD / RADAR_RINGS)) % RADAR_PERIOD) / RADAR_PERIOD;
        const radius = 60 + progress * 420;
        const size = radius * 2 + 8;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: RADAR_CENTER.x - size / 2,
              top: RADAR_CENTER.y - size / 2,
              opacity: (1 - progress) * 0.5 * fadeIn,
            }}
          >
            <Circle radius={radius} fill="none" stroke={colors.saffron} strokeWidth={4} />
          </div>
        );
      })}
      <div
        style={{
          position: "absolute",
          left: RADAR_CENTER.x - 46,
          top: RADAR_CENTER.y - 46,
          width: 92,
          height: 92,
          borderRadius: 24,
          background: colors.saffron,
          border: `8px solid ${colors.white}`,
          boxShadow: "0 0 60px rgba(255, 153, 51, 0.55)",
        }}
      />

      {/* copy */}
      <div style={{ position: "absolute", left: 140, top: 270 }}>
        <div
          style={{
            fontSize: 34,
            letterSpacing: 10,
            color: colors.saffron,
            fontWeight: 600,
            opacity: eyebrowIn,
            translate: `0px ${(1 - eyebrowIn) * 24}px`,
          }}
        >
          {eyebrow}
        </div>
        <div
          style={{
            fontSize: 210,
            fontWeight: 700,
            lineHeight: 1.05,
            opacity: titleIn,
            translate: `0px ${(1 - titleIn) * 60}px`,
          }}
        >
          {title}
        </div>
        <svg width={760} height={16} viewBox="0 0 760 16" style={{ display: "block", marginTop: 6 }}>
          <path
            d={UNDERLINE_PATH}
            fill="none"
            stroke={colors.saffron}
            strokeWidth={8}
            strokeLinecap="round"
            strokeDasharray={underline.strokeDasharray}
            strokeDashoffset={underline.strokeDashoffset}
          />
        </svg>
        <div
          style={{
            marginTop: 36,
            fontSize: 58,
            fontWeight: 500,
            maxWidth: 1000,
            lineHeight: 1.15,
            textWrap: "balance",
            opacity: subtitleIn,
            translate: `0px ${(1 - subtitleIn) * 30}px`,
          }}
        >
          {subtitle}
        </div>
        <div
          style={{
            marginTop: 28,
            fontSize: 34,
            color: colors.muted,
            opacity: taglineIn,
            translate: `0px ${(1 - taglineIn) * 20}px`,
          }}
        >
          {tagline}
        </div>
      </div>

      <div style={{ position: "absolute", left: 0, bottom: 0, width: "100%", height: 14, display: "flex" }}>
        {[colors.saffron, colors.white, colors.green].map((color) => (
          <div key={color} style={{ width: `${strip * (100 / 3)}%`, height: "100%", background: color }} />
        ))}
      </div>
    </AbsoluteFill>
  );
};
