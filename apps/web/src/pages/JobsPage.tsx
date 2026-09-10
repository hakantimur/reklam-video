import { EmptyState } from "../components/common/EmptyState";

// Spec §5.2 "İşler" ekranı (tür, durum, geçen süre, sağlayıcı kimliği,
// maliyet, kurtar — FR-20) bu safhanın kapsamında değil. Backend'de
// GET /jobs/{id} dışında bir liste uç noktası tanımlı değil ve worker
// süreci henüz çalışmıyor (bkz. docs/PROGRESS.md, Safha 2). Sahte iş
// kaydı göstermek yerine planlanan sütunlar ve gerçek boş durum sunulur.
const PLANNED_COLUMNS = ["Tür", "Durum", "Geçen süre", "Sağlayıcı kimliği", "Maliyet", "Kurtar"];

export function JobsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">İşler</h1>
        <p className="text-sm text-slate-400">
          Kalıcı arka plan işleri ve bütçe takibi.
        </p>
      </div>

      <EmptyState
        title="Bu ekran henüz uygulanmadı"
        description="İş kuyruğu, kalıcı durum ve kurtarma akışı sonraki bir geliştirme safhasında eklenecek — bkz. docs/PROGRESS.md, Safha 2. Şu an worker süreci ve iş listesi uç noktası yok."
      />

      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-800 bg-surface/40 text-xs uppercase tracking-wide text-slate-500">
              {PLANNED_COLUMNS.map((col) => (
                <th key={col} scope="col" className="px-4 py-2 font-medium">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={PLANNED_COLUMNS.length} className="px-4 py-6 text-center text-slate-500">
                Henüz veri yok.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
