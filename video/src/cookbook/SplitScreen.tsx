import { Video } from "@remotion/media";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { colors, fonts } from "../theme";

export type SplitScreenProps = {
  leftClip: string;
  rightClip: string;
  leftLabel: string;
  rightLabel: string;
  /** Start offset into each clip, in composition frames (same unit as `trimBefore`). */
  leftTrimBefore?: number;
  rightTrimBefore?: number;
};

const GAP = 48;
const PANEL_WIDTH = (1920 - 3 * GAP) / 2; // 888
const PANEL_HEIGHT = Math.round((PANEL_WIDTH * 9) / 16); // 16:9 panels
const LABEL_HEIGHT = 84; // 56px label + 14px margin + line spacing
const PANEL_TOP = Math.round((1080 - LABEL_HEIGHT - PANEL_HEIGHT) / 2); // vertically centred block

const Panel: React.FC<{
  src: string;
  label: string;
  accent: string;
  left: number;
  delay: number;
  trimBefore: number;
}> = ({ src, label, accent, left, delay, trimBefore }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame: frame - delay, fps, config: { damping: 200 } });

  return (
    <div
      style={{
        position: "absolute",
        left,
        top: PANEL_TOP,
        width: PANEL_WIDTH,
        opacity: enter,
        translate: `0px ${(1 - enter) * 50}px`,
      }}
    >
      <div style={{ fontFamily: fonts.display, fontSize: 56, fontWeight: 700, color: accent, marginBottom: 14 }}>{label}</div>
      <div
        style={{
          width: PANEL_WIDTH,
          height: PANEL_HEIGHT,
          borderRadius: 18,
          overflow: "hidden",
          border: `6px solid ${accent}`,
          background: "#000",
        }}
      >
        <Video
          src={staticFile(src)}
          trimBefore={trimBefore}
          premountFor={fps}
          objectFit="cover"
          muted
          style={{ width: "100%", height: "100%" }}
        />
      </div>
    </div>
  );
};

/** Two clips side by side, each shown whole (16:9 panels), with labels and a "VS" badge. */
export const SplitScreen: React.FC<SplitScreenProps> = ({
  leftClip,
  rightClip,
  leftLabel,
  rightLabel,
  leftTrimBefore = 0,
  rightTrimBefore = 0,
}) => {
  return (
    <AbsoluteFill style={{ background: colors.bg }}>
      <Panel src={leftClip} label={leftLabel} accent={colors.muted} left={GAP} delay={0} trimBefore={leftTrimBefore} />
      <Panel src={rightClip} label={rightLabel} accent={colors.saffron} left={2 * GAP + PANEL_WIDTH} delay={8} trimBefore={rightTrimBefore} />
      <div
        style={{
          position: "absolute",
          left: 960 - 44,
          top: PANEL_TOP + LABEL_HEIGHT + PANEL_HEIGHT / 2 - 44,
          width: 88,
          height: 88,
          borderRadius: 44,
          background: colors.bg,
          border: `4px solid ${colors.white}`,
          color: colors.white,
          fontFamily: fonts.display,
          fontWeight: 700,
          fontSize: 40,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        VS
      </div>
    </AbsoluteFill>
  );
};

/**
 * A/B wipe: both clips are full frame; the divider slides and `clip-path`
 * reveals the left clip. Good for "before / after" and "US robot vs Bharat-Bot".
 */
export const SplitWipe: React.FC<SplitScreenProps> = ({
  leftClip,
  rightClip,
  leftLabel,
  rightLabel,
  leftTrimBefore = 0,
  rightTrimBefore = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, durationInFrames } = useVideoConfig();

  // 0 -> 100% left, then sweeps to the middle and back to 70/30 so both clips get screen time.
  const split = interpolate(frame, [0, durationInFrames * 0.35, durationInFrames * 0.7, durationInFrames], [width, width * 0.5, width * 0.5, width * 0.7], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Video src={staticFile(rightClip)} trimBefore={rightTrimBefore} premountFor={fps} objectFit="cover" muted style={{ width: "100%", height: "100%" }} />
      <AbsoluteFill style={{ clipPath: `inset(0 ${width - split}px 0 0)` }}>
        <Video src={staticFile(leftClip)} trimBefore={leftTrimBefore} premountFor={fps} objectFit="cover" muted style={{ width: "100%", height: "100%" }} />
      </AbsoluteFill>
      <div style={{ position: "absolute", left: split - 3, top: 0, width: 6, height: "100%", background: colors.saffron }} />
      <div style={{ position: "absolute", left: 48, top: 40, fontFamily: fonts.display, fontSize: 56, fontWeight: 700, color: colors.white, textShadow: "0 2px 12px #000" }}>{leftLabel}</div>
      <div style={{ position: "absolute", right: 48, top: 40, fontFamily: fonts.display, fontSize: 56, fontWeight: 700, color: colors.saffron, textShadow: "0 2px 12px #000" }}>{rightLabel}</div>
    </AbsoluteFill>
  );
};
