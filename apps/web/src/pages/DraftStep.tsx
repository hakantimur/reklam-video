import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, describeApiError } from "../api/client";
import type { AssetSummary, PlanShot, Take } from "../api/types";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { LoadingState } from "../components/common/LoadingState";

const ACTIVE_JOB_STATES = new Set(["queued", "running"]);
const FRAMES_PER_SECOND = 30;
const DEFAULT_VIDEO_MODEL = "google/veo-3.1-lite";

export function DraftStep({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const planQuery = useQuery({ queryKey: ["plan", projectId], queryFn: () => api.getPlan(projectId) });
  const timelineQuery = useQuery({
    queryKey: ["timeline", projectId],
    queryFn: () => api.getTimeline(projectId),
  });

  const buildTimeline = useMutation({
    mutationFn: () => api.buildTimeline(projectId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["timeline", projectId] }),
  });

  const [previewJobId, setPreviewJobId] = useState<string | null>(null);
  const startPreview = useMutation({
    mutationFn: () => api.startRenderPreview(projectId),
    onSuccess: (job) => setPreviewJobId(job.job_id),
  });
  const previewJobQuery = useQuery({
    queryKey: ["render-job", previewJobId],
    queryFn: () => api.getJob(previewJobId as string),
    enabled: Boolean(previewJobId),
    refetchInterval: (query) => (query.state.data && ACTIVE_JOB_STATES.has(query.state.data.state) ? 4000 : false),
  });
  const previewJob = previewJobQuery.data;
  const previewRunning = previewJob ? ACTIVE_JOB_STATES.has(previewJob.state) : false;
  const previewAssetId =
    previewJob?.state === "succeeded" ? String(previewJob.result_json.asset_id ?? "") || null : null;

  if (planQuery.isLoading) {
    return <LoadingState label="Çekim planı yükleniyor…" />;
  }
  if (planQuery.isError) {
    return (
      <ErrorBanner
        title="Çekim planı alınamadı"
        message={describeApiError(planQuery.error)}
        onRetry={() => planQuery.refetch()}
      />
    );
  }
  if (!planQuery.data) {
    return (
      <EmptyState
        title="Henüz çekim planı yok"
        description="Önce Senaryo adımından bir fikir seçip çekim planı oluşturun."
      />
    );
  }

  const aiShots = planQuery.data.shots.filter((s) => s.source_type === "ai_generated");
  const voiceShots = planQuery.data.shots.filter((s) => Boolean(s.voice_text));
  const videoTrack = timelineQuery.data?.tracks.find((t) => t.kind === "video");
  const filledCount = videoTrack?.items.filter((item) => item.asset_id).length ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-base font-semibold text-slate-100">Taslak — AI sahneler, seslendirme, önizleme</h2>
        <p className="text-sm text-slate-400">
          AI üretimi sahneleri gerçek bir video sağlayıcısıyla, seslendirmeleri gerçek bir TTS sesiyle
          üretin, sonra tüm planı tek bir önizleme videosunda birleştirin.{" "}
          <strong>Her sahne/seslendirme üretimi gerçek bir AI çağrısı yapar ve gerçek maliyete yol
          açar.</strong>
        </p>
      </div>

      {aiShots.length > 0 ? (
        <section className="flex flex-col gap-3">
          <h3 className="text-sm font-semibold text-slate-200">AI sahneleri</h3>
          {aiShots.map((shot) => (
            <AiSceneCard key={shot.id} projectId={projectId} shot={shot} />
          ))}
        </section>
      ) : null}

      {voiceShots.length > 0 ? (
        <section className="flex flex-col gap-3">
          <h3 className="text-sm font-semibold text-slate-200">Seslendirmeler</h3>
          {voiceShots.map((shot) => (
            <VoiceCard key={shot.id} projectId={projectId} shot={shot} />
          ))}
        </section>
      ) : null}

      <section className="flex flex-col gap-3 border-t border-slate-800 pt-4">
        <h3 className="text-sm font-semibold text-slate-200">Önizleme render'ı</h3>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => buildTimeline.mutate()}
            disabled={buildTimeline.isPending}
            className="rounded-md border border-accent px-3 py-1.5 text-xs font-semibold text-accent transition hover:bg-accent/10 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {buildTimeline.isPending ? "Oluşturuluyor…" : "Timeline oluştur"}
          </button>
          <button
            type="button"
            onClick={() => startPreview.mutate()}
            disabled={startPreview.isPending || previewRunning}
            className="rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {previewRunning ? "Render ediliyor…" : "Önizleme render et"}
          </button>
        </div>

        {buildTimeline.isError ? (
          <ErrorBanner title="Timeline oluşturulamadı" message={describeApiError(buildTimeline.error)} />
        ) : null}
        {startPreview.isError ? (
          <ErrorBanner title="Render başlatılamadı" message={describeApiError(startPreview.error)} />
        ) : null}

        {timelineQuery.data && videoTrack ? (
          <p className="text-xs text-slate-500">
            Timeline: {videoTrack.items.length} sahne,{" "}
            {(timelineQuery.data.duration_frames / FRAMES_PER_SECOND).toFixed(1)} sn — {filledCount}/
            {videoTrack.items.length} sahnede gerçek içerik var.
          </p>
        ) : null}

        {previewRunning ? (
          <p className="text-xs text-slate-500">
            Remotion gerçek bir render çalıştırıyor, bu birkaç dakika sürebilir…
          </p>
        ) : null}
        {previewJob?.state === "failed" ? (
          <p className="text-xs text-error">
            Render başarısız oldu{previewJob.error_code ? ` (${previewJob.error_code})` : ""}.
          </p>
        ) : null}
        {previewAssetId ? (
          <video
            src={api.assetContentUrl(previewAssetId)}
            controls
            className="w-full max-w-xs rounded-lg bg-black"
          />
        ) : null}
      </section>
    </div>
  );
}

