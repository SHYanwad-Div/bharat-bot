import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts } from "../theme";

export type LowerThirdProps = {
  title: string;
  subtitle?: string;
  accent?: string;
};

/**
 * Wrap in a <Sequence from={..} durationInFrames={..}> (or give it timing
 * through its parent). Inside a Sequence, useCurrentFrame() starts at 0 and
 * useVideoConfig().durationInFrames is the Sequence length, which is what the
 * enter / exit animation below keys off.
 */
export const LowerThird: React.FC<LowerThirdProps> = ({ title, subtitle, accent = colors.saffron }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 200 }, durationInFrames: Math.round(0.6 * fps) });
  const exit = interpolate(frame, [durationInFrames - 12, durationInFrames - 1], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const s = width / 1920;

  return (
    <div
      style={{
        position: "absolute",
        left: 80 * s,
        bottom: 300 * s,
        display: "flex",
        alignItems: "stretch",
        gap: 20 * s,
        padding: `${18 * s}px ${34 * s}px ${18 * s}px ${22 * s}px`,
        borderRadius: 14 * s,
        background: "rgba(11, 18, 32, 0.86)",
        color: colors.text,
        fontFamily: fonts.display,
        opacity: enter * exit,
        translate: `${(1 - enter) * -80 * s}px 0px`,
        boxShadow: "0 12px 40px rgba(0, 0, 0, 0.45)",
      }}
    >
      <div style={{ width: 8 * s, borderRadius: 4 * s, background: accent }} />
      <div>
        <div style={{ fontSize: 54 * s, fontWeight: 700, lineHeight: 1.05 }}>{title}</div>
        {subtitle ? <div style={{ fontSize: 32 * s, color: colors.muted, fontWeight: 500 }}>{subtitle}</div> : null}
      </div>
    </div>
  );
};
