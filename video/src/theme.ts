import { loadFont as loadRajdhani } from "@remotion/google-fonts/Rajdhani";
import { loadFont as loadJetBrainsMono } from "@remotion/google-fonts/JetBrainsMono";

// Fonts are fetched from Google at render time (needs internet) and the render
// waits until they are ready. For offline-proof renders, drop .woff2 files in
// public/fonts and use `loadFont` from "@remotion/fonts" instead.
const display = loadRajdhani("normal", {
  weights: ["500", "600", "700"],
  subsets: ["latin"],
});
const mono = loadJetBrainsMono("normal", {
  weights: ["400", "700"],
  subsets: ["latin"],
});

export const fonts = {
  display: display.fontFamily,
  mono: mono.fontFamily,
} as const;

export const colors = {
  bg: "#0b1220",
  panel: "rgba(11, 18, 32, 0.78)",
  panelBorder: "rgba(255, 255, 255, 0.14)",
  text: "#f5f7fa",
  muted: "#9aa7bd",
  saffron: "#ff9933",
  white: "#ffffff",
  green: "#138808",
  greenBright: "#2ecc71",
  amber: "#f5b301",
  red: "#ef4444",
  blue: "#38bdf8",
  violet: "#a78bfa",
} as const;

/** Colour per robot state shown in the HUD chip. Unknown states fall back to `muted`. */
export const stateColors: Record<string, string> = {
  IDLE: colors.muted,
  CRUISE: colors.greenBright,
  SLOW: colors.amber,
  AVOID: colors.saffron,
  STOP: colors.red,
  WAIT: colors.blue,
  REROUTE: colors.violet,
  ALERT: colors.red,
};

export const severityColors = {
  info: colors.blue,
  warn: colors.amber,
  alert: colors.red,
} as const;
