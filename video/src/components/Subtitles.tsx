import type { Caption } from "@remotion/captions";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts } from "../theme";

/**
 * Shows the caption(s) active "now". Times are milliseconds relative to the
 * start of the enclosing <Sequence> (or the composition), so put the track
 * inside the same Sequence as the voiceover / clip it belongs to.
 * Captions are whitespace sensitive: keep any leading space in `text`.
 */
export const Subtitles: React.FC<{ captions: Caption[]; bottom?: number }> = ({ captions, bottom = 56 }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const nowMs = (frame / fps) * 1000;
  const active = captions.filter((c) => nowMs >= c.startMs && nowMs < c.endMs);

  if (active.length === 0) {
    return null;
  }

  const s = width / 1920;

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: bottom * s,
        display: "flex",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          maxWidth: 1500 * s,
          padding: `${10 * s}px ${28 * s}px`,
          borderRadius: 12 * s,
          background: "rgba(0, 0, 0, 0.62)",
          color: colors.white,
          fontFamily: fonts.display,
          fontSize: 52 * s,
          fontWeight: 600,
          lineHeight: 1.2,
          textAlign: "center",
          textWrap: "balance",
          whiteSpace: "pre-wrap",
        }}
      >
        {active.map((c) => c.text).join("").trim()}
      </div>
    </div>
  );
};
