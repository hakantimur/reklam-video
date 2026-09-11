import React from "react";
import {
  AbsoluteFill,
  Audio,
  OffthreadVideo,
  Sequence,
  staticFile,
  useVideoConfig,
  interpolate,
  useCurrentFrame,
} from "remotion";
import type {
  GraphicSpec,
  Timeline,
  Track,
  TrackItem,
} from "../schemas/timeline";

/**
 * Renders a full Timeline JSON (packages/contracts/timeline.schema.json) as
 * a Remotion composition. Spec: docs/IMPLEMENTATION_SPEC_TR.md sec.16.2 --
 * the same composition is used for the interactive Player and for the
 * final `remotion render` MP4, so there is exactly one visual definition.
 *
 * IMPORTANT (this round only): there is no real video/audio asset pipeline
 * wired up yet. `video` and `audio` track items are rendered as clearly
 * labelled placeholder rectangles / silent placeholder markers -- never as
 * something that could pass for real footage. Every placeholder is
 * annotated with "PLACEHOLDER" plus the item id so this can never be
 * silently mistaken for a final render.
 */

export interface AdCompositionProps {
  timeline: Timeline;
  // Index signature so this satisfies Remotion's <Composition> Props
  // constraint (Record<string, unknown>) without widening `timeline` itself.
  [key: string]: unknown;
}

// Deterministic-ish color per id so repeated renders are visually stable
// and different items are distinguishable at a glance.
function colorForId(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  }
  const hue = hash % 360;
  return `hsl(${hue}, 55%, 32%)`;
}

const TRACK_KIND_LABEL: Record<Track["kind"], string> = {
  video: "VIDEO",
  graphics: "GRAPHICS",
  audio: "AUDIO",
  subtitle: "SUBTITLE",
};

function VideoPlaceholder({ item }: { item: TrackItem }) {
  const color = item.transform?.placeholderColor ?? colorForId(item.id);
  const label = item.transform?.placeholderLabel ?? "GAMEPLAY / SAHNE";
  return (
    <AbsoluteFill
      style={{
        backgroundColor: color,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        border: "6px dashed rgba(255,255,255,0.6)",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          fontFamily: "sans-serif",
          fontWeight: 800,
          fontSize: 54,
          color: "white",
          letterSpacing: 4,
          textShadow: "0 2px 8px rgba(0,0,0,0.6)",
        }}
      >
        PLACEHOLDER
      </div>
      <div
        style={{
          fontFamily: "monospace",
          fontSize: 28,
          color: "rgba(255,255,255,0.9)",
          marginTop: 12,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: "monospace",
          fontSize: 22,
          color: "rgba(255,255,255,0.7)",
          marginTop: 6,
        }}
      >
        item: {item.id}
        {item.shot_id ? ` | shot: ${item.shot_id}` : ""}
      </div>
    </AbsoluteFill>
  );
}

/** Safha 9: a real staged file (`transform.realFile`) always wins over the
 * placeholder — the placeholder exists only for shots/voice-overs that
 * genuinely have no take/asset yet, never as a stand-in once one exists. */
function VideoItemRenderer({ item }: { item: TrackItem }) {
  const { fps } = useVideoConfig();
  const realFile = item.transform?.realFile;
  if (!realFile) {
    return <VideoPlaceholder item={item} />;
  }
  const startFromFrames = item.source_in_us
    ? Math.round((item.source_in_us / 1_000_000) * fps)
    : 0;
  // Audio ducking: a voice-over reading over this exact shot must not
  // fight the clip's own embedded audio (real gameplay/AI clips often
  // carry their own game sound or Veo-generated ambience).
  const volume = item.transform?.hasVoiceOver ? 0.2 : 1;
  return (
    <OffthreadVideo
      src={staticFile(realFile)}
      startFrom={startFromFrames}
      volume={volume}
      style={{ width: "100%", height: "100%", objectFit: "cover" }}
    />
  );
}

function AudioItemRenderer({
  item,
  trackId,
  rowIndex,
}: {
  item: TrackItem;
  trackId: string;
  rowIndex: number;
}) {
  const realFile = item.transform?.realFile;
  if (!realFile) {
    return <AudioPlaceholder item={item} trackId={trackId} rowIndex={rowIndex} />;
  }
  return <Audio src={staticFile(realFile)} volume={item.gain ?? 1} />;
}