function AiSceneCard({ projectId, shot }: { projectId: string; shot: PlanShot }) {
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const takesQuery = useQuery({
    queryKey: ["takes", projectId, shot.id],
    queryFn: () => api.listTakes(projectId, shot.id),
  });

  const generateScene = useMutation({
    mutationFn: () => api.generateScene(projectId, shot.id, DEFAULT_VIDEO_MODEL),
    onSuccess: (job) => setActiveJobId(job.job_id),
  });

  const jobQuery = useQuery({
    queryKey: ["generation-job", activeJobId],
    queryFn: () => api.getJob(activeJobId as string),
    enabled: Boolean(activeJobId),
    refetchInterval: (query) => (query.state.data && ACTIVE_JOB_STATES.has(query.state.data.state) ? 4000 : false),
  });
  const job = jobQuery.data;
  const isRunning = job ? ACTIVE_JOB_STATES.has(job.state) : false;
  const queryClient = useQueryClient();
  if (job?.state === "succeeded") {
    queryClient.invalidateQueries({ queryKey: ["takes", projectId, shot.id] });
  }

  const takes: Take[] = takesQuery.data ?? [];

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-slate-700 bg-surface/60 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-slate-100">
            Sahne {shot.order_index + 1} — {(shot.target_frames / FRAMES_PER_SECOND).toFixed(1)} sn hedef
          </h4>
          <p className="text-sm text-slate-300">{shot.purpose}</p>
        </div>
        <button
          type="button"
          onClick={() => generateScene.mutate()}
          disabled={generateScene.isPending || isRunning}
          className="shrink-0 rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isRunning ? "Üretiliyor…" : takes.length > 0 ? "Yeniden üret" : "Sahneyi üret"}
        </button>
      </div>

      {generateScene.isError ? (
        <ErrorBanner title="Sahne üretilemedi" message={describeApiError(generateScene.error)} />
      ) : null}
      {job?.state === "failed" ? (
        <p className="text-xs text-error">
          Üretim başarısız{job.error_code ? ` (${job.error_code})` : ""}.
        </p>
      ) : null}

      {takes.length > 0 ? (
        <div className="flex flex-col gap-2 border-t border-slate-800 pt-2">
          {takes.map((take) => (
            <video
              key={take.id}
              src={api.assetContentUrl(take.asset_id)}
              controls
              className="h-24 w-16 rounded bg-black object-cover"
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function VoiceCard({ projectId, shot }: { projectId: string; shot: PlanShot }) {
  const [selectedVoice, setSelectedVoice] = useState<string>("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const voicesQuery = useQuery({ queryKey: ["voices"], queryFn: api.listVoices });
  const assetsQuery = useQuery({
    queryKey: ["assets", projectId, "audio"],
    queryFn: () => api.listAssets(projectId, { type: "audio" }),
  });

  const voiceAssets: AssetSummary[] = (assetsQuery.data ?? []).filter(
    (a) => a.metadata_json.shot_id === shot.id && a.metadata_json.role === "voice_over",
  );

  const generateVoice = useMutation({
    mutationFn: () => api.generateVoice(projectId, shot.id, selectedVoice),
    onSuccess: (job) => setActiveJobId(job.job_id),
  });

  const jobQuery = useQuery({
    queryKey: ["generation-job", activeJobId],
    queryFn: () => api.getJob(activeJobId as string),
    enabled: Boolean(activeJobId),
    refetchInterval: (query) => (query.state.data && ACTIVE_JOB_STATES.has(query.state.data.state) ? 4000 : false),
  });
  const job = jobQuery.data;
  const isRunning = job ? ACTIVE_JOB_STATES.has(job.state) : false;
  if (job?.state === "succeeded") {
    queryClient.invalidateQueries({ queryKey: ["assets", projectId, "audio"] });
  }

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-slate-700 bg-surface/60 p-4">
      <div>
        <h4 className="text-sm font-semibold text-slate-100">Sahne {shot.order_index + 1}</h4>
        <p className="text-sm italic text-slate-300">“{shot.voice_text}”</p>
      </div>

      {voicesQuery.isError ? (
        <ErrorBanner title="Ses listesi alınamadı" message={describeApiError(voicesQuery.error)} />
      ) : (
        <div className="flex items-center gap-2">
          <select
            value={selectedVoice}
            onChange={(e) => setSelectedVoice(e.target.value)}
            className="w-full max-w-xs rounded-md border border-slate-600 bg-bg px-3 py-2 text-sm text-slate-100"
          >
            <option value="">Ses seçin…</option>
            {(voicesQuery.data ?? []).map((v) => (
              <option key={v.voice_id} value={v.voice_id}>
                {v.name ?? v.voice_id}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => generateVoice.mutate()}
            disabled={!selectedVoice || generateVoice.isPending || isRunning}
            className="shrink-0 rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isRunning ? "Üretiliyor…" : voiceAssets.length > 0 ? "Yeniden üret" : "Seslendirme üret"}
          </button>
        </div>
      )}

      {generateVoice.isError ? (
        <ErrorBanner title="Seslendirme üretilemedi" message={describeApiError(generateVoice.error)} />
      ) : null}
      {job?.state === "failed" ? (
        <p className="text-xs text-error">
          Üretim başarısız{job.error_code ? ` (${job.error_code})` : ""}.
        </p>
      ) : null}

      {voiceAssets.length > 0 ? (
        <div className="flex flex-col gap-1 border-t border-slate-800 pt-2">
          {voiceAssets.map((asset) => (
            <audio key={asset.id} src={api.assetContentUrl(asset.id)} controls className="w-full max-w-xs" />
          ))}
        </div>
      ) : null}
    </div>
  );
}
