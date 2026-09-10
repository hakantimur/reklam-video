import { useState, type FormEvent, type ReactNode } from "react";
import { useMutation } from "@tanstack/react-query";

import { api, describeApiError } from "../api/client";
import type { BriefPayload } from "../api/types";

interface BriefFormProps {
  projectId: string;
}

type FieldErrors = Partial<Record<"product_name" | "description" | "cta", string>>;

const REQUIRED_MESSAGE = "Bu alan zorunludur.";

const DEFAULT_BRIEF: BriefPayload = {
  product_name: "",
  description: "",
  cta: "",
  destination_url: "",
  audience: "",
  single_message: "",
  objective: "Uygulama indirmesi",
  language: "tr",
  style_id: "natural_gameplay",
  duration_seconds: 20,
  placement_id: "facebook_reels_9x16",
  budget_usd: 5,
};

const LANGUAGE_OPTIONS = [
  { value: "tr", label: "Türkçe" },
  { value: "en", label: "İngilizce" },
];

const STYLE_OPTIONS = [
  { value: "natural_gameplay", label: "Doğal oyuncu tepkisi + gerçek oynanış" },
  { value: "challenge", label: "Meydan okuma" },
  { value: "quick_break", label: "Kısa mola" },
];

const PLACEMENT_OPTIONS = [
  { value: "facebook_reels_9x16", label: "Facebook Reels — 9:16" },
  { value: "16x9", label: "16:9" },
  { value: "1x1", label: "1:1" },
  { value: "4x5", label: "4:5" },
];

