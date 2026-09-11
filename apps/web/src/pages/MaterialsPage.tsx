import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, describeApiError } from "../api/client";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { LoadingState } from "../components/common/LoadingState";
import { useUIStore } from "../state/uiStore";

const TYPE_LABEL: Record<string, string> = {
  video: "Video",
  image: "Görsel",
  audio: "Ses",
  subtitle: "Altyazı",
  storyboard: "Storyboard",
  proxy: "Önizleme",
  export: "Dışa aktarım",
  evidence: "Kanıt",
};

const ORIGIN_LABEL: Record<string, string> = {
  user_upload: "Kullanıcı yükledi",
  emulator_capture: "Gerçek oynanış çekimi",
  provider_generation: "AI üretimi",
  derived: "Türetilmiş (render)",
  synthetic_test: "Test/sentetik",
};

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function MaterialsPage() {
  const activeProjectId = useUIStore((state) => state.activeProjectId);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Malzemeler</h1>
        <p className="text-sm text-slate-400">
          Projeye yüklenen ve üretilen görsel/ses malzemelerin arşivi.
        </p>
      </div>

      {!activeProjectId ? (
        <EmptyState
          title="Aktif proje seçilmedi"
          description="Malzeme arşivini görmek için önce Projeler ekranından bir proje açın."
          action={
            <Link
              to="/projeler"
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90"
            >
              Projelere git
            </Link>
          }
        />
      ) : (
        <MaterialsTable projectId={activeProjectId} />
      )}
    </div>
  );
}

function MaterialsTable({ projectId }: { projectId: string }) {
  const [typeFilter, setTypeFilter] = useState<string>("");

  const assetsQuery = useQuery({
    queryKey: ["assets", projectId, "all", typeFilter],
    queryFn: () => api.listAssets(projectId, typeFilter ? { type: typeFilter } : undefined),
  });

  if (assetsQuery.isLoading) {
    return <LoadingState label="Malzemeler yükleniyor…" />;
  }
  if (assetsQuery.isError) {
    return (
      <ErrorBanner
        title="Malzemeler alınamadı"
        message={describeApiError(assetsQuery.error)}
        onRetry={() => assetsQuery.refetch()}
      />
    );
  }

  const assets = assetsQuery.data ?? [];

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <label className="text-xs text-slate-400" htmlFor="type-filter">
          Tür
        </label>
        <select
          id="type-filter"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-md border border-slate-600 bg-bg px-2 py-1 text-xs text-slate-100"
        >
          <option value="">Tümü</option>
          {Object.entries(TYPE_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {assets.length === 0 ? (
        <EmptyState
          title="Henüz malzeme yok"
          description="Çekim, Taslak ve Çıktı adımlarında üretilen gerçek görsel/ses dosyaları burada görünür."
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-surface/40 text-xs uppercase tracking-wide text-slate-500">
                <th className="px-4 py-2 font-medium">Önizleme</th>
                <th className="px-4 py-2 font-medium">Tür</th>
                <th className="px-4 py-2 font-medium">Kaynak</th>
                <th className="px-4 py-2 font-medium">Süre</th>
                <th className="px-4 py-2 font-medium">Boyut</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((asset) => (
                <tr key={asset.id} className="border-b border-slate-800/60 text-slate-300">
                  <td className="px-4 py-2">
                    {asset.type === "video" || asset.type === "proxy" || asset.type === "export" ? (
                      <video
                        src={api.assetContentUrl(asset.id)}
                        controls
                        className="h-16 w-10 rounded bg-black object-cover"
                      />
                    ) : asset.type === "audio" ? (
                      <audio src={api.assetContentUrl(asset.id)} controls className="w-40" />
                    ) : (
                      <span className="text-xs text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2">{TYPE_LABEL[asset.type] ?? asset.type}</td>
                  <td className="px-4 py-2 text-xs text-slate-400">
                    {ORIGIN_LABEL[asset.origin] ?? asset.origin}
                  </td>
                  <td className="px-4 py-2 text-xs text-slate-500">
                    {asset.duration_us ? `${(asset.duration_us / 1_000_000).toFixed(1)} sn` : "—"}
                  </td>
                  <td className="px-4 py-2 text-xs text-slate-500">{formatBytes(asset.byte_size)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
