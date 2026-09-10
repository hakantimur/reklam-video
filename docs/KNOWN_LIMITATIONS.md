# Bilinen Sınırlamalar (KNOWN_LIMITATIONS.md)

Bu dosya, gerçek sağlayıcı/oyun/OS sınırlamalarını ve canlı doğrulaması
yapılamamış alanları listeler (spec §24.1). "Tüm testler geçti" iddiası bu
liste boşalana kadar kullanılmaz.

## Canlı doğrulama engelleri (2026-09-11 itibarıyla)

1. **OpenRouter API anahtarı yok.** Yönetmen (director), operatör (oyun
   kontrolü stratejisi), reviewer ve video/TTS üretimi bu anahtara bağlıdır.
   Anahtar girilene kadar bu akışlar yalnızca mock/contract testleriyle
   doğrulanabilir; gerçek model çıktısı doğrulanmamıştır.
2. **ElevenLabs API anahtarı yok (opsiyonel ikinci ses yolu).**
3. **ffmpeg / scrcpy ikilik dosyaları makinede kurulu değildi**, otomatik
   kurulum betikleriyle temin edilmesi gerekiyor; kurulum sırasında ağ erişimi
   gerekir.
4. **Node sürümü LTS değil** (bkz. DECISIONS.md) — Remotion/derleme
   uyumluluğu bu sürümle doğrulanacak, sorun çıkarsa ayrıca raporlanacak.

## Frontend (apps/web) — Safha 1 UI iskeleti (2026-09-11, agent/frontend-web)

1. **Backend'in çoğu uç noktası henüz yok.** `backend/app/main.py` şu an
   yalnızca `GET /health` ve `GET /diagnostics` sunuyor. `apps/web/src/api/client.ts`
   spec §8.1'deki tam sözleşmeye göre TİPLENDİ, ancak `/projects`,
   `/settings/credentials/{provider}`, `/providers/models`,
   `/projects/{id}/brief`, `/projects/{id}/open-folder` çağrıları backend
   tamamlanana kadar gerçek "bağlantı yok / uç nokta yok" hatası döner.
   Projeler, Ayarlar ve Brief ekranları bu durumu görünür şekilde gösterir;
   sahte veri/başarı üretilmez.
2. **Brief/brand_profile alan sözleşmesi kesinleşmedi.** `BriefPayload` tipi
   spec §7.2 (`briefs`, `brand_profiles` tabloları) ve §4.2'den türetildi;
   backend gerçek `PUT /projects/{id}/brief` şemasını uyguladığında alan
   adları/gruplaması doğrulanıp gerekirse güncellenmeli.
3. **Malzemeler ve İşler ekranları bilinçli olarak iskelet düzeyinde.**
   Karşılık gelen backend uç noktaları (`GET /projects/{id}/assets`, iş
   listesi) yok; bu ekranlar sahte satır göstermek yerine planlanan
   sütunları ve açık "henüz uygulanmadı" durumunu gösteriyor.
4. **npm audit: 4 orta/yüksek risk uyarısı** (`react-router-dom` açık
   yönlendirme, `esbuild` dev-server isteği sızıntısı). İkisi de yalnızca
   majör sürüm atlamasıyla (`react-router-dom` 6→7, `vite` 5→8) düzeltiliyor;
   bu safhada kapsam dışı bırakıldı, bkz. DECISIONS.md.

## Donanım / oyun durumu (olumlu not)

- Hedef oyun `Synova` gerçek `.aab` dosyası ve iki AVD (`synova_shot`,
  `synova_test`) mevcut. Bu, emülatör köprüsü ve kontrol döngüsü testlerinin
  (Safha 4) API anahtarı gerekmeden canlı yapılabileceği anlamına gelir.

Bu bölüm ilerledikçe güncellenecektir.
