import React from "react";
import { Composition } from "remotion";
import { AdComposition } from "./compositions/AdComposition";
import type { AdCompositionProps } from "./compositions/AdComposition";
import type { Timeline } from "./schemas/timeline";

/**
 * Example Timeline JSON used to register the sample composition.
 *
 * Shape follows packages/contracts/timeline.schema.json exactly (schema_version
 * 1, fps {num,den}, canvas, tracks[].items[]). 9:16 1080x1920, 30fps,
 * ~200 frames (~6.7s), matching the task's requested sample size.
 *
 * This is throwaway example data for Phase 9 scaffolding, not a real
 * project revision -- real Timeline JSON will come from the backend once
 * the editor (Phase 9/10) is wired up.
 */
export const SAMPLE_TIMELINE: Timeline = {
  schema_version: 1,
  revision_id: "sample-0001",
  fps: { num: 30, den: 1 },
  duration_frames: 200,
  canvas: { width: 1080, height: 1920 },
  tracks: [
    {
      id: "v1",
      kind: "video",
      items: [
        {
          id: "shot_01_gameplay",
          shot_id: "shot_01",
          asset_id: null,
          start_frame: 0,
          duration_frames: 100,
          source_in_us: 0,
          transform: {
            placeholderLabel: "Synova gameplay - hafıza dizisi",
            placeholderColor: "#2b4d7a",
          },
          opacity: 1,
          lock: false,
        },
        {
          id: "shot_02_ai_actor",
          shot_id: "shot_02",
          asset_id: null,
          start_frame: 100,
          duration_frames: 100,
          source_in_us: 0,
          transform: {
            placeholderLabel: "AI insanlı sahne - kameraya konuşma",
            placeholderColor: "#6a2b7a",
          },
          opacity: 1,
          lock: false,
        },
      ],
    },
    {
      id: "graphics",
      kind: "graphics",
      items: [
        {
          id: "title_hook",
          start_frame: 0,
          duration_frames: 60,
          transform: {
            graphic: {
              template: "title",
              text: "Hafızanı test et!",
              subtext: "Synova ile başla",
              color: "#ffffff",
            },
          },
          opacity: 1,
          lock: false,
        },
        {
          id: "logo_corner",
          start_frame: 0,
          duration_frames: 200,
          transform: {
            graphic: {
              template: "logo",
              text: "SYNOVA",
              color: "rgba(255,255,255,0.92)",
            },
          },
          opacity: 0.9,
          lock: false,
        },
        {
          id: "cta_end_card",
          start_frame: 155,
          duration_frames: 45,
          transform: {
            graphic: {
              template: "cta_card",
              text: "Şimdi İndir",
              subtext: "Ücretsiz - App Store & Google Play",
              color: "#1b8a3e",
            },
          },
          opacity: 1,
          lock: false,
        },
      ],
    },
    {
      id: "voice",
      kind: "audio",
      items: [
        {
          id: "voice_over_01",
          start_frame: 0,
          duration_frames: 200,
          gain: 1,
          lock: false,
        },
      ],
    },
    {
      id: "music",
      kind: "audio",
      items: [
        {
          id: "music_bed_01",
          start_frame: 0,
          duration_frames: 200,
          gain: 0.6,
          lock: false,
        },
      ],
    },
    {
      id: "game_audio",
      kind: "audio",
      items: [
        {
          id: "game_audio_01",
          start_frame: 0,
          duration_frames: 100,
          gain: 0.4,
          lock: false,
        },
      ],
    },
    {
      id: "captions",
      kind: "subtitle",
      items: [
        {
          id: "caption_01",
          start_frame: 10,
          duration_frames: 80,
          lock: false,
        },
        {
          id: "caption_02",
          start_frame: 110,
          duration_frames: 80,
          lock: false,
        },
      ],
    },
  ],
};

export const RemotionRoot: React.FC = () => {
  // No zod schema is used for this composition (Remotion's <Composition> is
  // generic over <Schema, Props>; only the Props generic matters here).
  return (
    <Composition<any, AdCompositionProps>
      id="AdComposition"
      component={AdComposition}
      durationInFrames={SAMPLE_TIMELINE.duration_frames}
      fps={Math.round(SAMPLE_TIMELINE.fps.num / SAMPLE_TIMELINE.fps.den)}
      width={SAMPLE_TIMELINE.canvas.width}
      height={SAMPLE_TIMELINE.canvas.height}
      defaultProps={{ timeline: SAMPLE_TIMELINE }}
    />
  );
};