/** Spec §4.2 ve §5.2 Brief ekran sözleşmesi. */
export function BriefForm({ projectId }: BriefFormProps) {
  const [brief, setBrief] = useState<BriefPayload>(DEFAULT_BRIEF);
  const [errors, setErrors] = useState<FieldErrors>({});

  const saveBrief = useMutation({
    mutationFn: (payload: BriefPayload) => api.saveBrief(projectId, payload),
  });

  function updateField<K extends keyof BriefPayload>(key: K, value: BriefPayload[K]) {
    setBrief((prev) => ({ ...prev, [key]: value }));
  }

  function validate(): boolean {
    const nextErrors: FieldErrors = {};
    if (!brief.product_name.trim()) nextErrors.product_name = REQUIRED_MESSAGE;
    if (!brief.description.trim()) nextErrors.description = REQUIRED_MESSAGE;
    if (!brief.cta.trim()) nextErrors.cta = REQUIRED_MESSAGE;
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!validate()) return;
    saveBrief.mutate(brief);
  }

  let saveStatusText = "";
  if (saveBrief.isPending) saveStatusText = "Kaydediliyor…";
  else if (saveBrief.isSuccess) saveStatusText = "Kaydedildi";
  else if (saveBrief.isError) saveStatusText = `Kaydedilemedi: ${describeApiError(saveBrief.error)}`;

  return (
    <form onSubmit={handleSubmit} className="flex max-w-3xl flex-col gap-6">
      <section className="flex flex-col gap-4 rounded-lg border border-slate-700 bg-surface/60 p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
          Zorunlu alanlar
        </h2>

        <Field
          id="brief-product-name"
          label="Ürün adı"
          error={errors.product_name}
        >
          <input
            id="brief-product-name"
            type="text"
            value={brief.product_name}
            onChange={(e) => updateField("product_name", e.target.value)}
            aria-invalid={Boolean(errors.product_name)}
            aria-describedby={errors.product_name ? "brief-product-name-error" : undefined}
            className={inputClass(Boolean(errors.product_name))}
            placeholder="ör. Synova"
          />
        </Field>

        <Field
          id="brief-description"
          label="Kısa gerçek açıklama"
          error={errors.description}
          hint="Yalnızca gerçekten doğru olan özellikleri yazın; doğrulanmamış iddia üretilmeyecektir."
        >
          <textarea
            id="brief-description"
            value={brief.description}
            onChange={(e) => updateField("description", e.target.value)}
            aria-invalid={Boolean(errors.description)}
            aria-describedby={errors.description ? "brief-description-error" : undefined}
            className={`${inputClass(Boolean(errors.description))} min-h-[88px] resize-y`}
            placeholder="ör. Sırayı hatırlama mekaniğine dayalı, kısa turlu bir hafıza oyunu."
          />
        </Field>

        <Field id="brief-cta" label="Hedef / CTA" error={errors.cta}>
          <input
            id="brief-cta"
            type="text"
            value={brief.cta}
            onChange={(e) => updateField("cta", e.target.value)}
            aria-invalid={Boolean(errors.cta)}
            aria-describedby={errors.cta ? "brief-cta-error" : undefined}
            className={inputClass(Boolean(errors.cta))}
            placeholder="ör. Şimdi indir"
          />
        </Field>

        <Field id="brief-destination-url" label="Bağlantı (isteğe bağlı)">
          <input
            id="brief-destination-url"
            type="url"
            value={brief.destination_url}
            onChange={(e) => updateField("destination_url", e.target.value)}
            className={inputClass(false)}
            placeholder="https://…"
          />
        </Field>
      </section>

      <section className="flex flex-col gap-4 rounded-lg border border-slate-700 bg-surface/60 p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
          Diğer alanlar (varsayılanla dolu)
        </h2>

        <Field id="brief-audience" label="Hedef kitle">
          <input
            id="brief-audience"
            type="text"
            value={brief.audience}
            onChange={(e) => updateField("audience", e.target.value)}
            className={inputClass(false)}
            placeholder="ör. 18-34 yaş, mobil oyuncular"
          />
        </Field>

        <Field id="brief-single-message" label="Ana reklam mesajı">
          <input
            id="brief-single-message"
            type="text"
            value={brief.single_message}
            onChange={(e) => updateField("single_message", e.target.value)}
            className={inputClass(false)}
          />
        </Field>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field id="brief-language" label="Dil">
            <select
              id="brief-language"
              value={brief.language}
              onChange={(e) => updateField("language", e.target.value)}
              className={inputClass(false)}
            >
              {LANGUAGE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="brief-style" label="Tarz">
            <select
              id="brief-style"
              value={brief.style_id}
              onChange={(e) => updateField("style_id", e.target.value)}
              className={inputClass(false)}
            >
              {STYLE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="brief-duration" label="Süre (saniye)" hint="İzin verilen aralık: 6–90 sn.">
            <input
              id="brief-duration"
              type="number"
              min={6}
              max={90}
              value={brief.duration_seconds}
              onChange={(e) => updateField("duration_seconds", Number(e.target.value))}
              className={inputClass(false)}
            />
          </Field>

          <Field id="brief-placement" label="Yerleşim">
            <select
              id="brief-placement"
              value={brief.placement_id}
              onChange={(e) => updateField("placement_id", e.target.value)}
              className={inputClass(false)}
            >
              {PLACEMENT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </Field>

          <Field
            id="brief-budget"
            label="Önerilen bütçe (USD)"
            hint="Bu bir öneridir, harcama yetkisi vermez."
          >
            <input
              id="brief-budget"
              type="number"
              min={0}
              step={0.5}
              value={brief.budget_usd}
              onChange={(e) => updateField("budget_usd", Number(e.target.value))}
              className={inputClass(false)}
            />
          </Field>
        </div>
      </section>

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={saveBrief.isPending}
          className="rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Kaydet
        </button>
        {saveStatusText ? (
          <p
            role="status"
            className={
              saveBrief.isError
                ? "text-sm text-error"
                : saveBrief.isSuccess
                  ? "text-sm text-success"
                  : "text-sm text-slate-400"
            }
          >
            {saveStatusText}
          </p>
        ) : null}
      </div>
    </form>
  );
}

interface FieldProps {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  children: ReactNode;
}

function Field({ id, label, error, hint, children }: FieldProps) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm text-slate-300">
        {label}
      </label>
      {children}
      {hint && !error ? <p className="text-xs text-slate-500">{hint}</p> : null}
      {error ? (
        <p id={`${id}-error`} className="text-xs text-error">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function inputClass(invalid: boolean): string {
  return [
    "w-full rounded-md border bg-bg px-3 py-2 text-sm text-slate-100 outline-none transition",
    invalid ? "border-error focus:border-error" : "border-slate-600 focus:border-accent",
  ].join(" ");
}
