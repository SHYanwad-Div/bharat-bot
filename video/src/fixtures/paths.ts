/**
 * Paths (inside public/) of the generated test media the cookbook compositions use.
 * Swap these for real files, e.g. "clips/pothole.mp4", once Blender renders exist.
 * The leading underscore keeps fixtures sorted away from real assets.
 */
export const FIXTURE_CLIP = "_fixtures/test-clip.mp4";
export const FIXTURE_CLIP_FPS = 30;
export const FIXTURE_CLIP_FRAMES = 150;

export const FIXTURE_AUDIO = {
  music: "_fixtures/audio/music.wav",
  voiceover: "_fixtures/audio/vo.wav",
  ping: "_fixtures/audio/ping.wav",
  whoosh: "_fixtures/audio/whoosh.wav",
} as const;

/** Narration split into one file per sentence (Windows SAPI "Zira"), see research/remotion.md. */
export const FIXTURE_VOICEOVER_LINES = [
  { text: "Most delivery robots are built for smooth American sidewalks.", src: "_fixtures/audio/vo-1.wav" },
  { text: "Indian streets bring potholes, monsoon floods, stray dogs and cows.", src: "_fixtures/audio/vo-2.wav" },
  { text: "Bharat-Bot is built to handle all of it.", src: "_fixtures/audio/vo-3.wav" },
];
