import type { Caption } from "@remotion/captions";
import { staticFile } from "remotion";
import { getMediaDurationInSeconds } from "./media";

/** One spoken line: the text (also used as the caption) and its audio file inside public/. */
export type VoiceoverLine = { text: string; src: string };

export type PlannedLine = VoiceoverLine & {
  /** Frame (composition timeline) where the audio starts. */
  startFrame: number;
  durationInFrames: number;
};

export type VoiceoverPlan = {
  lines: PlannedLine[];
  /** Frame where the last line ends. */
  endFrame: number;
  /** Total length incl. lead-in and tail, ready for `durationInFrames`. */
  totalFrames: number;
  /** Subtitle cues, in ms from the start of the composition. */
  captions: Caption[];
};

/**
 * Script-driven voiceover: measure every line's audio file and lay the lines out
 * back to back. Caption timing falls out for free (no speech recognition needed).
 * Run it inside `calculateMetadata` and hand the result to the component as a prop.
 */
export const planVoiceover = async (
  lines: VoiceoverLine[],
  fps: number,
  { leadInFrames = 15, gapFrames = 9, tailFrames = 30 }: { leadInFrames?: number; gapFrames?: number; tailFrames?: number } = {},
): Promise<VoiceoverPlan> => {
  const seconds = await Promise.all(lines.map((line) => getMediaDurationInSeconds(staticFile(line.src))));

  let cursor = leadInFrames;
  const planned: PlannedLine[] = lines.map((line, i) => {
    const durationInFrames = Math.ceil(seconds[i] * fps);
    const item = { ...line, startFrame: cursor, durationInFrames };
    cursor += durationInFrames + gapFrames;
    return item;
  });

  const endFrame = cursor - gapFrames;
  const captions: Caption[] = planned.map((line) => ({
    text: line.text,
    startMs: (line.startFrame / fps) * 1000,
    endMs: ((line.startFrame + line.durationInFrames) / fps) * 1000,
    timestampMs: null,
    confidence: null,
  }));

  return { lines: planned, endFrame, totalFrames: endFrame + tailFrames, captions };
};
