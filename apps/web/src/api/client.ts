import type {
  ApiErrorBody,
  AssetSummary,
  BriefPayload,
  BriefResponse,
  CaptureJob,
  Concept,
  CreateProjectPayload,
  DeviceSummary,
  DiscoverJob,
  ExportJob,
  GenerationJob,
  Job,
  PlanShot,
  QAReport,
  RenderJob,
  Revision,
  RevisionSummary,
  ReviewJob,
  ShotReview,
  Take,
  Timeline,
  VoiceOption,
  CredentialPayload,
  CredentialProvider,
  CredentialResponse,
  DiagnosticsResponse,
  HealthResponse,
  ModelCatalogResponse,
  ProjectSummary,
} from "./types";

/**
 * Local Ad Director backend adresi (spec §3.2: yerel servis 127.0.0.1:8765).
 * Uygulama paketlendiğinde bu UI ile backend aynı makinede, kullanıcı
 * tarafından değiştirilmediği sürece bu adreste koşar.
 */
export const API_BASE_URL = "http://127.0.0.1:8765/api/v1";

export type ApiErrorKind = "network" | "http" | "parse";

/**
 * Tüm client hataları bu sınıfa normalize edilir; ekranlar "bağlantı yok",
 * "uç nokta yok" ve "sunucu hatası" durumlarını ayırt edebilir (spec §5.4,
 * §8.1 hata şeması).
 */
export class ApiClientError extends Error {
  readonly kind: ApiErrorKind;
  readonly status?: number;
  readonly code?: string;
  readonly retryable: boolean;
  readonly details?: Record<string, unknown>;

  constructor(params: {
    kind: ApiErrorKind;
    message: string;
    status?: number;
    code?: string;
    retryable?: boolean;
    details?: Record<string, unknown>;
  }) {
    super(params.message);
    this.name = "ApiClientError";
    this.kind = params.kind;
    this.status = params.status;
    this.code = params.code;
    this.retryable = params.retryable ?? false;
    this.details = params.details;
  }
}

/**
 * Yerel oturum token'ı yer tutucusu.
 *
 * Spec §8.1: "Mutasyonlarda yerel session token ve Origin/Host doğrulaması
 * gerekir." Backend şu an yalnızca Origin/Host kontrolü yapıyor
 * (backend/app/security/local_origin.py); token üreten/doğrulayan bir uç
 * nokta henüz yok. Bu fonksiyon backend o kısmı uyguladığında tek noktadan
 * devreye alınabilsin diye burada duruyor — şu an gerçek bir token
 * üretmediği için `null` döner ve Authorization header'ı eklenmez.
 */
