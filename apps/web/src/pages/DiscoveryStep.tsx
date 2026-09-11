import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { api, describeApiError } from "../api/client";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { LoadingState } from "../components/common/LoadingState";

const ACTIVE_JOB_STATES = new Set(["queued", "running"]);

export function DiscoveryStep({ projectId }: { projectId: string }) {
  const [selectedSerial, setSelectedSerial] = useState<string>("");
  const [selectedPackage, setSelectedPackage] = useState<string>("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const devicesQuery = useQuery({
    queryKey: ["devices"],
    queryFn: api.listDevices,
    refetchInterval: 5000,
  });

  const connectedDevices = (devicesQuery.data ?? []).filter((d) => d.state === "device");

  const appsQuery = useQuery({
    queryKey: ["device-apps", selectedSerial],
    queryFn: () => api.listDeviceApps(selectedSerial),
    enabled: Boolean(selectedSerial),
  });

  const startDiscovery = useMutation({
    mutationFn: () => api.startDiscovery(projectId, selectedSerial, selectedPackage),
    onSuccess: (job) => setActiveJobId(job.job_id),
  });

  const jobQuery = useQuery({
    queryKey: ["discover-job", activeJobId],
    queryFn: () => api.getJob(activeJobId as string),
    enabled: Boolean(activeJobId),
    refetchInterval: (query) => (query.state.data && ACTIVE_JOB_STATES.has(query.state.data.state) ? 3000 : false),
  });

  const job = jobQuery.data;
  const isRunning = job ? ACTIVE_JOB_STATES.has(job.state) : false;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-base font-semibold text-slate-100">Keşif — oyunu tanıma</h2>
        <p className="text-sm text-slate-400">
          Seçtiğiniz cihaz ve uygulamada, oyunu görerek karar veren bir AI en fazla 60 eylem veya
          10 dakika boyunca oyunu inceler (hangisi önce dolarsa). <strong>Bu, her eylemde gerçek
          bir AI görüntü çağrısı yapar ve gerçek maliyete yol açar.</strong> Keşif kayıtları
          reklam çekimi olarak kullanılmaz — yalnızca oyunun mekaniğini öğrenmek içindir.
        </p>
      </div>

      {devicesQuery.isLoading ? <LoadingState label="Cihazlar aranıyor…" /> : null}
      {devicesQuery.isError ? (
        <ErrorBanner
          title="Cihazlar alınamadı"
          message={describeApiError(devicesQuery.error)}
          onRetry={() => devicesQuery.refetch()}
        />
      ) : null}

      {devicesQuery.isSuccess && connectedDevices.length === 0 ? (
        <EmptyState
          title="Bağlı cihaz bulunamadı"
          description="Android emülatörünü başlatın ve ADB ile bağlı olduğundan emin olun, sonra bu sayfayı yenileyin."
        />
      ) : null}

      {connectedDevices.length > 0 ? (
        <div className="flex flex-col gap-3 rounded-lg border border-slate-700 bg-surface/60 p-4">
          <div>
            <label className="mb-1 block text-sm text-slate-300" htmlFor="device-select">
              Cihaz
            </label>
            <select
              id="device-select"
              value={selectedSerial}
              onChange={(e) => {
                setSelectedSerial(e.target.value);
                setSelectedPackage("");
              }}
              className="w-full rounded-md border border-slate-600 bg-bg px-3 py-2 text-sm text-slate-100"
            >
              <option value="">Seçin…</option>
              {connectedDevices.map((d) => (
                <option key={d.serial} value={d.serial}>
                  {d.model ?? d.serial} ({d.width}×{d.height})
                </option>
              ))}
            </select>
          </div>

          {selectedSerial ? (
            <div>
              <label className="mb-1 block text-sm text-slate-300" htmlFor="package-select">
                Uygulama
              </label>
              {appsQuery.isLoading ? <LoadingState label="Uygulamalar listeleniyor…" /> : null}
              {appsQuery.data ? (
                <select
                  id="package-select"
                  value={selectedPackage}
                  onChange={(e) => setSelectedPackage(e.target.value)}
                  className="w-full rounded-md border border-slate-600 bg-bg px-3 py-2 text-sm text-slate-100"
                >
                  <option value="">Seçin…</option>
                  {appsQuery.data.map((pkg) => (
                    <option key={pkg} value={pkg}>
                      {pkg}
                    </option>
                  ))}
                </select>
              ) : null}
            </div>
          ) : null}

          <button
            type="button"
            onClick={() => startDiscovery.mutate()}
            disabled={!selectedPackage || startDiscovery.isPending || isRunning}
            className="self-start rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isRunning ? "Keşif sürüyor…" : "Keşfi başlat"}
          </button>
        </div>
      ) : null}

      {startDiscovery.isError ? (
        <ErrorBanner title="Keşif başlatılamadı" message={describeApiError(startDiscovery.error)} />
      ) : null}

      {job ? (
        <div className="rounded-lg border border-slate-700 bg-surface/60 p-4 text-sm">
          <p className="text-slate-300">
            Durum: <span className="font-semibold text-slate-100">{job.state}</span>
          </p>
          {isRunning ? (
            <p className="mt-1 text-xs text-slate-500">
              AI oyunu izleyip deniyor, bu birkaç dakika sürebilir…
            </p>
          ) : null}
          {job.state === "succeeded" ? (
            <div className="mt-2 text-slate-300">
              <p>
                Güven: {String(job.result_json.confidence ?? "-")}
              </p>
              <p className="mt-1 italic text-slate-400">
                “{String(job.result_json.mechanic_summary ?? "")}”
              </p>
            </div>
          ) : null}
          {job.state === "failed" ? (
            <p className="mt-1 text-error">
              Keşif tamamlanamadı{job.error_code ? ` (${job.error_code})` : ""}. Beklenmeyen bir
              ekran (izin isteği, giriş ekranı vb.) çıkmış olabilir — cihazı kontrol edip tekrar
              deneyebilirsiniz.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
