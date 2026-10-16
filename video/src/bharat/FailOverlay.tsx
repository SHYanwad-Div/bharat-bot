import { Audio } from "@remotion/media";
import React from "react";
import { AbsoluteFill, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { frameAt, type SimTelemetry } from "./data";
import { colors, fonts, modeColor, panel } from "./theme";
import { DesignCanvas } from "./ui";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

type Props = {
  tel: SimTelemetry;
  trimBefore: number;
  playbackRate: number;
  stamp: string;
  why: string;
  scenario: string;
};

/** Overlay for a baseline (US-style) robot clip: label, live state, and a red stamp when the sim says it failed. */
export const FailOverlay: React.FC<Props> = ({ tel, trimBefore, playbackRate, stamp, why, scenario }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const seconds = (trimBefore + frame * playbackRate) / fps;
  const cur = frameAt(tel, seconds);
  const failEvent = tel.events.find((e) => e.level === "ALARM");
  const failAt = failEvent ? Math.round(((failEvent.frame / tel.fps) * fps - trimBefore) / playbackRate) : 10_000;
  const k = spring({ frame: frame - failAt, fps, config: { damping: 14, stiffness: 160 }, durationInFrames: Math.round(0.7 * fps) });
  const shown = frame >= failAt;
  const tint = shown ? interpolate(frame - failAt, [0, 6, 30], [0, 0.35, 0.18], clamp) : 0;
  return (
    <>
      <AbsoluteFill style={{ boxShadow: `inset 0 0 220px rgba(239,68,68,${tint})` }} />
      <DesignCanvas>
        <div style={{ ...panel, position: "absolute", left: 40, top: 30, padding: "14px 22px" }}>
          <div style={{ fontSize: 20, letterSpacing: 4, color: colors.muted }}>{scenario}</div>
          <div style={{ fontSize: 34, fontWeight: 700 }}>Standard sidewalk robot</div>
          <div style={{ fontSize: 20, color: colors.muted }}>18 cm wheels · no suspension · built for smooth US sidewalks</div>
        </div>
        <div style={{ ...panel, position: "absolute", left: 40, bottom: 40, padding: "12px 20px", display: "flex", gap: 20, alignItems: "baseline" }}>
          <span style={{ fontSize: 18, letterSpacing: 3, color: colors.muted }}>STATE</span>
          <span style={{ fontSize: 36, fontWeight: 700, color: modeColor(cur.state) }}>{cur.state}</span>
          <span style={{ fontFamily: fonts.mono, fontSize: 24 }}>{cur.speed.toFixed(1)} m/s</span>
        </div>
        {shown ? (
          <>
            <div style={{ position: "absolute", left: 0, right: 0, top: 150, display: "flex", justifyContent: "center" }}>
              <div style={{ border: `10px solid ${colors.red}`, color: colors.red, fontSize: 128, fontWeight: 700, letterSpacing: 10,
                padding: "0px 40px", borderRadius: 18, rotate: "-7deg", scale: String(2 - k), opacity: Math.min(1, k * 1.4),
                background: "rgba(10,10,14,0.35)", textShadow: "0 0 30px rgba(239,68,68,0.6)" }}>
                {stamp}
              </div>
            </div>
            <div style={{ position: "absolute", left: 0, right: 0, bottom: 130, display: "flex", justifyContent: "center",
              opacity: interpolate(frame - failAt, [8, 20], [0, 1], clamp) }}>
              <div style={{ ...panel, padding: "14px 28px", borderLeft: `8px solid ${colors.red}`, maxWidth: 1100 }}>
                <div style={{ fontSize: 38, fontWeight: 700 }}>{why}</div>
              </div>
            </div>
          </>
        ) : null}
      </DesignCanvas>
      {failEvent ? (
        <Sequence from={failAt} durationInFrames={Math.round(1.2 * fps)} premountFor={fps}>
          <Audio src={staticFile("audio/fail.wav")} volume={0.55} />
        </Sequence>
      ) : null}
    </>
  );
};
