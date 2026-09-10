import { EmptyState } from "../components/common/EmptyState";

// Spec §5.2 "Malzemeler" ekranının hedef sözleşmesi (tür, etiket, arama,
// yeniden kullanım — FR-10) bu safhanın kapsamında değil (bkz.
// docs/PROGRESS.md, Safha 7). Backend'de karşılık gelen uç nokta
// (GET /projects/{id}/assets) henüz yok; bu yüzden burada sahte kart veya
// sayaç göstermek yerine planlanan sütunları ve gerçek durumu bildiriyoruz.
const PLANNED_COLUMNS = ["Önizleme", "Tür", "Etiketler", "Süre", "Kaynak", "Kullanım"];

export function MaterialsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Malzemeler</h1>
        <p className="text-sm text-slate-400">
          Projeye yüklenen ve üretilen görsel/ses malzemelerin arşivi.
        </p>
      </div>

      <EmptyState
        title="Bu ekran henüz uygulanmadı"
        description="Malzeme arşivi (yükleme, etiketleme, arama, yeniden kullanım) sonraki bir geliştirme safhasında eklenecek — bkz. docs/PROGRESS.md, Safha 7. Şu an backend tarafında bu veriyi döndüren bir uç nokta yok."
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
