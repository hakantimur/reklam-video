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
