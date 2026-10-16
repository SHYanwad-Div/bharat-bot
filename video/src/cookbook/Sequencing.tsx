import { Video } from "@remotion/media";
import { linearTiming, springTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { AbsoluteFill, Series, Sequence, staticFile, useVideoConfig } from "remotion";
import { colors, fonts } from "../theme";

const SceneCard: React.FC<{ label: string; color: string }> = ({ label, color }) => {
  return (
    <AbsoluteFill
      style={{
        background: color,
        alignItems: "center",
        justifyContent: "center",
        fontFamily: fonts.display,
        fontSize: 140,
        fontWeight: 700,
        color: colors.bg,
      }}
    >
      {label}
    </AbsoluteFill>
  );
};

const ClipScene: React.FC<{ src: string }> = ({ src }) => {
  const { fps } = useVideoConfig();
  return <Video src={staticFile(src)} premountFor={fps} objectFit="cover" muted style={{ width: "100%", height: "100%" }} />;
};

// ---------------------------------------------------------------- Series ----
// Back-to-back scenes, no transitions. `offset` shifts a scene (negative = overlap).
export const SERIES_FRAMES = 45 + 60 + 45 - 10; // the -10 comes from offset={-10}

export const SeriesDemo: React.FC<{ clip: string }> = ({ clip }) => {
  const { fps } = useVideoConfig();
  return (
    <Series>
      <Series.Sequence durationInFrames={45} premountFor={fps} name="Intro">
        <SceneCard label="1 · Problem" color={colors.saffron} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={60} offset={-10} premountFor={fps} name="Clip">
        <ClipScene src={clip} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={45} premountFor={fps} name="Outro">
        <SceneCard label="3 · Result" color={colors.greenBright} />
      </Series.Sequence>
    </Series>
  );
};

// ---------------------------------------------------------- TransitionSeries ----
const SCENE_FRAMES = [45, 60, 45] as const;
const TRANSITION_1 = linearTiming({ durationInFrames: 15 });
const TRANSITION_2 = springTiming({ config: { damping: 200 }, durationInFrames: 20 });

/** Transitions overlap their neighbours, so the total is SHORTER than the sum of the scenes. */
export const transitionDemoFrames = (fps: number): number => {
  const sum = SCENE_FRAMES.reduce((a, b) => a + b, 0);
  return sum - TRANSITION_1.getDurationInFrames({ fps }) - TRANSITION_2.getDurationInFrames({ fps }); // 150 - 15 - 20 = 115
};

export const TransitionDemo: React.FC<{ clip: string }> = ({ clip }) => {
  const { fps } = useVideoConfig();
  return (
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES[0]} premountFor={fps} name="Intro">
        <SceneCard label="Intro" color={colors.saffron} />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={TRANSITION_1} />
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES[1]} premountFor={fps} name="Clip">
        <ClipScene src={clip} />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={slide({ direction: "from-right" })} timing={TRANSITION_2} />
      <TransitionSeries.Sequence durationInFrames={SCENE_FRAMES[2]} premountFor={fps} name="Outro">
        <SceneCard label="Outro" color={colors.greenBright} />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};

// ---------------------------------------------- plain <Sequence> (free layout) ----
// Independent items placed anywhere on the timeline; they may overlap.
export const FreeSequenceDemo: React.FC<{ clip: string }> = ({ clip }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill>
      <ClipScene src={clip} />
      <Sequence from={30} durationInFrames={60} premountFor={fps} name="Badge">
        <div style={{ position: "absolute", left: 80, top: 80, padding: "14px 28px", borderRadius: 14, background: colors.saffron, color: colors.bg, fontFamily: fonts.display, fontSize: 56, fontWeight: 700 }}>
          Pothole!
        </div>
      </Sequence>
    </AbsoluteFill>
  );
};