function getSessionToken(): string | null {
  return null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("Accept", "application/json");
  const token = getSessionToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(url, { ...init, headers });
  } catch {
    throw new ApiClientError({
      kind: "network",
      message:
        "Backend bağlantısı yok (127.0.0.1:8765). Servis çalışmıyor olabilir veya henüz başlatılmadı.",
      retryable: true,
    });
  }

  if (!response.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = null;
    }

    if (body?.error) {
      throw new ApiClientError({
        kind: "http",
        status: response.status,
        message: body.error.message,
        code: body.error.code,
        retryable: body.error.retryable,
        details: body.error.details,
      });
    }

    throw new ApiClientError({
      kind: "http",
      status: response.status,
      message:
        response.status === 404
          ? "Bu uç nokta backend tarafında henüz uygulanmadı."
          : `Sunucu hatası (HTTP ${response.status}).`,
      retryable: response.status >= 500,
    });
  }

  if (response.status === 204) {
    return undefined as T;
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiClientError({
      kind: "parse",
      message: "Sunucu yanıtı çözümlenemedi.",
      retryable: false,
    });
  }
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  diagnostics: () => request<DiagnosticsResponse>("/diagnostics"),

  saveCredential: (provider: CredentialProvider, payload: CredentialPayload) =>
    request<CredentialResponse>(`/settings/credentials/${provider}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  listModels: () => request<ModelCatalogResponse>("/providers/models"),

  listProjects: () =>
    request<{ items: ProjectSummary[] }>("/projects").then((response) => response.items),

  createProject: (payload: CreateProjectPayload) =>
    request<ProjectSummary>("/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getProject: (id: string) => request<ProjectSummary>(`/projects/${id}`),

  saveBrief: (projectId: string, payload: BriefPayload) =>
    request<BriefResponse>(`/projects/${projectId}/brief`, {
      method: "PUT",
      // Backend's `BriefPut` (backend/app/schemas/brief.py) uses frame-based
      // duration and micro-USD budget, not the seconds/whole-dollars the UI
      // works in — translate at the boundary rather than leaking backend
      // storage units into the form.
      body: JSON.stringify({
        product_name: payload.product_name,
        description: payload.description,
        cta: payload.cta,
        destination_url: payload.destination_url || null,
        audience: payload.audience ?? "",
        single_message: payload.single_message ?? "",
        objective: payload.objective || "Uygulama indirmesi",
        style_id: payload.style_id,
        language: payload.language,
        target_frames: Math.round(payload.duration_seconds * 30),
        fps_num: 30,
        fps_den: 1,
        placement_id: payload.placement_id,
        budget_microusd: Math.round(payload.budget_usd * 1_000_000),
      }),
    }),

  openProjectFolder: (id: string) =>
    request<void>(`/projects/${id}/open-folder`, { method: "POST" }),

  generateConcepts: (projectId: string, model?: string) =>
    request<Concept[]>(`/projects/${projectId}/concepts`, {
      method: "POST",
      body: JSON.stringify(model ? { model } : {}),
    }),

  listConcepts: (projectId: string) => request<Concept[]>(`/projects/${projectId}/concepts`),

  selectConcept: (projectId: string, conceptId: string) =>
    request<Concept>(`/projects/${projectId}/concepts/${conceptId}/select`, { method: "POST" }),

  generatePlan: (projectId: string, conceptId: string, model?: string) =>
    request<Revision>(`/projects/${projectId}/plan`, {
      method: "POST",
      body: JSON.stringify(model ? { concept_id: conceptId, model } : { concept_id: conceptId }),
    }),

  getPlan: (projectId: string) => request<Revision | null>(`/projects/${projectId}/plan`),

  listRevisions: (projectId: string) => request<RevisionSummary[]>(`/projects/${projectId}/revisions`),

  updateShotLocks: (projectId: string, shotId: string, locks: Partial<Record<string, boolean>>) =>
    request<PlanShot>(`/projects/${projectId}/shots/${shotId}/locks`, {
      method: "PATCH",
      body: JSON.stringify(locks),
    }),

  createVariation: (
    projectId: string,
    revisionId: string,
    shotInstructions: Record<string, string>,
    model?: string,
  ) =>
    request<Revision>(`/projects/${projectId}/revisions/${revisionId}/variation`, {
      method: "POST",
      body: JSON.stringify(model ? { shot_instructions: shotInstructions, model } : { shot_instructions: shotInstructions }),
    }),

  listDevices: () => request<DeviceSummary[]>("/devices"),

  listDeviceApps: (serial: string) => request<string[]>(`/devices/${serial}/apps`),

  startDiscovery: (projectId: string, serial: string, packageId: string) =>
    request<DiscoverJob>(`/projects/${projectId}/discover`, {
      method: "POST",
      body: JSON.stringify({ serial, package_id: packageId }),
    }),

  getJob: (jobId: string) => request<Job>(`/jobs/${jobId}`),

  listJobs: (projectId: string, state?: string) =>
    request<Job[]>(`/projects/${projectId}/jobs${state ? `?state=${state}` : ""}`),

  pauseJob: (jobId: string) => request<Job>(`/jobs/${jobId}/pause`, { method: "POST" }),
  resumeJob: (jobId: string) => request<Job>(`/jobs/${jobId}/resume`, { method: "POST" }),
  cancelJob: (jobId: string) => request<Job>(`/jobs/${jobId}/cancel`, { method: "POST" }),

  startCapture: (projectId: string, shotId: string, serial: string) =>
    request<CaptureJob>(`/projects/${projectId}/shots/${shotId}/capture`, {
      method: "POST",
      body: JSON.stringify({ serial }),
    }),

  listTakes: (projectId: string, shotId: string) =>
    request<Take[]>(`/projects/${projectId}/shots/${shotId}/takes`),

  selectTake: (projectId: string, shotId: string, takeId: string) =>
    request<{ shot_id: string; selected_take_id: string | null }>(
      `/projects/${projectId}/shots/${shotId}/takes/${takeId}/select`,
      { method: "POST" },
    ),

  assetContentUrl: (assetId: string) => `${API_BASE_URL}/assets/${assetId}/content`,

  listAssets: (projectId: string, params?: { type?: string; origin?: string }) => {
    const query = new URLSearchParams();
    if (params?.type) query.set("type", params.type);
    if (params?.origin) query.set("origin", params.origin);
    const qs = query.toString();
    return request<{ items: AssetSummary[] }>(
      `/projects/${projectId}/assets${qs ? `?${qs}` : ""}`,
    ).then((response) => response.items);
  },

  listVoices: () =>
    request<{ voices: VoiceOption[] }>("/providers/voices").then((response) => response.voices),

  generateScene: (projectId: string, shotId: string, videoModel: string) =>
    request<GenerationJob>(`/projects/${projectId}/shots/${shotId}/generate-scene`, {
      method: "POST",
      body: JSON.stringify({ video_model: videoModel }),
    }),

  generateVoice: (projectId: string, shotId: string, voiceId: string, language?: string) =>
    request<GenerationJob>(`/projects/${projectId}/shots/${shotId}/generate-voice`, {
      method: "POST",
      body: JSON.stringify(language ? { voice_id: voiceId, language } : { voice_id: voiceId }),
    }),

  buildTimeline: (projectId: string) =>
    request<Timeline>(`/projects/${projectId}/timeline/build`, { method: "POST" }),

  getTimeline: (projectId: string) => request<Timeline | null>(`/projects/${projectId}/timeline`),

  startRenderPreview: (projectId: string) =>
    request<RenderJob>(`/projects/${projectId}/render/preview`, { method: "POST" }),

  getRevisionQA: (projectId: string, revisionId: string) =>
    request<QAReport>(`/projects/${projectId}/revisions/${revisionId}/qa`),

  startExport: (projectId: string, revisionId: string) =>
    request<ExportJob>(`/projects/${projectId}/revisions/${revisionId}/export`, { method: "POST" }),

  getShotReview: (projectId: string, shotId: string) =>
    request<ShotReview | null>(`/projects/${projectId}/shots/${shotId}/review`),

  startShotReview: (projectId: string, shotId: string, model?: string) =>
    request<ReviewJob>(`/projects/${projectId}/shots/${shotId}/review`, {
      method: "POST",
      body: JSON.stringify(model ? { model } : {}),
    }),
};

/** Bir hatayı kullanıcıya gösterilecek tek satırlık Türkçe metne çevirir. */
export function describeApiError(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Bilinmeyen bir hata oluştu.";
}
