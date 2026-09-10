import type {
  ApiErrorBody,
  BriefPayload,
  BriefResponse,
  CreateProjectPayload,
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
