/**
 * Backend API sözleşmesi.
 *
 * Kaynak: docs/IMPLEMENTATION_SPEC_TR.md §7.2 (tablo alanları) ve §8.1
 * (uç nokta listesi). Bu dosyadaki tipler backend'in HENÜZ UYGULAMADIĞI
 * uç noktaları da içerir (bkz. docs/PROGRESS.md — şu an yalnızca
 * GET /health ve GET /diagnostics gerçek). Var olmayan bir uç noktaya
 * yapılan istek apps/web/src/api/client.ts içinde gerçek bir bağlantı/
 * 404 hatası olarak ele alınır; bu dosyadaki tipler asla sahte veri
 * üretmek için kullanılmaz.
 */

export interface HealthResponse {
  status: "ok" | "degraded";
  db: { ok: boolean; error: string | null };
  disk: Record<string, unknown>;
  worker: { status: string };
}

export type DiagnosticsResponse = Record<string, unknown>;

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    retryable: boolean;
    details: Record<string, unknown>;
    job_id: string | null;
  };
}

// --- projects (spec §7.2 "projects" tablosu) ---------------------------

export interface ProjectSummary {
  id: string;
  name: string;
  slug: string;
  root_path: string;
  locale: string;
  active_revision_id: string | null;
  created_at: string;
  updated_at: string;
  version: number;
  /** Backend'de henüz karşılığı olmayabilecek, Projeler ekranı §5.2 sözleşmesi alanları. */
  last_export_at?: string | null;
  last_opened_at?: string | null;
}

export interface CreateProjectPayload {
  name: string;
  locale?: string;
}

// --- brief (spec §7.2 "briefs" + "brand_profiles" tabloları, §4.2) -----

export interface BriefPayload {
  product_name: string;
  description: string;
  cta: string;
  destination_url?: string;
  audience?: string;
  single_message?: string;
  objective?: string;
  language: string;
  style_id: string;
  duration_seconds: number;
  placement_id: string;
  budget_usd: number;
}

export interface BriefResponse extends BriefPayload {
  id: string;
  project_id: string;
  revision: number;
}

// --- concepts (spec §10.2 ConceptSet, §8.1 POST/GET /projects/{id}/concepts) ---

export interface Concept {
  id: string;
  angle: string;
  hook: string;
  rationale: string;
  claim_refs: string[];
  selected: boolean;
}

// --- devices / discovery (spec §11, §8.1) ---

export interface DeviceSummary {
  serial: string;
  state: string;
  model: string | null;
  width: number | null;
  height: number | null;
  orientation: number | null;
}

export interface DiscoverJob {
  job_id: string;
  revision_id: string | null;
  state: string;
}

export interface Job {
  id: string;
  project_id: string;
  kind: string;
  state: string;
  result_json: Record<string, unknown>;
  error_code: string | null;
  created_at?: string;
  updated_at?: string;
}

// --- plan (spec §10.2 Script+ShotPlan, §8.1 POST/GET /projects/{id}/plan) ---

export interface PlanShot {
  id: string;
  order_index: number;
  source_type: "gameplay" | "ai_generated" | "composed";
  purpose: string;
  desired_event: string | null;
  target_frames: number;
  caption_text: string | null;
  voice_text: string | null;
  locks: Record<string, boolean>;
}

export interface Revision {
  id: string;
  sequence_no: number;
  status: string;
  change_summary: string | null;
  shots: PlanShot[];
}

export interface RevisionSummary {
  id: string;
  parent_id: string | null;
  sequence_no: number;
  status: string;
  change_summary: string | null;
  shot_count: number;
  created_at: string;
}

// --- capture / takes (spec §11, §7.2 "takes" tablosu, §8.1 Safha 7) -----

export interface CaptureJob {
  job_id: string;
  state: string;
}

export interface Take {
  id: string;
  shot_id: string;
  asset_id: string;
  attempt: number;
  status: "pending" | "accepted" | "rejected" | "uncertain";
  rejection_reason: string | null;
  quality_json: Record<string, unknown>;
  created_at: string;
}

// --- generation (Safha 8: AI sahne + seslendirme) ----------------------

export interface GenerationJob {
  job_id: string;
  state: string;
}

export interface VoiceOption {
  voice_id: string;
  name: string | null;
}

export interface AssetSummary {
  id: string;
  project_id: string;
  type: string;
  origin: string;
  relative_path: string;
  byte_size: number;
  duration_us: number | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

// --- timeline / render (spec §16, Safha 9) ------------------------------

export interface TimelineTrackItem {
  id: string;
  shot_id: string | null;
  asset_id: string | null;
  start_frame: number;
  duration_frames: number;
}

export interface TimelineTrack {
  id: string;
  kind: "video" | "graphics" | "audio" | "subtitle";
  items: TimelineTrackItem[];
}

export interface Timeline {
  schema_version: number;
  revision_id: string;
  fps: { num: number; den: number };
  duration_frames: number;
  canvas: { width: number; height: number };
  tracks: TimelineTrack[];
}

export interface RenderJob {
  job_id: string;
  state: string;
}

// --- QA / export (Safha 11) --------------------------------------------

export interface QAReport {
  revision_id: string;
  passed: boolean;
  issues: string[];
}

export interface ExportJob {
  job_id: string;
  state: string;
}

// --- content review (spec §10: reviewer ajanı) --------------------------

export interface ReviewJob {
  job_id: string;
  state: string;
}

export interface ShotReview {
  outcome: "pass" | "fail" | "uncertain";
  reasoning: string;
  defects: string[];
  reviewer_model: string | null;
  created_at: string;
}

// --- settings / credentials (spec §8.1 PUT /settings/credentials/{provider}) ---

export type CredentialProvider = "openrouter" | "elevenlabs";

export interface CredentialPayload {
  api_key: string;
}

export interface CredentialResponse {
  provider: CredentialProvider;
  masked_key: string;
  saved_at: string;
}

// --- model katalogu (spec §9.1) ----------------------------------------

export interface ModelCatalogEntry {
  id: string;
  roles: string[];
  input_modalities: string[];
  output_modalities: string[];
  supports_tools: boolean | null;
  supported_durations_s: number[];
  supported_ratios: string[];
  supported_resolutions: string[];
  supports_reference_images: boolean | null;
  supports_native_audio: boolean | null;
  supports_audio_driven_lipsync: boolean | null;
  pricing: Record<string, unknown>;
  capability_status: "unverified" | "compatible" | "incompatible";
  fetched_at: string;
}

export interface ModelCatalogResponse {
  models: ModelCatalogEntry[];
  cache_age_seconds: number | null;
  stale: boolean;
}
