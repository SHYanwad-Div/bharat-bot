import { interpolate } from "remotion";

/**
 * Music gain that dips while a voiceover plays: `full` -> `ducked` over `rampFrames`
 * before `startFrame`, stays ducked until `endFrame`, then recovers.
 * Call it with the current frame and pass the result to <Audio volume={...}>.
 */
export const duckingVolume = (
  frame: number,
  startFrame: number,
  endFrame: number,
  { full = 0.5, ducked = 0.12, rampFrames = 8 }: { full?: number; ducked?: number; rampFrames?: number } = {},
): number => {
  return interpolate(
    frame,
    [startFrame - rampFrames, startFrame, endFrame, endFrame + 2 * rampFrames],
    [full, ducked, ducked, full],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
};
