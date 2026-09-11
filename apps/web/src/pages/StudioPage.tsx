import { Link, Navigate, NavLink, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, describeApiError } from "../api/client";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { LoadingState } from "../components/common/LoadingState";
import { useUIStore } from "../state/uiStore";
import { BriefForm } from "./BriefForm";
import { CaptureStep } from "./CaptureStep";
import { ConceptsStep } from "./ConceptsStep";
import { DeliveryStep } from "./DeliveryStep";
import { DiscoveryStep } from "./DiscoveryStep";
import { DraftStep } from "./DraftStep";

interface StepDef {
  key: string;
  label: string;
  enabled: boolean;
}

// Spec §5.1: "Stüdyo adımları: Brief → Keşif → Senaryo → Çekim → Taslak → Düzenle → Çıktı."
// Yalnızca Düzenle (tam editör: sahne sırası değiştirme, crop, manuel
// senkron) sonraki bir safhada eklenecek (bkz. docs/PROGRESS.md). Devre
// dışı adımlar tıklanabilir sahte buton olarak değil, açık "henüz yok"
// durumuyla gösteriliyor.
const STEPS: StepDef[] = [
  { key: "brief", label: "Brief", enabled: true },
  { key: "kesif", label: "Keşif", enabled: true },
  { key: "senaryo", label: "Senaryo", enabled: true },
  { key: "cekim", label: "Çekim", enabled: true },
  { key: "taslak", label: "Taslak", enabled: true },
  { key: "duzenle", label: "Düzenle", enabled: false },
  { key: "cikti", label: "Çıktı", enabled: true },
];

export function StudioPage() {
  const activeProjectId = useUIStore((state) => state.activeProjectId);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Stüdyo</h1>
        <p className="text-sm text-slate-400">
          Brief → Keşif → Senaryo → Çekim → Taslak → Düzenle → Çıktı
        </p>
      </div>

      <StepTabs />

      {!activeProjectId ? (
        <EmptyState
          title="Aktif proje seçilmedi"
          description="Stüdyoda çalışmak için önce Projeler ekranından bir proje açın veya yeni proje oluşturun."
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
        <Routes>
          <Route path="/" element={<Navigate to="brief" replace />} />
          <Route path="brief" element={<BriefStep projectId={activeProjectId} />} />
          <Route path="kesif" element={<DiscoveryStep projectId={activeProjectId} />} />
          <Route path="senaryo" element={<ConceptsStep projectId={activeProjectId} />} />
          <Route path="cekim" element={<CaptureStep projectId={activeProjectId} />} />
          <Route path="taslak" element={<DraftStep projectId={activeProjectId} />} />
          <Route path="cikti" element={<DeliveryStep projectId={activeProjectId} />} />
          <Route path="*" element={<Navigate to="brief" replace />} />
        </Routes>
      )}
    </div>
  );
}

function StepTabs() {
  return (
    <div role="tablist" aria-label="Stüdyo adımları" className="flex flex-wrap gap-2">
      {STEPS.map((step, index) =>
        step.enabled ? (
          <NavLink
            key={step.key}
            to={step.key}
            role="tab"
            className={({ isActive }) =>
              [
                "rounded-md border px-3 py-1.5 text-xs font-medium",
                isActive
                  ? "border-accent bg-accent/20 text-accent"
                  : "border-accent/60 bg-accent/10 text-accent hover:bg-accent/20",
              ].join(" ")
            }
          >
            {index + 1}. {step.label}
          </NavLink>
        ) : (
          <div
            key={step.key}
            role="tab"
            aria-disabled="true"
            title="Bu adım ilerleyen bir safhada eklenecek"
            className="cursor-not-allowed rounded-md border border-slate-800 bg-surface/30 px-3 py-1.5 text-xs font-medium text-slate-600"
          >
            {index + 1}. {step.label}
            <span className="ml-1 text-[10px] text-slate-600">(yakında)</span>
          </div>
        ),
      )}
    </div>
  );
}

function BriefStep({ projectId }: { projectId: string }) {
  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
  });

  if (projectQuery.isLoading) {
    return <LoadingState label="Proje bilgisi yükleniyor…" />;
  }

  if (projectQuery.isError) {
    return (
      <ErrorBanner
        title="Proje yüklenemedi"
        message={describeApiError(projectQuery.error)}
        onRetry={() => projectQuery.refetch()}
        retrying={projectQuery.isFetching}
      />
    );
  }

  return <BriefForm projectId={projectId} />;
}
