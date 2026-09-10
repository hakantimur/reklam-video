import { useState, type FormEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { api, describeApiError } from "../api/client";
import type { CredentialProvider } from "../api/types";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { LoadingState } from "../components/common/LoadingState";

// Varsayılan proje kökü spec §3.2: "Windows Known Folder Documents altında
// LocalAdDirector/Projects". Gerçek değer backend/app/core/config.py içinde
// hesaplanıyor; burada yalnızca bilgi amaçlı gösteriliyor (kullanıcının
// kendi Documents klasörüne göre backend'de belirlenir).
const DEFAULT_PROJECTS_ROOT_HINT = "Belgelerim\\LocalAdDirector\\Projects";

export function SettingsPage() {
  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Ayarlar</h1>
        <p className="text-sm text-slate-400">
          Sağlayıcı anahtarları, proje klasörü, çalışma zamanı ve model kataloğu.
        </p>
      </div>

      <CredentialSection provider="openrouter" title="OpenRouter anahtarı" required />
      <CredentialSection provider="elevenlabs" title="ElevenLabs anahtarı (isteğe bağlı)" required={false} />
      <FolderSection />
      <RuntimeSection />
      <CatalogSection />
      <LogsSection />
    </div>
  );
}

function CredentialSection({
  provider,
  title,
  required,
}: {
  provider: CredentialProvider;
  title: string;
  required: boolean;
}) {
  const [apiKey, setApiKey] = useState("");

  const saveCredential = useMutation({
    mutationFn: () => api.saveCredential(provider, { api_key: apiKey }),
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!apiKey.trim()) return;
    saveCredential.mutate();
  }

  let statusText = "Doğrulanmadı";
  let statusClass = "text-slate-400";
  if (saveCredential.isPending) {
    statusText = "Kaydediliyor…";
  } else if (saveCredential.isSuccess) {
    statusText = `Kaydedildi (${saveCredential.data.masked_key})`;
    statusClass = "text-success";
  } else if (saveCredential.isError) {
    statusText = `Kaydedilemedi: ${describeApiError(saveCredential.error)}`;
    statusClass = "text-error";
  }

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-slate-700 bg-surface/60 p-5">
      <h2 className="text-sm font-semibold text-slate-100">
        {title}
        {!required ? <span className="ml-2 text-xs font-normal text-slate-500">isteğe bağlı</span> : null}
      </h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label htmlFor={`cred-${provider}`} className="mb-1 block text-sm text-slate-300">
            API anahtarı
          </label>
          <input
            id={`cred-${provider}`}
            type="password"
            autoComplete="off"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk-…"
            className="w-full rounded-md border border-slate-600 bg-bg px-3 py-2 text-sm text-slate-100 outline-none focus:border-accent"
          />
        </div>
        <button
          type="submit"
          disabled={saveCredential.isPending || !apiKey.trim()}
          className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Kaydet
        </button>
      </form>
      <p role="status" className={`text-xs ${statusClass}`}>
        Provider durumu: {statusText}
      </p>
      {!required ? (
        <p className="text-xs text-slate-500">
          Anahtar girilmeden proje oluşturma, malzeme yükleme ve yerel kurgu çalışmaya devam eder;
          yalnızca AI işlemleri devre dışı kalır.
        </p>
      ) : null}
    </section>
  );
}

function FolderSection() {
  return (
    <section className="flex flex-col gap-2 rounded-lg border border-slate-700 bg-surface/60 p-5">
      <h2 className="text-sm font-semibold text-slate-100">Proje klasörü</h2>
      <p className="text-sm text-slate-300">
        Varsayılan konum: <code className="text-slate-200">{DEFAULT_PROJECTS_ROOT_HINT}</code>
      </p>
      <p className="text-xs text-slate-500">
        Klasör değiştirme akışı (spec §7.4 proje taşıma) bu safhada uygulanmadı; şu an backend'in
        varsayılan yolu kullanılıyor.
      </p>
    </section>
  );
}

function RuntimeSection() {
  const diagnosticsQuery = useQuery({
    queryKey: ["diagnostics"],
    queryFn: api.diagnostics,
  });

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-slate-700 bg-surface/60 p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-100">Çalışma zamanı tanılaması</h2>
        <button
          type="button"
          onClick={() => diagnosticsQuery.refetch()}
          disabled={diagnosticsQuery.isFetching}
          className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {diagnosticsQuery.isFetching ? "Kontrol ediliyor…" : "Yeniden test et"}
        </button>
      </div>

      {diagnosticsQuery.isLoading ? <LoadingState label="Tanılama çalışıyor…" /> : null}

      {diagnosticsQuery.isError ? (
        <ErrorBanner
          message={describeApiError(diagnosticsQuery.error)}
          onRetry={() => diagnosticsQuery.refetch()}
          retrying={diagnosticsQuery.isFetching}
        />
      ) : null}

      {diagnosticsQuery.isSuccess ? (
        <dl className="grid grid-cols-1 gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
          {Object.entries(diagnosticsQuery.data).map(([key, value]) => (
            <div key={key} className="flex justify-between gap-2 rounded-md bg-bg/60 px-3 py-2">
              <dt className="text-slate-400">{key}</dt>
              <dd className="text-right text-slate-200">
                {typeof value === "object" ? JSON.stringify(value) : String(value)}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
    </section>
  );
}

function CatalogSection() {
  const modelsQuery = useQuery({
    queryKey: ["providers", "models"],
    queryFn: api.listModels,
    enabled: false,
  });

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-slate-700 bg-surface/60 p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-100">Model kataloğu</h2>
        <button
          type="button"
          onClick={() => modelsQuery.refetch()}
          disabled={modelsQuery.isFetching}
          className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {modelsQuery.isFetching ? "Yükleniyor…" : "Modelleri yenile"}
        </button>
      </div>

      {modelsQuery.fetchStatus === "idle" && !modelsQuery.data && !modelsQuery.error ? (
        <p className="text-sm text-slate-500">
          Katalog cache süresi 24 saat (spec §3.2). Görüntülemek için "Modelleri yenile" düğmesine
          basın.
        </p>
      ) : null}

      {modelsQuery.isFetching ? <LoadingState label="Katalog alınıyor…" /> : null}

      {modelsQuery.isError ? (
        <ErrorBanner
          message={describeApiError(modelsQuery.error)}
          onRetry={() => modelsQuery.refetch()}
          retrying={modelsQuery.isFetching}
        />
      ) : null}

      {modelsQuery.isSuccess ? (
        <div className="flex flex-col gap-1 text-sm text-slate-300">
          <p>
            {modelsQuery.data.models.length} model bulundu
            {modelsQuery.data.stale ? " (önbellek — 24 saattir doğrulanmadı)" : ""}.
          </p>
          <ul className="list-disc pl-5 text-xs text-slate-400">
            {modelsQuery.data.models.map((model) => (
              <li key={model.id}>
                {model.id} — {model.capability_status}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function LogsSection() {
  return (
    <section className="flex flex-col gap-2 rounded-lg border border-slate-700 bg-surface/60 p-5">
      <h2 className="text-sm font-semibold text-slate-100">Loglar</h2>
      <p className="text-sm text-slate-400">
        Uygulama içi log görüntüleyici bu safhada uygulanmadı. Şimdilik backend süreç çıktısını
        (konsol / <code className="text-slate-300">backend/</code> altındaki log dosyalarını) elle
        inceleyebilirsiniz.
      </p>
    </section>
  );
}
