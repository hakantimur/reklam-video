import { useHealth } from "../../api/useHealth";

/**
 * Backend bağlantı durumunu her zaman metinle gösterir (spec §5.1: renk
 * tek bilgi taşıyıcısı olamaz). Üç durum: kontrol ediliyor / bağlı /
 * bağlantı yok.
 */
export function ConnectionBadge() {
  const health = useHealth();

  let dotClass = "bg-slate-500";
  let label = "Bağlantı kontrol ediliyor…";

  if (health.isSuccess) {
    const healthy = health.data.status === "ok";
    dotClass = healthy ? "bg-success" : "bg-warning";
    label = healthy ? "Backend bağlı" : "Backend bağlı (kısıtlı)";
  } else if (health.isError) {
    dotClass = "bg-error";
    label = "Backend bağlantısı yok";
  }

  return (
    <div className="flex items-center gap-2 rounded-md border border-slate-700 bg-surface/60 px-3 py-1.5 text-xs text-slate-300">
      <span aria-hidden="true" className={`h-2 w-2 rounded-full ${dotClass}`} />
      <span>{label}</span>
    </div>
  );
}
