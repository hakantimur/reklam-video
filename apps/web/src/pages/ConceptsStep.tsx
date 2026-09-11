import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, describeApiError } from "../api/client";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { LoadingState } from "../components/common/LoadingState";

export function ConceptsStep({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();

  const conceptsQuery = useQuery({
    queryKey: ["concepts", projectId],
    queryFn: () => api.listConcepts(projectId),
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
    </div>
  );
}
