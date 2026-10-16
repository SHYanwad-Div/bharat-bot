import { parseTelemetry } from "../lib/telemetry";
import samplePothole from "./sample-pothole.telemetry.json";

/**
 * One typed export per telemetry file the Blender sim writes.
 * To add a scene: drop `<scene>.telemetry.json` next to this file, import it
 * above and export `parseTelemetry(json)` below (parseTelemetry throws a clear
 * error if the export is malformed).
 */
export const telemetry = {
  samplePothole: parseTelemetry(samplePothole),
} as const;
