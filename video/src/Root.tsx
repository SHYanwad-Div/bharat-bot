import { Composition, Folder } from "remotion";
import { AudioMix, AUDIO_MIX_FPS, calculateAudioMixMetadata } from "./cookbook/AudioMix";
import { VoiceoverCaptions, VOICEOVER_FPS, calculateVoiceoverCaptionsMetadata } from "./cookbook/VoiceoverCaptions";
import { CaptionsLowerThird } from "./cookbook/CaptionsLowerThird";
import { RobotCam } from "./cookbook/RobotCam";
import { ClipHud, CLIP_HUD_FPS, HudOnly, calculateClipHudMetadata, calculateHudOnlyMetadata } from "./cookbook/ClipHud";
import { FreeSequenceDemo, SeriesDemo, SERIES_FRAMES, TransitionDemo, transitionDemoFrames } from "./cookbook/Sequencing";
import { SplitScreen, SplitWipe } from "./cookbook/SplitScreen";
import { telemetry } from "./data";
import { FixtureClip } from "./fixtures/FixtureClip";
import { FIXTURE_AUDIO, FIXTURE_CLIP, FIXTURE_CLIP_FPS, FIXTURE_CLIP_FRAMES, FIXTURE_VOICEOVER_LINES } from "./fixtures/paths";
import { Main } from "./Main";
import { BharatBotFilm } from "./bharat/BharatBotFilm";
import { BharatBotHighlights } from "./bharat/BharatBotHighlights";
import {
  CostScene, FeaturesScene, HeroScene, IndiaScene, LimitsScene, OutroScene, ResultsScene, SafetyScene, TitleScene,
} from "./bharat/scenes";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* The film: npx remotion render BharatBotFilm out/bharat-bot-film.mp4 */}
      <Composition id="BharatBotFilm" component={BharatBotFilm} durationInFrames={5263} fps={30} width={1920} height={1080} />
      {/* ~1 minute cut for sharing: npx remotion render BharatBotHighlights out/bharat-bot-highlights.mp4 */}
      <Composition id="BharatBotHighlights" component={BharatBotHighlights} durationInFrames={1780} fps={30} width={1920} height={1080} />
      <Folder name="BharatBot-scenes">
        <Composition id="Title" component={TitleScene} durationInFrames={150} fps={30} width={1920} height={1080} />
        <Composition id="IndiaFacts" component={IndiaScene} durationInFrames={240} fps={30} width={1920} height={1080} />
        <Composition id="MeetBharatBot" component={FeaturesScene} durationInFrames={240} fps={30} width={1920} height={1080} />
        <Composition id="HeroRun" component={HeroScene} durationInFrames={2676} fps={30} width={1920} height={1080} />
        <Composition id="Results" component={ResultsScene} durationInFrames={300} fps={30} width={1920} height={1080} />
        <Composition id="Safety" component={SafetyScene} durationInFrames={210} fps={30} width={1920} height={1080} />
        <Composition id="Economics" component={CostScene} durationInFrames={270} fps={30} width={1920} height={1080} />
        <Composition id="Limits" component={LimitsScene} durationInFrames={240} fps={30} width={1920} height={1080} />
        <Composition id="Outro" component={OutroScene} durationInFrames={180} fps={30} width={1920} height={1080} />
      </Folder>

      {/* Placeholder title card: `npx remotion render Main out/test.mp4` */}
      <Composition
        id="Main"
        component={Main}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          eyebrow: "SIDEWALK DELIVERY ROBOT · INDIA EDITION",
          title: "Bharat-Bot",
          subtitle: "Built for potholes, monsoon streets, stray dogs and cows",
          tagline: "Simulation explainer · placeholder title card",
        }}
      />

      {/* Working reference compositions, see research/remotion.md. Safe to delete. */}
      <Folder name="Cookbook">
        <Composition
          id="ClipHud"
          component={ClipHud}
          durationInFrames={FIXTURE_CLIP_FRAMES}
          fps={CLIP_HUD_FPS}
          width={1920}
          height={1080}
          defaultProps={{ clip: FIXTURE_CLIP, telemetry: telemetry.samplePothole, debug: true }}
          calculateMetadata={calculateClipHudMetadata}
        />
        <Composition
          id="HudOnly"
          component={HudOnly}
          durationInFrames={FIXTURE_CLIP_FRAMES}
          fps={CLIP_HUD_FPS}
          width={1920}
          height={1080}
          defaultProps={{ telemetry: telemetry.samplePothole }}
          calculateMetadata={calculateHudOnlyMetadata}
        />
        <Composition
          id="SplitSideBySide"
          component={SplitScreen}
          durationInFrames={FIXTURE_CLIP_FRAMES}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{
            leftClip: FIXTURE_CLIP,
            rightClip: FIXTURE_CLIP,
            leftLabel: "Typical US sidewalk robot",
            rightLabel: "Bharat-Bot",
            rightTrimBefore: 30,
          }}
        />
        <Composition
          id="SplitWipe"
          component={SplitWipe}
          durationInFrames={FIXTURE_CLIP_FRAMES}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{
            leftClip: FIXTURE_CLIP,
            rightClip: FIXTURE_CLIP,
            leftLabel: "Before",
            rightLabel: "After",
            rightTrimBefore: 30,
          }}
        />
        <Composition
          id="SeriesDemo"
          component={SeriesDemo}
          durationInFrames={SERIES_FRAMES}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{ clip: FIXTURE_CLIP }}
        />
        <Composition
          id="TransitionDemo"
          component={TransitionDemo}
          durationInFrames={transitionDemoFrames(30)}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{ clip: FIXTURE_CLIP }}
        />
        <Composition
          id="FreeSequenceDemo"
          component={FreeSequenceDemo}
          durationInFrames={120}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{ clip: FIXTURE_CLIP }}
        />
        <Composition
          id="CaptionsLowerThird"
          component={CaptionsLowerThird}
          durationInFrames={FIXTURE_CLIP_FRAMES}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{ clip: FIXTURE_CLIP }}
        />
        <Composition
          id="RobotCam"
          component={RobotCam}
          durationInFrames={FIXTURE_CLIP_FRAMES}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{ clip: FIXTURE_CLIP, label: "CAM 01 · FRONT" }}
        />
        <Composition
          id="AudioMix"
          component={AudioMix}
          durationInFrames={150}
          fps={AUDIO_MIX_FPS}
          width={1920}
          height={1080}
          defaultProps={{
            music: FIXTURE_AUDIO.music,
            voiceover: FIXTURE_AUDIO.voiceover,
            voiceoverStartFrame: 30,
            sfx: [
              { src: FIXTURE_AUDIO.ping, atFrame: 15 },
              { src: FIXTURE_AUDIO.whoosh, atFrame: 90, volume: 0.6 },
            ],
          }}
          calculateMetadata={calculateAudioMixMetadata}
        />
        <Composition
          id="VoiceoverCaptions"
          component={VoiceoverCaptions}
          durationInFrames={300}
          fps={VOICEOVER_FPS}
          width={1920}
          height={1080}
          defaultProps={{ clip: FIXTURE_CLIP, music: FIXTURE_AUDIO.music, lines: FIXTURE_VOICEOVER_LINES }}
          calculateMetadata={calculateVoiceoverCaptionsMetadata}
        />
      </Folder>

      {/* Stand-in for a Blender render: `npm run fixtures` writes public/_fixtures/test-clip.mp4 */}
      <Folder name="Fixtures">
        <Composition id="FixtureClip" component={FixtureClip} durationInFrames={FIXTURE_CLIP_FRAMES} fps={FIXTURE_CLIP_FPS} width={1280} height={720} />
      </Folder>
    </>
  );
};
