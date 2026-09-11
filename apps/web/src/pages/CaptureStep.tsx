import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, describeApiError } from "../api/client";
import type { PlanShot, Take } from "../api/types";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { LoadingState } from "../components/common/LoadingState";

const ACTIVE_JOB_STATES = new Set(["queued", "running"]);
const FRAMES_PER_SECOND = 30;

const TAKE_STATUS_LABEL: Record<string, string> = {
  pending: "İncelemede",
  accepted: "Kabul edildi",
  rejected: "Reddedildi",
  uncertain: "Belirsiz",
};

export function CaptureStep({ projectId }: { projectId: string }) {
  const planQuery = useQuery({
    queryKey: ["plan", projectId],
    queryFn: () => api.getPlan(projectId),
  });

  const devicesQuery = useQuery({
    queryKey: ["devices"],
    queryFn: api.listDevices,
    refetchInterval: 10000,
  });

  const connectedDevices = (devicesQuery.data ?? []).filter((d) => d.state === "device");
  const [selectedSerial, setSelectedSerial] = useState<string>("");

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

  const gameplayShots = planQuery.data.shots.filter((s) => s.source_type === "gameplay");

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-base font-semibold text-slate-100">Çekim — gerçek oynanış</h2>
        <p className="text-sm text-slate-400">
          Her sahne için AI, o sahnenin amacına ulaşana kadar gerçek cihazda oynar ve kaydı
          scrcpy ile alır. <strong>Her çekim gerçek bir AI görüntü çağrısı yapar ve gerçek
          maliyete yol açar.</strong> Çekimden önce Keşif adımıyla bu proje için bir oyun
          profili üretilmiş olmalıdır.
        </p>
      </div>

      <div className="flex flex-col gap-2 rounded-lg border border-slate-700 bg-surface/60 p-4">
        <label className="mb-1 block text-sm text-slate-300" htmlFor="capture-device-select">
          Çekim cihazı
        </label>
        {devicesQuery.isSuccess && connectedDevices.length === 0 ? (
          <p className="text-xs text-slate-500">
            Bağlı cihaz yok. Emülatörü başlatıp bu sayfayı yenileyin.
          </p>
        ) : (
          <select
            id="capture-device-select"
            value={selectedSerial}
            onChange={(e) => setSelectedSerial(e.target.value)}
            className="w-full max-w-sm rounded-md border border-slate-600 bg-bg px-3 py-2 text-sm text-slate-100"
          >
            <option value="">Seçin…</option>
            {connectedDevices.map((d) => (
              <option key={d.serial} value={d.serial}>
                {d.model ?? d.serial} ({d.width}×{d.height})
              </option>
            ))}
          </select>
        )}
      </div>

      {gameplayShots.length === 0 ? (
        <EmptyState
          title="Bu planda gerçek oynanış sahnesi yok"
          description="Çekim planındaki tüm sahneler AI üretimi veya grafik kompozisyonu — bu adımda yapılacak bir şey yok."
        />
      ) : (
        <div className="flex flex-col gap-4">
          {gameplayShots.map((shot) => (
            <GameplayShotCard
              key={shot.id}
              projectId={projectId}
              shot={shot}
              serial={selectedSerial}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function GameplayShotCard({
  projectId,
  shot,
  serial,
}: {
  projectId: string;
  shot: PlanShot;
  serial: string;
}) {
  const queryClient = useQueryClient();
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const takesQuery = useQuery({
    queryKey: ["takes", projectId, shot.id],
    queryFn: () => api.listTakes(projectId, shot.id),
  });

  const startCapture = useMutation({
    mutationFn: () => api.startCapture(projectId, shot.id, serial),
    onSuccess: (job) => setActiveJobId(job.job_id),
  });

  const selectTake = useMutation({
    mutationFn: (takeId: string) => api.selectTake(projectId, shot.id, takeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["takes", projectId, shot.id] });
      queryClient.invalidateQueries({ queryKey: ["plan", projectId] });
    },
  });

  const jobQuery = useQuery({
    queryKey: ["capture-job", activeJobId],
    queryFn: () => api.getJob(activeJobId as string),
    enabled: Boolean(activeJobId),
    refetchInterval: (query) => (query.state.data && ACTIVE_JOB_STATES.has(query.state.data.state) ? 3000 : false),
  });

  const job = jobQuery.data;
  const isRunning = job ? ACTIVE_JOB_STATES.has(job.state) : false;

  if (job && (job.state === "succeeded" || job.state === "failed")) {
    // A one-shot invalidation right after the job settles keeps this simple —
    // no need for the takes list itself to poll continuously.
    if (job.state === "succeeded") {
      queryClient.invalidateQueries({ queryKey: ["takes", projectId, shot.id] });
    }
  }

  const takes: Take[] = takesQuery.data ?? [];

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-slate-700 bg-surface/60 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            Sahne {shot.order_index + 1} — {(shot.target_frames / FRAMES_PER_SECOND).toFixed(1)} sn hedef
          </h3>
          <p className="text-sm text-slate-300">{shot.purpose}</p>
          {shot.desired_event ? (
            <p className="text-xs text-slate-500">Beklenen olay: {shot.desired_event}</p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() => startCapture.mutate()}
          disabled={!serial || startCapture.isPending || isRunning}
          className="shrink-0 rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isRunning ? "Çekim sürüyor…" : takes.length > 0 ? "Yeniden çek" : "Çek"}
        </button>
      </div>

      {startCapture.isError ? (
        <ErrorBanner title="Çekim başlatılamadı" message={describeApiError(startCapture.error)} />
      ) : null}

      {job && isRunning ? (
        <p className="text-xs text-slate-500">
          AI oyunu oynayıp kaydediyor, sahnenin amacına ulaşınca durduracak…
        </p>
      ) : null}
      {job?.state === "failed" ? (
        <p className="text-xs text-error">
          Çekim tamamlanamadı{job.error_code ? ` (${job.error_code})` : ""}. Beklenmeyen bir ekran
          çıkmış olabilir; kısmi kayıt reddedilmiş bir take olarak aşağıda görünür olabilir.
        </p>
      ) : null}

      {takesQuery.isLoading ? <LoadingState label="Çekimler yükleniyor…" /> : null}
      {takes.length > 0 ? (
        <div className="flex flex-col gap-2 border-t border-slate-800 pt-2">
          {takes.map((take) => (
            <div
              key={take.id}
              className="flex flex-col gap-1 rounded-md border border-slate-800 bg-bg/40 p-2 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
                <video
                  src={api.assetContentUrl(take.asset_id)}
                  controls
                  className="h-24 w-16 rounded bg-black object-cover"
                />
                <div className="text-xs">
                  <p className="text-slate-300">
                    Deneme {take.attempt} — {TAKE_STATUS_LABEL[take.status] ?? take.status}
                  </p>
                  {take.rejection_reason ? (
                    <p className="text-slate-500">{take.rejection_reason}</p>
                  ) : null}
                </div>
              </div>
              <button
                type="button"
                onClick={() => selectTake.mutate(take.id)}
                disabled={selectTake.isPending || take.status === "rejected"}
                className="self-start rounded-md border border-accent px-2 py-1 text-[11px] font-semibold text-accent transition hover:bg-accent/10 disabled:cursor-not-allowed disabled:opacity-40 sm:self-center"
              >
                Bu çekimi seç
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
