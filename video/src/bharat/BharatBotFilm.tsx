import { Audio } from "@remotion/media";
import { linearTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import React from "react";
import { AbsoluteFill, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import {
  CostScene, FailScene, FeaturesScene, HeroScene, IndiaScene, LimitsScene, OutroScene, ResultsScene, SafetyScene,
  TitleScene, UsScene,
} from "./scenes";

const Whoosh: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <Sequence durationInFrames={fps} premountFor={fps}>
      <Audio src={staticFile("audio/whoosh.wav")} volume={0.3} />
    </Sequence>
  );
};

export const BharatBotFilm: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = linearTiming({ durationInFrames: 12 });
  return (
    <AbsoluteFill style={{ background: "#070b14" }}>
      <TransitionSeries>
        <TransitionSeries.Sequence name="Title" durationInFrames={150} premountFor={fps}>
          <TitleScene />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="US sidewalk" durationInFrames={180} premountFor={fps}>
          <UsScene />
          <Whoosh />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="India facts" durationInFrames={240} premountFor={fps}>
          <IndiaScene />
          <Whoosh />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Baseline: pothole" durationInFrames={190} premountFor={fps}>
          <FailScene clip="clips/baseline_pothole.mp4" shot="baselinePothole" trimBefore={36} playbackRate={1}
            stamp="STUCK" scenario="TEST 1 · BROKEN ROAD" intro="Now drop a US-style robot onto an Indian street"
            why="Front wheels drop into an 11 cm pothole; it can only climb 6 cm" />
          <Whoosh />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Baseline: dogs" durationInFrames={271} premountFor={fps}>
          <FailScene clip="clips/baseline_dogs.mp4" shot="baselineDogs" trimBefore={45} playbackRate={1}
            stamp="BLOCKED" scenario="TEST 2 · STREET DOGS"
            why="It keeps driving, the pack keeps chasing, and stop-start retries keep them excited" />
          <Whoosh />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Baseline: theft" durationInFrames={260} premountFor={fps}>
          <FailScene clip="clips/baseline_theft.mp4" shot="baselineTheft" trimBefore={30} playbackRate={1.5}
            stamp="STOLEN" scenario="TEST 3 · THEFT"
            why="No tamper sensing: lifted and carried into a side lane, food and all" />
          <Whoosh />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Meet Bharat-Bot" durationInFrames={240} premountFor={fps}>
          <FeaturesScene />
          <Whoosh />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Bharat-Bot full run" durationInFrames={2676} premountFor={fps}>
          <HeroScene />
          <Whoosh />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Results" durationInFrames={300} premountFor={fps}>
          <ResultsScene />
          <Whoosh />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Safety architecture" durationInFrames={210} premountFor={fps}>
          <SafetyScene />
          <Whoosh />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Economics" durationInFrames={270} premountFor={fps}>
          <CostScene />
          <Whoosh />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Honest limits" durationInFrames={240} premountFor={fps}>
          <LimitsScene />
          <Whoosh />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Outro" durationInFrames={180} premountFor={fps}>
          <OutroScene />
          <Whoosh />
        </TransitionSeries.Sequence>
      </TransitionSeries>
      <Audio src={staticFile("audio/music.wav")} premountFor={fps}
        volume={interpolate(frame, [0, fps, durationInFrames - 3 * fps, durationInFrames], [0, 0.3, 0.3, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
    </AbsoluteFill>
  );
};
