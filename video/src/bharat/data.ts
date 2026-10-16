/**
 * Telemetry of the five simulated shots (written by sim/export_telemetry.py, one row per rendered frame).
 * Extends the base contract in ../lib/telemetry.ts with the control-room event levels and a map.
 */
import bharatFull from "../data/bharat_full.telemetry.json";
import baselineDogs from "../data/baseline_dogs.telemetry.json";
import baselinePothole from "../data/baseline_pothole.telemetry.json";
import baselineTheft from "../data/baseline_theft.telemetry.json";
import usSidewalk from "../data/us_sidewalk.telemetry.json";

export type Level = "SENSE" | "AI" | "SAFETY" | "ACT" | "OK" | "ALARM" | "INFO";

export type SimFrame = {
  f: number;
  t: number;
  speed: number;
  state: string;
  x: number;
  y: number;
  heading: number;
  battery: number;
};

export type SimEvent = {
  frame: number;
  durationFrames: number;
  type: string;
  level: Level;
  label: string;
  detail: string;
  severity: "info" | "warn" | "alert";
};

export type SimMap = {
  xMin: number;
  xMax: number;
  roadHalf: number;
  shoulder: number;
  potholes: { x: number; y: number; r: number; depth: number; water: number }[];
  places: { kind: string; x: number; y: number }[];
  route: { x: number[]; y: number[] };
};

export type SimTelemetry = {
  version: 1;
  scene: string;
  label: string;
  fps: number;
  frameCount: number;
  frames: SimFrame[];
  events: SimEvent[];
  map: SimMap | null;
};

export const shots = {
  bharatFull: bharatFull as SimTelemetry,
  baselinePothole: baselinePothole as SimTelemetry,
  baselineDogs: baselineDogs as SimTelemetry,
  baselineTheft: baselineTheft as SimTelemetry,
  usSidewalk: usSidewalk as SimTelemetry,
};

export type ShotKey = keyof typeof shots;

/** Telemetry row for a moment `seconds` into the source clip (time based, so comp fps may differ). */
export const frameAt = (tel: SimTelemetry, seconds: number): SimFrame => {
  const i = Math.max(0, Math.min(tel.frames.length - 1, Math.round(seconds * tel.fps)));
  return tel.frames[i];
};

/** Events already fired at `seconds`, newest last. */
export const eventsUntil = (tel: SimTelemetry, seconds: number): SimEvent[] =>
  tel.events.filter((e) => e.frame / tel.fps <= seconds);

export const firstEvent = (tel: SimTelemetry, title: string): SimEvent | undefined =>
  tel.events.find((e) => e.label.startsWith(title));
