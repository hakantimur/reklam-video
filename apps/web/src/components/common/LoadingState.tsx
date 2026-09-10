interface LoadingStateProps {
  label?: string;
}

/** Sonsuz/anlamsız spinner yerine gerçek durum metni gösterir (spec §2.3). */
export function LoadingState({ label = "Yükleniyor…" }: LoadingStateProps) {
  return (
    <div
      role="status"
      className="flex items-center gap-2 rounded-lg border border-slate-700 bg-surface/40 px-4 py-3 text-sm text-slate-300"
    >
      <span
        aria-hidden="true"
        className="h-3 w-3 animate-pulse rounded-full bg-accent"
      />
      <span>{label}</span>
    </div>
  );
}
