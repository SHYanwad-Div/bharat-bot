import { Video } from "@remotion/media";
import {
  AbsoluteFill,
  OffthreadVideo,
  staticFile,
  useVideoConfig,
  type CalculateMetadataFunction,
} from "remotion";
import { Hud } from "../components/Hud";
import { getMediaDurationInSeconds } from "../lib/media";
import { telemetryDurationInFrames, type Telemetry } from "../lib/telemetry";

export const CLIP_HUD_FPS = 30;

export type ClipHudProps = {
  /** Path inside public/, e.g. "clips/pothole.mp4". */
  clip: string;
  telemetry: Telemetry;
  /** Show the telemetry frame index (for sync checks). */
  debug?: boolean;
  /**
   * "media"    = <Video> from @remotion/media (recommended default, WebCodecs, fastest).
   * "offthread" = <OffthreadVideo> from remotion (ffmpeg frame extraction, widest codec support).
   */
  engine?: "media" | "offthread";
  /** With engine "media": fail the render instead of silently falling back to OffthreadVideo. */
  strict?: boolean;
};

/** A rendered Blender clip with the frame-synced telemetry HUD on top. */
export const ClipHud: React.FC<ClipHudProps> = ({ clip, telemetry, debug, engine = "media", strict = false }) => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {engine === "media" ? (
        <Video
          src={staticFile(clip)}
          objectFit="cover"
          premountFor={fps}
          disallowFallbackToOffthreadVideo={strict}
          style={{ width: "100%", height: "100%" }}
        />
      ) : (
        <OffthreadVideo src={staticFile(clip)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      )}
      <Hud telemetry={telemetry} debug={debug} />
    </AbsoluteFill>
  );
};

/** Composition length = length of the MP4, measured with Mediabunny. */
export const calculateClipHudMetadata: CalculateMetadataFunction<ClipHudProps> = async ({ props }) => {
  const seconds = await getMediaDurationInSeconds(staticFile(props.clip));
  return { durationInFrames: Math.max(1, Math.round(seconds * CLIP_HUD_FPS)) };
};

/**
 * The HUD alone on a transparent background, for compositing in another editor.
 * Length comes from the telemetry itself (no clip needed); the metadata also
 * switches the default export to VP9 + alpha, so the Studio "Render" button and a
 * plain `npx remotion render HudOnly out/hud.webm` both produce a transparent video.
 */
export const HudOnly: React.FC<{ telemetry: Telemetry }> = ({ telemetry }) => {
  return <Hud telemetry={telemetry} />;
};

export const calculateHudOnlyMetadata: CalculateMetadataFunction<{ telemetry: Telemetry }> = ({ props }) => {
  return {
    durationInFrames: telemetryDurationInFrames(props.telemetry, CLIP_HUD_FPS),
    defaultCodec: "vp9",
    defaultVideoImageFormat: "png",
    defaultPixelFormat: "yuva420p",
  };
};
