import { ALL_FORMATS, Input, UrlSource } from "mediabunny";

/**
 * Reads container metadata with Mediabunny (the engine behind `<Video>` from
 * `@remotion/media`). Works for anything `staticFile()` / a URL can serve:
 * rendered Blender MP4s, voiceover WAV/MP3, music, ...
 * Use inside `calculateMetadata` to size a composition from its media.
 */
const withInput = async <T>(src: string, fn: (input: Input) => Promise<T>): Promise<T> => {
  const input = new Input({ formats: ALL_FORMATS, source: new UrlSource(src) });
  try {
    return await fn(input);
  } finally {
    input.dispose();
  }
};

export const getMediaDurationInSeconds = (src: string): Promise<number> => {
  return withInput(src, (input) => input.computeDuration());
};

export const getVideoDimensions = (src: string): Promise<{ width: number; height: number }> => {
  return withInput(src, async (input) => {
    const track = await input.getPrimaryVideoTrack();
    if (!track) {
      throw new Error(`No video track found in ${src}`);
    }
    return { width: track.displayWidth, height: track.displayHeight };
  });
};
