import { Audio, Video } from "@remotion/media";
import { AbsoluteFill, staticFile, useCurrentFrame, useVideoConfig, type CalculateMetadataFunction } from "remotion";
import { Subtitles } from "../components/Subtitles";
import { duckingVolume } from "../lib/audio";
import { planVoiceover, type VoiceoverLine, type VoiceoverPlan } from "../lib/voiceover";

export const VOICEOVER_FPS = 30;

export type VoiceoverCaptionsProps = {
  clip: string;
  music: string;
  lines: VoiceoverLine[];
  /** Filled in by calculateMetadata. */
  plan?: VoiceoverPlan;
};

/**
 * Script-driven narration: one audio file per line, captions timed from the real
 * audio lengths, music ducked under the voice, background clip looped.
 */
export const VoiceoverCaptions: React.FC<VoiceoverCaptionsProps> = ({ clip, music, plan }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!plan) {
    return null;
  }

  const first = plan.lines[0];

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Video src={staticFile(clip)} loop muted premountFor={fps} objectFit="cover" style={{ width: "100%", height: "100%" }} />
      <Audio src={staticFile(music)} loop volume={duckingVolume(frame, first.startFrame, plan.endFrame)} premountFor={fps} name="Music" />
      {plan.lines.map((line) => (
        <Audio key={line.src} src={staticFile(line.src)} from={line.startFrame} premountFor={fps} name={`VO ${line.src}`} />
      ))}
      <Subtitles captions={plan.captions} />
    </AbsoluteFill>
  );
};

export const calculateVoiceoverCaptionsMetadata: CalculateMetadataFunction<VoiceoverCaptionsProps> = async ({ props }) => {
  const plan = await planVoiceover(props.lines, VOICEOVER_FPS);
  return { durationInFrames: plan.totalFrames, props: { ...props, plan } };
};
