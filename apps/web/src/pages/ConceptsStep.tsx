import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, describeApiError } from "../api/client";
import type { PlanShot } from "../api/types";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { LoadingState } from "../components/common/LoadingState";

const FRAMES_PER_SECOND = 30;

const SOURCE_TYPE_LABEL: Record<string, string> = {
  gameplay: "Gerçek oynanış",
  ai_generated: "AI üretimi",
  composed: "Grafik kompozisyon",
};

const LOCK_KEYS = ["visual", "voice", "caption", "timing"] as const;
const LOCK_LABEL: Record<(typeof LOCK_KEYS)[number], string> = {
  visual: "Görsel",
  voice: "Ses",
  caption: "Yazı",
  timing: "Süre",
};

export function ConceptsStep({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [instructions, setInstructions] = useState<Record<string, string>>({});

  const conceptsQuery = useQuery({
    queryKey: ["concepts", projectId],
    queryFn: () => api.listConcepts(projectId),
  });

  const planQuery = useQuery({
    queryKey: ["plan", projectId],
    queryFn: () => api.getPlan(projectId),
  });

  const generatePlan = useMutation({
    mutationFn: (conceptId: string) => api.generatePlan(projectId, conceptId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plan", projectId] });
    },
  });

  const generate = useMutation({
    mutationFn: () => api.generateConcepts(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["concepts", projectId] });
    },
  });

  const select = useMutation({
    mutationFn: (conceptId: string) => api.selectConcept(projectId, conceptId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["concepts", projectId] });
    },
  });

  const createVariation = useMutation({
    mutationFn: (revisionId: string) =>
      api.createVariation(
        projectId,
        revisionId,
        Object.fromEntries(Object.entries(instructions).filter(([, text]) => text.trim().length > 0)),
      ),
    onSuccess: () => {
      setInstructions({});
      queryClient.invalidateQueries({ queryKey: ["plan", projectId] });
    },
  });

  const concepts = conceptsQuery.data ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-100">Senaryo — Reklam fikirleri</h2>
          <p className="text-sm text-slate-400">
            Kaydettiğiniz brief'ten yönetmen (LLM) üç farklı reklam yaklaşımı üretir. Oyunun
            otomatik keşfi henüz yapılmadığından, model gerçek oynanış ayrıntısı uydurmaz —
            gerekli yerlerde bunu açıkça belirtir.
          </p>
        </div>
        <button
          type="button"
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
          className="shrink-0 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {generate.isPending ? "Üretiliyor…" : concepts.length > 0 ? "Yeniden üret" : "Fikir üret"}
        </button>
      </div>

      {generate.isError ? (
        <ErrorBanner
          title="Fikir üretilemedi"
          message={describeApiError(generate.error)}
          onRetry={() => generate.reset()}
        />
      ) : null}

      {conceptsQuery.isLoading ? <LoadingState label="Fikirler yükleniyor…" /> : null}

      {conceptsQuery.isError ? (
        <ErrorBanner
          title="Fikirler alınamadı"
          message={describeApiError(conceptsQuery.error)}
          onRetry={() => conceptsQuery.refetch()}
          retrying={conceptsQuery.isFetching}
        />
      ) : null}

      {conceptsQuery.isSuccess && concepts.length === 0 ? (
        <EmptyState
          title="Henüz fikir üretilmedi"
          description="Yukarıdaki 'Fikir üret' düğmesiyle brief'ten üç farklı reklam yaklaşımı oluşturabilirsiniz. Bu, gerçek bir AI çağrısıdır ve seçtiğiniz sağlayıcı üzerinden küçük bir maliyete yol açabilir."
        />
      ) : null}

      {concepts.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {concepts.map((concept) => (
            <div
              key={concept.id}
              className={[
                "flex flex-col gap-2 rounded-lg border p-4",
                concept.selected ? "border-accent bg-accent/10" : "border-slate-700 bg-surface/60",
              ].join(" ")}
            >
              <h3 className="text-sm font-semibold text-slate-100">{concept.angle}</h3>
              <p className="text-sm italic text-slate-300">“{concept.hook}”</p>
              <p className="text-xs text-slate-400">{concept.rationale}</p>
              {concept.claim_refs.length > 0 ? (
                <ul className="mt-1 flex flex-wrap gap-1">
                  {concept.claim_refs.map((ref) => (
                    <li
                      key={ref}
                      className="rounded border border-slate-600 px-1.5 py-0.5 text-[10px] text-slate-400"
                    >
                      {ref}
                    </li>
                  ))}
                </ul>
              ) : null}
              <button
                type="button"
                onClick={() => select.mutate(concept.id)}
                disabled={select.isPending || concept.selected}
                className="mt-2 rounded-md border border-accent px-3 py-1.5 text-xs font-semibold text-accent transition hover:bg-accent/10 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {concept.selected ? "Seçili" : "Bu fikri seç"}
              </button>
            </div>
          ))}
        </div>
      ) : null}

      {(() => {
        const selectedConcept = concepts.find((c) => c.selected);
        if (!selectedConcept) return null;
        const currentRevisionId = planQuery.data?.id;
        return (
          <div className="mt-2 flex flex-col gap-4 border-t border-slate-800 pt-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-slate-100">Çekim planı</h2>
                <p className="text-sm text-slate-400">
                  Seçili fikirden ("{selectedConcept.angle}") sahne sahne bir çekim planı üretir.
                  Oyun keşfi henüz yapılmadığından gerçek oynanış sahneleri genel amaçlarla
                  planlanır; gerçek çekim sırası ve olay tespiti sonraki bir safhada eklenecek.
                </p>
              </div>
              <button
                type="button"
                onClick={() => generatePlan.mutate(selectedConcept.id)}
                disabled={generatePlan.isPending}
                className="shrink-0 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {generatePlan.isPending
                  ? "Üretiliyor…"
                  : planQuery.data
                    ? "Yeniden üret"
                    : "Çekim planı oluştur"}
              </button>
            </div>

            {generatePlan.isError ? (
              <ErrorBanner
                title="Çekim planı üretilemedi"
                message={describeApiError(generatePlan.error)}
                onRetry={() => generatePlan.reset()}
              />
            ) : null}

            {planQuery.isLoading ? <LoadingState label="Çekim planı yükleniyor…" /> : null}

            {planQuery.data ? (
              <div className="flex flex-col gap-2">
                {planQuery.data.shots.map((shot) => (
                  <ShotCard
                    key={shot.id}
                    projectId={projectId}
                    shot={shot}
                    instruction={instructions[shot.id] ?? ""}
                    onInstructionChange={(text) =>
                      setInstructions((prev) => ({ ...prev, [shot.id]: text }))
                    }
                  />
                ))}
              </div>
            ) : null}

            {planQuery.data ? (
              <div className="flex flex-col gap-2 border-t border-slate-800 pt-4">
                <div>
                  <h3 className="text-sm font-semibold text-slate-200">Revizyon — yeni bir varyasyon oluştur</h3>
                  <p className="text-xs text-slate-400">
                    Yukarıda değiştirmek istediğiniz sahnelere talimat yazın (kilitli alanlar
                    korunur), sonra "Varyasyon oluştur"a basın. Bu, mevcut planı silmez — yeni bir
                    revizyon ekler; talimat yazılmayan sahneler (çekimleri ve seslendirmeleriyle
                    birlikte) değişmeden yeni revizyona taşınır.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => currentRevisionId && createVariation.mutate(currentRevisionId)}
                  disabled={
                    !currentRevisionId ||
                    createVariation.isPending ||
                    Object.values(instructions).every((text) => text.trim().length === 0)
                  }
                  className="w-fit rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {createVariation.isPending ? "Oluşturuluyor…" : "Varyasyon oluştur"}
                </button>
                {createVariation.isError ? (
                  <ErrorBanner
                    title="Varyasyon oluşturulamadı"
                    message={describeApiError(createVariation.error)}
                    onRetry={() => createVariation.reset()}
                  />
                ) : null}
                {createVariation.isSuccess ? (
                  <p className="text-xs text-slate-400">
                    Yeni revizyon (#{createVariation.data.sequence_no}) oluşturuldu:{" "}
                    {createVariation.data.change_summary}
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>
        );
      })()}
    </div>
  );
}

function ShotCard({
  projectId,
  shot,
  instruction,
  onInstructionChange,
}: {
  projectId: string;
  shot: PlanShot;
  instruction: string;
  onInstructionChange: (text: string) => void;
}) {
  const queryClient = useQueryClient();
  const toggleLock = useMutation({
    mutationFn: (patch: Partial<Record<string, boolean>>) => api.updateShotLocks(projectId, shot.id, patch),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["plan", projectId] }),
  });

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-slate-700 bg-surface/60 p-3">
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold text-slate-200">
          Sahne {shot.order_index + 1} — {SOURCE_TYPE_LABEL[shot.source_type]}
        </span>
        <span className="text-slate-500">{(shot.target_frames / FRAMES_PER_SECOND).toFixed(1)} sn</span>
      </div>
      <p className="text-sm text-slate-300">{shot.purpose}</p>
      {shot.desired_event ? (
        <p className="text-xs text-slate-500">Beklenen olay: {shot.desired_event}</p>
      ) : null}
      {shot.caption_text ? (
        <p className="text-xs text-slate-400">Ekran yazısı: “{shot.caption_text}”</p>
      ) : null}
      {shot.voice_text ? <p className="text-xs text-slate-400">Seslendirme: “{shot.voice_text}”</p> : null}

      <div className="flex flex-wrap items-center gap-3 border-t border-slate-800 pt-2">
        <span className="text-[10px] uppercase tracking-wide text-slate-500">Kilitler:</span>
        {LOCK_KEYS.map((key) => (
          <label key={key} className="flex items-center gap-1 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={Boolean(shot.locks[key])}
              disabled={toggleLock.isPending}
              onChange={(e) => toggleLock.mutate({ [key]: e.target.checked })}
              className="accent-accent"
            />
            {LOCK_LABEL[key]}
          </label>
        ))}
      </div>
      {toggleLock.isError ? (
        <ErrorBanner title="Kilit güncellenemedi" message={describeApiError(toggleLock.error)} />
      ) : null}

      <textarea
        value={instruction}
        onChange={(e) => onInstructionChange(e.target.value)}
        placeholder="Bu sahneyi değiştirmek için bir talimat yazın (boş bırakırsanız sahne değişmeden taşınır)…"
        rows={2}
        className="w-full rounded-md border border-slate-600 bg-bg px-2 py-1.5 text-xs text-slate-100 placeholder:text-slate-600"
      />
    </div>
  );
}
