import { Audio } from "@remotion/media";
import { linearTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import React from "react";
import { AbsoluteFill, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { FailScene, HeroMoment, IndiaScene, OutroScene, ResultsScene, TitleScene } from "./scenes";

/** ~1 minute cut for sharing: the problem in 15 s, Bharat-Bot's five big moments, the scorecard. */
export const BharatBotHighlights: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = linearTiming({ durationInFrames: 10 });
  return (
    <AbsoluteFill style={{ background: "#070b14" }}>
      <TransitionSeries>
        <TransitionSeries.Sequence name="Title" durationInFrames={90} premountFor={fps}>
          <TitleScene />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="India facts" durationInFrames={120} premountFor={fps}>
          <IndiaScene />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Fail: pothole" durationInFrames={120} premountFor={fps}>
          <FailScene clip="clips/baseline_pothole.mp4" shot="baselinePothole" trimBefore={100} playbackRate={1}
            stamp="STUCK" scenario="US-STYLE ROBOT · BROKEN ROAD"
            why="11 cm pothole, and it can only climb 6 cm" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Fail: dogs" durationInFrames={130} premountFor={fps}>
          <FailScene clip="clips/baseline_dogs.mp4" shot="baselineDogs" trimBefore={110} playbackRate={1}
            stamp="BLOCKED" scenario="US-STYLE ROBOT · STREET DOGS"
            why="It keeps moving, so the pack keeps chasing" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Fail: theft" durationInFrames={140} premountFor={fps}>
          <FailScene clip="clips/baseline_theft.mp4" shot="baselineTheft" trimBefore={200} playbackRate={1.5}
            stamp="STOLEN" scenario="US-STYLE ROBOT · THEFT"
            why="No tamper alarm: carried off, food and all" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Bharat-Bot: potholes" durationInFrames={180} premountFor={fps}>
          <HeroMoment moment="potholes" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Bharat-Bot: dogs" durationInFrames={240} premountFor={fps}>
          <HeroMoment moment="dogs" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Bharat-Bot: cow + auto" durationInFrames={180} premountFor={fps}>
          <HeroMoment moment="cow" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Bharat-Bot: theft" durationInFrames={210} premountFor={fps}>
          <HeroMoment moment="theft" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Bharat-Bot: delivery" durationInFrames={180} premountFor={fps}>
          <HeroMoment moment="delivery" />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Results" durationInFrames={210} premountFor={fps}>
          <ResultsScene />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={t} />
        <TransitionSeries.Sequence name="Outro" durationInFrames={90} premountFor={fps}>
          <OutroScene />
        </TransitionSeries.Sequence>
      </TransitionSeries>
      <Audio src={staticFile("audio/music.wav")} premountFor={fps}
        volume={interpolate(frame, [0, fps, durationInFrames - 2 * fps, durationInFrames], [0, 0.3, 0.3, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
    </AbsoluteFill>
  );
};
