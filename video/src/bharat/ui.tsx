import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts, panel } from "./theme";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** 0 -> 1 -> 0 envelope over the enclosing Sequence (fade in, hold, fade out). */
export const useInOut = (inFrames = 12, outFrames = 12): number => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return Math.min(
    interpolate(frame, [0, inFrames], [0, 1], { ...clamp, easing: Easing.bezier(0.16, 1, 0.3, 1) }),
    interpolate(frame, [durationInFrames - outFrames, durationInFrames], [1, 0], clamp),
  );
};

/** Lays children out on a 1920x1080 design canvas scaled to the composition size. */
export const DesignCanvas: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { width } = useVideoConfig();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, scale: String(width / 1920),
        transformOrigin: "0 0", fontFamily: fonts.display, color: colors.text }}>
        {children}
      </div>
    </AbsoluteFill>
  );
};

/** Big caption card that fades and rises in, then fades out. */
export const CaptionCard: React.FC<{ text: string; accent?: string; top?: number; maxWidth?: number }> = ({
  text, accent = colors.saffron, top = 96, maxWidth = 900,
}) => {
  const k = useInOut(10, 10);
  return (
    <DesignCanvas>
      <div style={{ position: "absolute", left: 0, right: 0, top, display: "flex", justifyContent: "center" }}>
        <div style={{ ...panel, maxWidth, padding: "16px 30px 16px 26px", borderLeft: `8px solid ${accent}`, opacity: k,
          translate: `0px ${(1 - k) * 18}px` }}>
          <div style={{ fontSize: 42, fontWeight: 700, lineHeight: 1.12 }}>{text}</div>
        </div>
      </div>
    </DesignCanvas>
  );
};

/** Small "source" chip so every number on screen can be traced. */
export const SourceChip: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <span style={{ fontFamily: fonts.mono, fontSize: 18, color: colors.muted, border: "1px solid rgba(255,255,255,0.2)",
    borderRadius: 8, padding: "3px 10px", whiteSpace: "nowrap", ...style }}>
    {children}
  </span>
);

/** Dark title-card background with a faint street grid and a tricolour edge. */
export const CardBackground: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 30% 30%, #142238 0%, #0b1220 55%, #070b14 100%)" }}>
      <AbsoluteFill style={{ opacity: 0.18, backgroundImage:
        "linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px)",
        backgroundSize: "64px 64px", backgroundPosition: `${frame * 0.6}px 0px` }} />
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 10, display: "flex" }}>
        <div style={{ flex: 1, background: colors.saffron }} />
        <div style={{ flex: 1, background: "#ffffff" }} />
        <div style={{ flex: 1, background: colors.green }} />
      </div>
    </AbsoluteFill>
  );
};

/** Pops in with a spring after `delay` frames (for list items and cards). */
export const PopIn: React.FC<{ delay: number; children: React.ReactNode; style?: React.CSSProperties }> = ({ delay, children, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const k = spring({ frame: frame - delay, fps, config: { damping: 200 }, durationInFrames: Math.round(0.6 * fps) });
  return <div style={{ opacity: k, translate: `0px ${(1 - k) * 26}px`, ...style }}>{children}</div>;
};

export const Kicker: React.FC<{ children: React.ReactNode; color?: string }> = ({ children, color = colors.saffron }) => (
  <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: 6, color, textTransform: "uppercase" }}>{children}</div>
);
