import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts } from "../theme";

/**
 * Stand-in for a rendered Blender clip: a top-down street with a moving robot
 * and a BURNED-IN source frame counter. Render it once to
 * public/_fixtures/test-clip.mp4 (npm run fixtures) and use that file wherever a
 * Blender MP4 would go. Because the frame number is in the picture, you can
 * verify that HUD / telemetry / captions are frame-synced with the clip.
 */
const smooth = (a: number, b: number, x: number): number => {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

export const FixtureClip: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();

  const scroll = (frame * 12) % 200;
  const swerve = 150 * smooth(55, 75, frame) * (1 - smooth(85, 105, frame));
  const potholeX = width * 0.82 - frame * 12 + 600;
  const roadTop = height * 0.28;

  return (
    <AbsoluteFill style={{ background: "#262a31", overflow: "hidden", fontFamily: fonts.mono }}>
      {/* sidewalk + curb */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: roadTop, background: "#7c828c" }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: roadTop - 8, height: 8, background: "#c9ced6" }} />

      {/* scrolling lane dashes */}
      {Array.from({ length: 9 }, (_, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: i * 200 - scroll,
            top: height * 0.62,
            width: 110,
            height: 10,
            background: "rgba(255, 255, 255, 0.55)",
          }}
        />
      ))}

      {/* pothole */}
      <div
        style={{
          position: "absolute",
          left: potholeX,
          top: height * 0.52,
          width: 170,
          height: 96,
          borderRadius: "50%",
          background: "#101216",
          boxShadow: "0 0 0 8px #3a3f48",
        }}
      />

      {/* robot */}
      <div
        style={{
          position: "absolute",
          left: width * 0.3,
          top: height * 0.6 - swerve * 0.9,
          width: 130,
          height: 86,
          borderRadius: 18,
          background: colors.saffron,
          border: "6px solid #fff",
        }}
      >
        <div style={{ position: "absolute", right: 14, top: 22, width: 30, height: 30, borderRadius: 15, background: "#1b2a4a" }} />
      </div>

      {/* burned-in frame counter, placed where HUD overlays do not cover it */}
      <div style={{ position: "absolute", left: 28, top: 128, padding: "12px 20px", background: "rgba(0, 0, 0, 0.7)", color: "#fff", borderRadius: 12 }}>
        <div style={{ fontSize: 54, fontWeight: 700 }}>
          SRC FRAME {String(frame).padStart(3, "0")} / {durationInFrames}
        </div>
        <div style={{ fontSize: 26, color: "#9fb0c8" }}>
          t = {(frame / fps).toFixed(2)} s · {width}x{height} · {fps} fps · FIXTURE (not Blender)
        </div>
      </div>
    </AbsoluteFill>
  );
};
