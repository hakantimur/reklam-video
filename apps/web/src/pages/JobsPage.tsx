import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, describeApiError } from "../api/client";
import type { Job } from "../api/types";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { LoadingState } from "../components/common/LoadingState";
import { useUIStore } from "../state/uiStore";

const ACTIVE_STATES = new Set(["queued", "running", "waiting_provider"]);
const PAUSABLE_STATES = new Set(["queued", "running", "waiting_provider", "blocked"]);

const KIND_LABEL: Record<string, string> = {
  discover: "Keşif",
  capture_shot: "Çekim",
  generate_ai_scene: "AI sahne üretimi",
  generate_voice: "Seslendirme üretimi",
  render_preview: "Önizleme render",
  export_final: "Dışa aktarma",
  dummy_echo: "Test",
};

const STATE_LABEL: Record<string, string> = {
  queued: "Kuyrukta",
  running: "Çalışıyor",
  succeeded: "Tamamlandı",
  waiting_provider: "Sağlayıcı bekleniyor",
  paused: "Duraklatıldı",
  blocked: "Bloklandı",
  failed: "Başarısız",
  cancel_requested: "İptal isteniyor",
  cancelled: "İptal edildi",
  interrupted: "Kesintiye uğradı",
  submission_unknown: "Gönderim durumu belirsiz",
};

function elapsed(job: Job): string {
  if (!job.created_at) return "—";
  const end = ACTIVE_STATES.has(job.state) ? Date.now() : new Date(job.updated_at ?? job.created_at).getTime();
  const start = new Date(job.created_at).getTime();
  const seconds = Math.max(0, Math.round((end - start) / 1000));
  if (seconds < 60) return `${seconds} sn`;
  return `${Math.floor(seconds / 60)} dk ${seconds % 60} sn`;
}

export function JobsPage() {
  const activeProjectId = useUIStore((state) => state.activeProjectId);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">İşler</h1>
        <p className="text-sm text-slate-400">Kalıcı arka plan işleri ve durumları.</p>
      </div>

      {!activeProjectId ? (
        <EmptyState
          title="Aktif proje seçilmedi"
          description="İş geçmişini görmek için önce Projeler ekranından bir proje açın."
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
        <JobsTable projectId={activeProjectId} />
      )}
    </div>
  );
}

function JobsTable({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const jobsQuery = useQuery({
    queryKey: ["jobs", projectId],
    queryFn: () => api.listJobs(projectId),
    refetchInterval: 5000,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["jobs", projectId] });
  const pause = useMutation({ mutationFn: (id: string) => api.pauseJob(id), onSuccess: invalidate });
  const resume = useMutation({ mutationFn: (id: string) => api.resumeJob(id), onSuccess: invalidate });
  const cancel = useMutation({ mutationFn: (id: string) => api.cancelJob(id), onSuccess: invalidate });

  if (jobsQuery.isLoading) {
    return <LoadingState label="İşler yükleniyor…" />;
  }
  if (jobsQuery.isError) {
    return (
      <ErrorBanner
        title="İşler alınamadı"
        message={describeApiError(jobsQuery.error)}
        onRetry={() => jobsQuery.refetch()}
      />
    );
  }

  const jobs = jobsQuery.data ?? [];
  if (jobs.length === 0) {
    return (
      <EmptyState
        title="Henüz iş yok"
        description="Keşif, çekim, AI sahne/seslendirme üretimi, önizleme render'ı ve dışa aktarma işleri burada gerçek zamanlı görünür."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-800 bg-surface/40 text-xs uppercase tracking-wide text-slate-500">
            <th className="px-4 py-2 font-medium">Tür</th>
            <th className="px-4 py-2 font-medium">Durum</th>
            <th className="px-4 py-2 font-medium">Geçen süre</th>
            <th className="px-4 py-2 font-medium">Hata</th>
            <th className="px-4 py-2 font-medium">Eylem</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} className="border-b border-slate-800/60 text-slate-300">
              <td className="px-4 py-2">{KIND_LABEL[job.kind] ?? job.kind}</td>
              <td className="px-4 py-2">{STATE_LABEL[job.state] ?? job.state}</td>
              <td className="px-4 py-2 text-slate-500">{elapsed(job)}</td>
              <td className="px-4 py-2 text-xs text-error">{job.error_code ?? "—"}</td>
              <td className="px-4 py-2">
                <div className="flex gap-1">
                  {PAUSABLE_STATES.has(job.state) && job.state !== "paused" ? (
                    <button
                      type="button"
                      onClick={() => pause.mutate(job.id)}
                      className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-800"
                    >
                      Duraklat
                    </button>
                  ) : null}
                  {job.state === "paused" ? (
                    <button
                      type="button"
                      onClick={() => resume.mutate(job.id)}
                      className="rounded border border-accent px-2 py-1 text-[11px] text-accent hover:bg-accent/10"
                    >
                      Devam ettir
                    </button>
                  ) : null}
                  {ACTIVE_STATES.has(job.state) || job.state === "paused" ? (
                    <button
                      type="button"
                      onClick={() => cancel.mutate(job.id)}
                      className="rounded border border-red-800 px-2 py-1 text-[11px] text-red-400 hover:bg-red-950/40"
                    >
                      İptal et
                    </button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="border-t border-slate-800 px-4 py-2 text-[11px] text-slate-600">
        Maliyet takibi bu ekrana henüz bağlanmadı (bkz. docs/KNOWN_LIMITATIONS.md).
      </p>
    </div>
  );
}
