import { Video } from "@remotion/media";
import { parseSrt } from "@remotion/captions";
import { AbsoluteFill, Sequence, staticFile, useVideoConfig } from "remotion";
import { LowerThird } from "../components/LowerThird";
import { Subtitles } from "../components/Subtitles";

// Inline SRT keeps the demo self-contained. For a real file, put it in public/
// and fetch(staticFile("subs/scene1.srt")) inside calculateMetadata.
const SRT = `1
00:00:00,300 --> 00:00:02,200
Most delivery robots are built for smooth sidewalks.

2
00:00:02,400 --> 00:00:04,800
Indian streets bring potholes, monsoon floods, stray dogs and cows.
`;

const { captions } = parseSrt({ input: SRT });

export const CaptionsLowerThird: React.FC<{ clip: string }> = ({ clip }) => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Video src={staticFile(clip)} premountFor={fps} objectFit="cover" muted style={{ width: "100%", height: "100%" }} />

      {/* Lower third: appears at 0.5 s, stays 3 s. Timing lives on the Sequence. */}
      <Sequence from={Math.round(0.5 * fps)} durationInFrames={3 * fps} premountFor={fps} name="Lower third">
        <LowerThird title="Bharat-Bot" subtitle="Pothole avoidance · simulation" />
      </Sequence>

      {/* Subtitles: caption times are relative to this Sequence's start. */}
      <Sequence name="Subtitles">
        <Subtitles captions={captions} />
      </Sequence>
    </AbsoluteFill>
  );
};