function AudioPlaceholder({
  item,
  trackId,
  rowIndex,
}: {
  item: TrackItem;
  trackId: string;
  rowIndex: number;
}) {
  // No real decodable audio asset exists yet in this round. Rather than
  // silently rendering nothing (which could look like a real, silent take
  // in a QA pass), show an on-screen marker for the duration of the item.
  // This composition intentionally does NOT include a <Audio> tag here --
  // wiring a real asset happens once the asset pipeline lands.
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 16,
          bottom: 16 + rowIndex * 30,
          fontFamily: "monospace",
          fontSize: 20,
          color: "rgba(255,255,0,0.85)",
          background: "rgba(0,0,0,0.5)",
          padding: "4px 8px",
          borderRadius: 4,
        }}
      >
        AUDIO PLACEHOLDER ({trackId}) - item: {item.id} - gerçek ses asset'i yok
      </div>
    </AbsoluteFill>
  );
}

function SubtitleItemRenderer({ item }: { item: TrackItem }) {
  const captionText = item.transform?.captionText;
  return (
    <AbsoluteFill
      style={{
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "center",
        paddingBottom: 220,
      }}
    >
      <div
        style={{
          fontFamily: "sans-serif",
          fontSize: 32,
          fontWeight: 700,
          color: "white",
          background: "rgba(0,0,0,0.55)",
          padding: "8px 20px",
          borderRadius: 8,
          maxWidth: "80%",
          textAlign: "center",
        }}
      >
        {captionText ?? `[altyazı placeholder — ${item.id}]`}
      </div>
    </AbsoluteFill>
  );
}

function GraphicTitle({ spec, opacity }: { spec: GraphicSpec; opacity: number }) {
  return (
    <AbsoluteFill
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        paddingTop: 140,
        opacity,
      }}
    >
      <div
        style={{
          fontFamily: "sans-serif",
          fontWeight: 900,
          fontSize: 72,
          color: spec.color ?? "white",
          textAlign: "center",
          textShadow: "0 4px 12px rgba(0,0,0,0.7)",
          maxWidth: "85%",
        }}
      >
        {spec.text ?? "Başlık"}
      </div>
      {spec.subtext ? (
        <div
          style={{
            fontFamily: "sans-serif",
            fontSize: 34,
            color: "rgba(255,255,255,0.9)",
            marginTop: 12,
          }}
        >
          {spec.subtext}
        </div>
      ) : null}
    </AbsoluteFill>
  );
}

function GraphicCtaCard({ spec, opacity }: { spec: GraphicSpec; opacity: number }) {
  return (
    <AbsoluteFill
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity,
      }}
    >
      <div
        style={{
          background: spec.color ?? "#1b8a3e",
          borderRadius: 24,
          padding: "28px 56px",
          boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
        }}
      >
        <div
          style={{
            fontFamily: "sans-serif",
            fontWeight: 800,
            fontSize: 44,
            color: "white",
          }}
        >
          {spec.text ?? "Şimdi İndir"}
        </div>
        {spec.subtext ? (
          <div
            style={{
              fontFamily: "sans-serif",
              fontSize: 24,
              color: "rgba(255,255,255,0.9)",
              marginTop: 6,
              textAlign: "center",
            }}
          >
            {spec.subtext}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
}

function GraphicLogo({ spec, opacity }: { spec: GraphicSpec; opacity: number }) {
  return (
    <AbsoluteFill
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "flex-end",
        padding: 40,
        opacity,
      }}
    >
      <div
        style={{
          width: 140,
          height: 140,
          borderRadius: 28,
          background: spec.color ?? "rgba(255,255,255,0.9)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "sans-serif",
          fontWeight: 900,
          fontSize: 28,
          color: "#111",
          textAlign: "center",
        }}
      >
        {spec.text ?? "LOGO"}
      </div>
    </AbsoluteFill>
  );
}

