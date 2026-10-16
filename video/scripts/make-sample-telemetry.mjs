// Writes src/data/sample-pothole.telemetry.json: deterministic fake telemetry in
// the exact format the Blender sim should export (see src/lib/telemetry.ts).
// Run: node scripts/make-sample-telemetry.mjs
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const FPS = 30;
const FRAMES = 150;
const outFile = resolve(dirname(fileURLToPath(import.meta.url)), "../src/data/sample-pothole.telemetry.json");

const smooth = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
const round = (value, digits) => Number(value.toFixed(digits));

const frames = [];
let x = 0;
let prevX = 0;
let prevY = 0;
let heading = 0;

for (let f = 0; f < FRAMES; f++) {
  let speed;
  let state;
  if (f < 6) {
    speed = 0;
    state = "IDLE";
  } else if (f < 45) {
    speed = 1.4 * smooth(6, 21, f);
    state = "CRUISE";
  } else if (f < 60) {
    speed = 1.4 - 0.9 * smooth(45, 60, f);
    state = "SLOW";
  } else if (f < 105) {
    speed = 0.5 + 0.25 * smooth(60, 80, f);
    state = "AVOID";
  } else {
    speed = 0.75 + 0.65 * smooth(105, 125, f);
    state = "CRUISE";
  }

  x += speed / FPS;
  // lateral swerve around the pothole between f55 and f105
  const y = 0.9 * smooth(55, 75, f) * (1 - smooth(85, 105, f));
  const dx = x - prevX;
  const dy = y - prevY;
  if (Math.hypot(dx, dy) > 1e-4) {
    heading = (Math.atan2(dy, dx) * 180) / Math.PI;
  }
  prevX = x;
  prevY = y;

  frames.push({
    f,
    t: round(f / FPS, 4),
    speed: round(speed, 3),
    state,
    x: round(x, 3),
    y: round(y, 3),
    heading: round(heading, 1),
    battery: round(0.82 - 0.00025 * f, 4),
  });
}

const telemetry = {
  version: 1,
  scene: "pothole",
  fps: FPS,
  frameCount: FRAMES,
  frames,
  events: [
    { frame: 45, durationFrames: 45, type: "pothole_detected", label: "Pothole 3 m ahead", severity: "warn" },
    { frame: 60, durationFrames: 40, type: "path_replanned", label: "Swerving into clear lane", severity: "info" },
    { frame: 105, durationFrames: 35, type: "path_clear", label: "Clear: resuming speed", severity: "info" },
  ],
};

mkdirSync(dirname(outFile), { recursive: true });
writeFileSync(outFile, JSON.stringify(telemetry));
console.log(`wrote ${outFile} (${FRAMES} frames @ ${FPS} fps)`);
