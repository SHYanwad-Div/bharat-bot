import { colors, fonts } from "../theme";

export { colors, fonts };

/** Colour per control-room level (SENSE -> AI -> SAFETY -> ACT, then OK or ALARM). */
export const levelColors: Record<string, string> = {
  SENSE: colors.blue,
  AI: colors.violet,
  SAFETY: colors.amber,
  ACT: "#e2e8f0",
  OK: colors.greenBright,
  ALARM: colors.red,
  INFO: colors.muted,
};

/** Colour per robot mode coming out of the simulator. */
export const modeColors: Record<string, string> = {
  CRUISE: colors.greenBright,
  ARRIVING: colors.greenBright,
  DELIVERED: colors.greenBright,
  "POTHOLE AVOID": colors.saffron,
  "SPEED BREAKER": colors.amber,
  WADING: colors.blue,
  "DOG HOTSPOT": colors.amber,
  "DOG FREEZE": colors.amber,
  CREEP: colors.amber,
  YIELD: colors.blue,
  "PERSON IN PATH": colors.amber,
  DELIVERING: colors.blue,
  TAMPER: colors.red,
  ALARM: colors.red,
  BLOCKED: colors.red,
  STUCK: colors.red,
  STOLEN: colors.red,
};

export const modeColor = (state: string): string => modeColors[state] ?? colors.muted;

export const panel: React.CSSProperties = {
  background: "rgba(8, 14, 26, 0.74)",
  border: "1.5px solid rgba(255, 255, 255, 0.14)",
  borderRadius: 18,
  boxShadow: "0 14px 44px rgba(0, 0, 0, 0.45)",
  backdropFilter: "blur(6px)",
};