function GraphicChallengeCounter({ spec, frame }: { spec: GraphicSpec; frame: number }) {
  const count = Math.max(0, Math.floor(frame / 6));
  return (
    <AbsoluteFill
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          fontFamily: "monospace",
          fontWeight: 800,
          fontSize: 96,
          color: spec.color ?? "white",
          textShadow: "0 4px 12px rgba(0,0,0,0.7)",
        }}
      >
        {spec.text ? `${spec.text}: ` : ""}
        {count}
      </div>
    </AbsoluteFill>
  );
}

function GraphicLowerThird({ spec, opacity }: { spec: GraphicSpec; opacity: number }) {
  return (
    <AbsoluteFill
      style={{
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "flex-start",
        padding: 40,
        opacity,
      }}
    >
      <div
        style={{
          background: spec.color ?? "rgba(0,0,0,0.6)",
          borderLeft: "6px solid white",
          padding: "12px 20px",
        }}
      >
        <div style={{ fontFamily: "sans-serif", fontWeight: 800, fontSize: 32, color: "white" }}>
          {spec.text ?? "Alt bilgi"}
        </div>
        {spec.subtext ? (
          <div style={{ fontFamily: "sans-serif", fontSize: 20, color: "rgba(255,255,255,0.85)" }}>
            {spec.subtext}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
}

function GraphicItemRenderer({ item }: { item: TrackItem }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const spec = item.transform?.graphic;

  // Simple, template-independent fade-in so graphic overlays don't hard-cut.
  const fadeInFrames = Math.min(8, Math.floor(fps / 6));
  const localOpacityIn = interpolate(frame, [0, fadeInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const baseOpacity = (item.opacity ?? 1) * localOpacityIn;

  if (!spec) {
    return (
      <AbsoluteFill
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            fontFamily: "monospace",
            fontSize: 24,
            color: "rgba(255,255,255,0.8)",
          }}
        >
          [grafik placeholder — {item.id}: transform.graphic tanımsız]
        </div>
      </AbsoluteFill>
    );
  }

  switch (spec.template) {
    case "title":
      return <GraphicTitle spec={spec} opacity={baseOpacity} />;
    case "cta_card":
      return <GraphicCtaCard spec={spec} opacity={baseOpacity} />;
    case "logo":
      return <GraphicLogo spec={spec} opacity={baseOpacity} />;
    case "challenge_counter":
      return <GraphicChallengeCounter spec={spec} frame={frame} />;
    case "lower_third":
      return <GraphicLowerThird spec={spec} opacity={baseOpacity} />;
    default:
      return null;
  }
}

function TrackItemRenderer({
  item,
  track,
  audioRowIndex,
}: {
  item: TrackItem;
  track: Track;
  audioRowIndex: number;
}) {
  switch (track.kind) {
    case "video":
      return <VideoItemRenderer item={item} />;
    case "audio":
      return <AudioItemRenderer item={item} trackId={track.id} rowIndex={audioRowIndex} />;
    case "subtitle":
      return <SubtitleItemRenderer item={item} />;
    case "graphics":
      return <GraphicItemRenderer item={item} />;
    default:
      return null;
  }
}

function TrackLayer({ track, audioRowIndex }: { track: Track; audioRowIndex: number }) {
  return (
    <>
      {track.items.map((item) => (
        <Sequence
          key={item.id}
          from={item.start_frame}
          durationInFrames={item.duration_frames}
          name={`${track.id}:${item.id}`}
          layout="none"
        >
          <AbsoluteFill>
            <TrackItemRenderer item={item} track={track} audioRowIndex={audioRowIndex} />
          </AbsoluteFill>
        </Sequence>
      ))}
    </>
  );
}

// Render order: video first (bottom), then graphics, then audio markers,
// then subtitles on top.
const VISUAL_TRACK_ORDER: Track["kind"][] = ["video", "graphics", "audio", "subtitle"];

export const AdComposition: React.FC<AdCompositionProps> = ({ timeline }) => {
  const orderedTracks = [...timeline.tracks].sort(
    (a, b) => VISUAL_TRACK_ORDER.indexOf(a.kind) - VISUAL_TRACK_ORDER.indexOf(b.kind)
  );

  let audioRowIndex = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {orderedTracks.map((track) => {
        const rowIndex = track.kind === "audio" ? audioRowIndex++ : 0;
        return <TrackLayer key={track.id} track={track} audioRowIndex={rowIndex} />;
      })}
    </AbsoluteFill>
  );
};
