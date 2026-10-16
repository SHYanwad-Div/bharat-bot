"""Telemetry writer: simulation -> Remotion HUD.

Stdlib only, so it also runs inside Blender's bundled Python. Copy the file next
to your sim scripts or add this folder to sys.path.

    from telemetry_writer import TelemetryWriter

    tw = TelemetryWriter(scene="pothole", fps=30)
    for _ in range(frame_count):                 # once per RENDERED frame, in order
        tw.log(speed=1.4, state="CRUISE", x=robot.x, y=robot.y, heading=0.0, battery=0.82)
    tw.event("pothole_detected", "Pothole 3 m ahead", severity="warn", frame=45)
    tw.save("video/src/data/pothole.telemetry.json")

The JSON matches `Telemetry` in src/lib/telemetry.ts: frames[i] is the i-th frame
of the rendered MP4 (0-based), so clip and telemetry cannot drift apart.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union


class TelemetryWriter:
    def __init__(self, scene: str, fps: float) -> None:
        self.scene = scene
        self.fps = float(fps)
        self.frames: list[dict] = []
        self.events: list[dict] = []

    def log(
        self,
        speed: float,
        state: str,
        x: Optional[float] = None,
        y: Optional[float] = None,
        heading: Optional[float] = None,
        battery: Optional[float] = None,
    ) -> int:
        """Record one rendered frame. Returns its 0-based index (position in the clip)."""
        index = len(self.frames)
        row: dict = {
            "f": index,
            "t": round(index / self.fps, 4),
            "speed": round(float(speed), 3),
            "state": str(state),
        }
        if x is not None:
            row["x"] = round(float(x), 3)
        if y is not None:
            row["y"] = round(float(y), 3)
        if heading is not None:
            row["heading"] = round(float(heading), 1)
        if battery is not None:
            row["battery"] = round(float(battery), 4)
        self.frames.append(row)
        return index

    def event(
        self,
        type: str,
        label: str,
        severity: str = "info",
        frame: Optional[int] = None,
        duration_frames: int = 45,
    ) -> None:
        """Mark something worth a HUD toast. `frame=None` means the most recently logged frame."""
        if frame is None:
            frame = max(0, len(self.frames) - 1)
        self.events.append(
            {
                "frame": int(frame),
                "durationFrames": int(duration_frames),
                "type": type,
                "label": label,
                "severity": severity,
            }
        )

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "scene": self.scene,
            "fps": self.fps,
            "frameCount": len(self.frames),
            "frames": self.frames,
            "events": self.events,
        }

    def save(self, path: Union[str, Path]) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.to_dict(), separators=(",", ":")), encoding="utf-8")
        return out
