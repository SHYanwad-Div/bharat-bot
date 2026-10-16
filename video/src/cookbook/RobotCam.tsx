import { Video } from "@remotion/media";
import { scanlines } from "@remotion/effects/scanlines";
import { vignette } from "@remotion/effects/vignette";
import { AbsoluteFill, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts } from "../theme";

/**
 * "Robot POV" look for a Blender clip: vignette + scrolling scanlines applied
 * directly to <Video> through its `effects` prop. Effects use WebGL2; they render
 * fine with the default GL backend on this laptop. If one ever comes out black or
 * flat, render with `--gl=angle` (or Config.setChromiumOpenGlRenderer("angle")).
 */
export const RobotCam: React.FC<{ clip: string; label: string }> = ({ clip, label }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Video
        src={staticFile(clip)}
        premountFor={fps}
        objectFit="cover"
        muted
        style={{ width: "100%", height: "100%" }}
        effects={[vignette({ amount: 0.75 }), scanlines({ amount: 0.2, spacing: 4, offset: frame * 0.5 })]}
      />
      <div
        style={{
          position: "absolute",
          left: 48,
          bottom: 40,
          display: "flex",
          alignItems: "center",
          gap: 16,
          fontFamily: fonts.mono,
          fontSize: 34,
          color: colors.text,
          textShadow: "0 2px 8px #000",
        }}
      >
        <div style={{ width: 20, height: 20, borderRadius: 10, background: colors.red, opacity: 0.5 + 0.5 * Math.sin(frame / 6) ** 2 }} />
        REC · {label}
      </div>
    </AbsoluteFill>
  );
};
