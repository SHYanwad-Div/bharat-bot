import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  type CalculateMetadataFunction,
} from "remotion";
import { duckingVolume } from "../lib/audio";
import { getMediaDurationInSeconds } from "../lib/media";
import { colors, fonts } from "../theme";

export const AUDIO_MIX_FPS = 30;

export type AudioMixProps = {
  /** Paths inside public/. */
  music: string;
  voiceover: string;
  sfx: { src: string; atFrame: number; volume?: number }[];
  voiceoverStartFrame: number;
  /** Filled in by calculateMetadata from the real length of the voiceover file. */
  voiceoverFrames?: number;
};

const MUSIC_FULL = 0.5;
const MUSIC_DUCKED = 0.12;

/** Music bed that ducks under the voiceover, plus one-shot sound effects. */
export const AudioMix: React.FC<AudioMixProps> = ({ music, voiceover, sfx, voiceoverStartFrame, voiceoverFrames = 90 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const voiceoverEnd = voiceoverStartFrame + voiceoverFrames;
  const musicVolume = duckingVolume(frame, voiceoverStartFrame, voiceoverEnd, { full: MUSIC_FULL, ducked: MUSIC_DUCKED });

  return (
    <AbsoluteFill style={{ background: colors.bg, color: colors.text, fontFamily: fonts.display, padding: 80 }}>
      {/* looping music bed (loop repeats the file until the composition ends) */}
      <Audio src={staticFile(music)} loop volume={musicVolume} premountFor={fps} name="Music" />

      {/* voiceover: `from` delays the start, no wrapper Sequence needed */}
      <Audio src={staticFile(voiceover)} from={voiceoverStartFrame} premountFor={fps} name="Voiceover" />

      {/* one-shot SFX pinned to frames, e.g. to a telemetry event */}
      {sfx.map((effect) => (
        <Audio key={`${effect.src}-${effect.atFrame}`} src={staticFile(effect.src)} from={effect.atFrame} volume={effect.volume ?? 0.8} premountFor={fps} name="SFX" />
      ))}

      <div style={{ fontSize: 96, fontWeight: 700 }}>Audio mix demo</div>
      <div style={{ fontSize: 44, color: colors.muted, marginTop: 12 }}>
        music gain {musicVolume.toFixed(2)} · voiceover {voiceoverStartFrame}–{voiceoverEnd} · frame {frame}
      </div>
      <div style={{ marginTop: 40, width: 1200, height: 28, borderRadius: 14, background: "rgba(255,255,255,0.12)" }}>
        <div style={{ width: `${(musicVolume / MUSIC_FULL) * 100}%`, height: "100%", borderRadius: 14, background: colors.saffron }} />
      </div>
    </AbsoluteFill>
  );
};

/** Composition length follows the real voiceover length; the measured value is also passed to the component. */
export const calculateAudioMixMetadata: CalculateMetadataFunction<AudioMixProps> = async ({ props }) => {
  const seconds = await getMediaDurationInSeconds(staticFile(props.voiceover));
  const voiceoverFrames = Math.ceil(seconds * AUDIO_MIX_FPS);
  return {
    durationInFrames: props.voiceoverStartFrame + voiceoverFrames + 30,
    props: { ...props, voiceoverFrames },
  };
};
