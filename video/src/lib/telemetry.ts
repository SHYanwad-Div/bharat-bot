/**
 * Telemetry contract between the Blender simulation and Remotion.
 *
 * The sim writes ONE json file per rendered clip. `frames[i]` describes the
 * i-th frame of that clip (0-based, same order as the rendered MP4), so a
 * clip and its telemetry can never drift as long as both come from the same
 * sim run. `fps` is the frame rate the sim ran at (usually the Blender scene fps).
 */
export type TelemetryFrame = {
  /** 0-based index inside the clip (== position in `frames`). */
  f: number;
  /** Seconds since clip start. */
  t: number;
  /** Robot speed in m/s. */
  speed: number;
  /** Robot state machine label, e.g. CRUISE / SLOW / AVOID / STOP / WAIT / REROUTE / ALERT. */
  state: string;
  /** Top-down position in metres (optional, used by the mini-map). */
  x?: number;
  y?: number;
  /** Heading in degrees (optional). */
  heading?: number;
  /** Battery 0..1 (optional). */
  battery?: number;
};

export type TelemetrySeverity = "info" | "warn" | "alert";

export type TelemetryEvent = {
  /** Clip frame (at `Telemetry.fps`) where the event starts. */
  frame: number;
  /** How long the HUD toast stays visible, in telemetry frames. Default 45. */
  durationFrames?: number;
  /** Machine-readable id, e.g. "pothole_detected", "dog_nearby", "cow_blocking". */
  type: string;
  /** Text shown in the HUD. */
  label: string;
  severity?: TelemetrySeverity;
};

export type Telemetry = {
  version: 1;
  scene: string;
  /** Frame rate the sim / the clip was rendered at. */
  fps: number;
  frameCount: number;
  frames: TelemetryFrame[];
  events: TelemetryEvent[];
};

export const DEFAULT_EVENT_FRAMES = 45;

/** Validates a parsed JSON blob so a bad export fails loudly instead of rendering a blank HUD. */
export const parseTelemetry = (raw: unknown): Telemetry => {
  const t = raw as Partial<Telemetry> | null;
  if (!t || typeof t !== "object") {
    throw new Error("Telemetry JSON is not an object");
  }
  if (typeof t.fps !== "number" || t.fps <= 0) {
    throw new Error("Telemetry JSON needs a positive numeric `fps`");
  }
  if (!Array.isArray(t.frames) || t.frames.length === 0) {
    throw new Error("Telemetry JSON needs a non-empty `frames` array");
  }
  return {
    version: 1,
    scene: t.scene ?? "unnamed",
    fps: t.fps,
    frameCount: t.frameCount ?? t.frames.length,
    frames: t.frames,
    events: t.events ?? [],
  };
};

/**
 * Index into `frames` for a moment `seconds` after the start of the clip.
 * Time based (not frame based) so it stays correct when the composition fps
 * differs from the sim fps.
 */
export const telemetryIndexAt = (telemetry: Telemetry, seconds: number): number => {
  const index = Math.round(seconds * telemetry.fps);
  return Math.max(0, Math.min(telemetry.frames.length - 1, index));
};

export const telemetryFrameAt = (telemetry: Telemetry, seconds: number): TelemetryFrame => {
  return telemetry.frames[telemetryIndexAt(telemetry, seconds)];
};

/** Events whose toast window contains the given telemetry frame index. */
export const activeEventsAt = (telemetry: Telemetry, index: number): TelemetryEvent[] => {
  return telemetry.events.filter((event) => {
    const length = event.durationFrames ?? DEFAULT_EVENT_FRAMES;
    return index >= event.frame && index < event.frame + length;
  });
};

/** Duration of the telemetry in composition frames, for `calculateMetadata`. */
export const telemetryDurationInFrames = (telemetry: Telemetry, compositionFps: number): number => {
  return Math.ceil((telemetry.frames.length / telemetry.fps) * compositionFps);
};
