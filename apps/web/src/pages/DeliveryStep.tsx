import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { api, describeApiError } from "../api/client";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { LoadingState } from "../components/common/LoadingState";

const ACTIVE_JOB_STATES = new Set(["queued", "running"]);

export function DeliveryStep({ projectId }: { projectId: string }) {
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const planQuery = useQuery({ queryKey: ["plan", projectId], queryFn: () => api.getPlan(projectId) });
  const revisionId = planQuery.data?.id ?? null;

  const qaQuery = useQuery({
    queryKey: ["qa", projectId, revisionId],
    queryFn: () => api.getRevisionQA(projectId, revisionId as string),
    enabled: Boolean(revisionId),
  });

  const startExport = useMutation({
    mutationFn: () => api.startExport(projectId, revisionId as string),
    onSuccess: (job) => setActiveJobId(job.job_id),
  });

  const jobQuery = useQuery({
    queryKey: ["export-job", activeJobId],
    queryFn: () => api.getJob(activeJobId as string),
    enabled: Boolean(activeJobId),
    refetchInterval: (query) => (query.state.data && ACTIVE_JOB_STATES.has(query.state.data.state) ? 4000 : false),
  });
  const job = jobQuery.data;
  const isRunning = job ? ACTIVE_JOB_STATES.has(job.state) : false;
  const exportAssetId = job?.state === "succeeded" ? String(job.result_json.asset_id ?? "") || null : null;

  if (planQuery.isLoading) {
    return <LoadingState label="Çekim planı yükleniyor…" />;
  }
  if (!planQuery.data || !revisionId) {
    return (
      <EmptyState
        title="Henüz çekim planı yok"
        description="Önce Senaryo adımından bir çekim planı oluşturun."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-base font-semibold text-slate-100">Çıktı — QA ve dışa aktarma</h2>
        <p className="text-sm text-slate-400">
          QA, her sahnenin kabul edilebilir bir çekim/üretime ve geçerli teknik kaliteye sahip olup
          olmadığını kontrol eder. QA geçmeden dışa aktarma başlatılamaz — eksik bir reklam asla
          "hazır" olarak sunulmaz.
        </p>
      </div>

      {qaQuery.isLoading ? <LoadingState label="QA çalıştırılıyor…" /> : null}
      {qaQuery.isError ? (
        <ErrorBanner
          title="QA çalıştırılamadı"
          message={describeApiError(qaQuery.error)}
          onRetry={() => qaQuery.refetch()}
        />
      ) : null}

      {qaQuery.data ? (
        <div
          className={[
            "rounded-lg border p-4 text-sm",
            qaQuery.data.passed
              ? "border-emerald-700 bg-emerald-950/40 text-emerald-300"
              : "border-amber-700 bg-amber-950/30 text-amber-300",
          ].join(" ")}
        >
          <p className="font-semibold">{qaQuery.data.passed ? "QA geçti — dışa aktarılabilir" : "QA geçmedi"}</p>
          {qaQuery.data.issues.length > 0 ? (
            <ul className="mt-2 list-disc pl-5 text-xs">
              {qaQuery.data.issues.map((issue, index) => (
                <li key={index}>{issue}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <div className="flex flex-col gap-2 rounded-lg border border-slate-700 bg-surface/60 p-4">
        <button
          type="button"
          onClick={() => startExport.mutate()}
          disabled={!qaQuery.data?.passed || startExport.isPending || isRunning}
          className="self-start rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isRunning ? "Dışa aktarılıyor…" : "Dışa aktar"}
        </button>

        {startExport.isError ? (
          <ErrorBanner title="Dışa aktarma başlatılamadı" message={describeApiError(startExport.error)} />
        ) : null}
        {isRunning ? (
          <p className="text-xs text-slate-500">
            Remotion gerçek bir final render çalıştırıyor, bu birkaç dakika sürebilir…
          </p>
        ) : null}
        {job?.state === "failed" ? (
          <p className="text-xs text-error">
            Dışa aktarma başarısız oldu{job.error_code ? ` (${job.error_code})` : ""}.
          </p>
        ) : null}
        {exportAssetId ? (
          <div className="flex flex-col gap-2">
            <p className="text-xs text-emerald-400">Dışa aktarma tamamlandı.</p>
            <video
              src={api.assetContentUrl(exportAssetId)}
              controls
              className="w-full max-w-xs rounded-lg bg-black"
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}
