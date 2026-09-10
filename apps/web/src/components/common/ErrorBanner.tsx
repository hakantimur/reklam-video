interface ErrorBannerProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  retrying?: boolean;
}

/**
 * Gerçek hata durumlarını göstermek için tek yer. Renk (kırmızı çerçeve)
 * ile birlikte her zaman okunabilir metin taşır (spec §5.1 erişilebilirlik
 * kuralı: renk tek bilgi taşıyıcısı olamaz).
 */
export function ErrorBanner({ title, message, onRetry, retrying }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="flex flex-col gap-2 rounded-lg border border-error/50 bg-error/10 p-4 text-sm text-slate-100"
    >
      <p className="font-semibold text-error">{title ?? "Hata"}</p>
      <p className="text-slate-200">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          disabled={retrying}
          className="mt-1 w-fit rounded-md border border-error/60 px-3 py-1.5 text-error transition hover:bg-error/20 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {retrying ? "Yeniden deneniyor…" : "Yeniden dene"}
        </button>
      ) : null}
    </div>
  );
}
