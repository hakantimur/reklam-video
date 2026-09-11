/**
 * TypeScript types mirroring packages/contracts/timeline.schema.json 1:1.
 *
 * This file is hand-written (not code-generated) but every field, its
 * optionality and its constraints are taken directly from the JSON Schema,
 * which remains the single source of truth (spec sec.16.1). Do not add
 * fields here that aren't representable by the schema; the schema does not
 * set `additionalProperties: false` anywhere, so the small set of
 * render-only extension fields below (grouped under `TrackItemRenderExt`)
 * are schema-valid additions, not a fork of the contract.
 *
 * Keep this file in sync by hand whenever
 * packages/contracts/timeline.schema.json changes.
 */

export const TIMELINE_SCHEMA_VERSION = 1 as const;

export interface Fps {
  num: number;
  den: number;
}

export interface Canvas {
  width: number;
  height: number;
}

export type TrackKind = "video" | "graphics" | "audio" | "subtitle";

/**
 * Graphics-track-only rendering hints. The schema leaves `transform` as an
 * open `object`, so graphics items pass their template selection and
 * content through `transform.graphic` rather than inventing a new
 * top-level schema field.
 */
export type GraphicTemplate =
  | "title"
  | "cta_card"
  | "lower_third"
  | "logo"
  | "challenge_counter";

export interface GraphicKeyframe {
  frame: number;
  /** Partial CSS-like transform properties this keyframe animates to. */
  x?: number;
  y?: number;
  scale?: number;
  opacity?: number;
}

export interface GraphicSpec {
  template: GraphicTemplate;
  text?: string;
  subtext?: string;
  logoAssetId?: string | null;
  color?: string;
  keyframes?: GraphicKeyframe[];
}

/**
 * Extra, schema-permitted fields placed inside `transform` for track items
 * that need extra render-time info the base contract intentionally leaves
 * generic (placeholder color for un-rendered video/audio placeholders, and
 * the graphics template payload above).
 */
export interface TrackItemRenderExt {
  /** Only meaningful for video/audio placeholder rendering in this round. */
  placeholderLabel?: string;
  placeholderColor?: string;
  /** Only meaningful for graphics-track items. */
  graphic?: GraphicSpec;
  /**
   * Safha 9: filename of a real asset staged into `apps/render/public/` by
   * `app/services/render.py` before invoking `remotion render` (Remotion's
   * documented way to serve a local file via `staticFile()`). When absent,
   * the item still renders — as its placeholder, never as a silent gap —
   * so an unfinished timeline is always visibly unfinished.
   */
  realFile?: string;
  /** Only meaningful for subtitle-track items — the real caption text to
   * burn in, straight from `Shot.caption_text`. */
  captionText?: string;
  /** Only meaningful for video-track items — true when this shot has a
   * voice-over playing over the same start/duration, so the clip's own
   * embedded audio should duck rather than fight it. */
  hasVoiceOver?: boolean;
  [key: string]: unknown;
}

export interface TrackItem {
  id: string;
  shot_id?: string | null;
  asset_id?: string | null;
  start_frame: number;
  duration_frames: number;
  source_in_us?: number | null;
  transform?: TrackItemRenderExt;
  opacity?: number;
  gain?: number;
  lock?: boolean;
}

export interface Track {
  id: string;
  kind: TrackKind;
  items: TrackItem[];
}

export interface Timeline {
  schema_version: 1;
  revision_id: string;
  fps: Fps;
  duration_frames: number;
  canvas: Canvas;
  tracks: Track[];
}

/** Runtime guard used before handing a Timeline to the composition. */
export function isTimeline(value: unknown): value is Timeline {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  if (v.schema_version !== TIMELINE_SCHEMA_VERSION) return false;
  if (typeof v.revision_id !== "string") return false;
  if (typeof v.duration_frames !== "number") return false;
  if (typeof v.fps !== "object" || v.fps === null) return false;
  if (typeof v.canvas !== "object" || v.canvas === null) return false;
  if (!Array.isArray(v.tracks)) return false;
  return true;
}
