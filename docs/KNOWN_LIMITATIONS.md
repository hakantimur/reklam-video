# Bilinen Sınırlamalar (KNOWN_LIMITATIONS.md)

Bu dosya, gerçek sağlayıcı/oyun/OS sınırlamalarını ve canlı doğrulaması
yapılamamış alanları listeler (spec §24.1). "Tüm testler geçti" iddiası bu
liste boşalana kadar kullanılmaz.

## Canlı doğrulama engelleri (2026-09-11 itibarıyla)

1. ~~OpenRouter API anahtarı yok~~ — **çözüldü (2026-09-11)**: kullanıcı
   gerçek anahtarını Ayarlar ekranından girdi, Windows Credential Manager'a
   kaydedildi. Yönetmen (concept üretimi) bu anahtarla CANLI doğrulandı.
   Operatör (oyun kontrol stratejisi), reviewer ve video üretimi henüz
   uygulanmadı (Safha 5/8) — anahtar var ama bu akışlar için kod yok.
2. ~~ElevenLabs API anahtarı yok~~ — **çözüldü (2026-09-11)**: kullanıcı
   gerçek anahtarını girdi, `list_voices()` ile canlı doğrulandı (21 ses
   bulundu). TTS üretimi (synthesize) henüz bir akışa bağlanmadı.
3. ~~ffmpeg / scrcpy ikilik dosyaları makinede kurulu değildi~~ — **çözüldü
   (2026-09-11)**: `scripts/setup/fetch_binaries.py` ile ffmpeg 9.0.1 ve
   scrcpy v4.1 resmi kaynaklardan sürüm+checksum doğrulamasıyla indirildi,
   çalıştırılabilir olduğu teyit edildi (`backend/.tools/{ffmpeg,scrcpy}/`,
   `app/core/tool_paths.py` bunları PATH'te yoksa otomatik buluyor).
4. **Node sürümü LTS değil** (bkz. DECISIONS.md). Remotion 4.0.523 bu Node
   v25.9.0 ile GERÇEKTEN render alarak doğrulandı (`npx remotion versions`
   ve `npx remotion render` başarılı) — ama Node 25 Remotion'ın resmi
   desteklenen LTS listesinde değil. Resmi bir LTS'e geçilirse bu render
   tekrar doğrulanmalı.
5. **Remotion "MIT/Apache" değil, kendi özel lisansına tabi** (bkz.
   `THIRD_PARTY_NOTICES.md`). Ücretsiz katman bireyler ve ≤3 çalışanlı kâr
   amaçlı şirketleri kapsıyor; kullanıcının/organizasyonun gerçek durumu bu
   ajan tarafından değerlendirilmedi — büyük bir organizasyon için
   kullanılacaksa Company License gerekip gerekmediği ayrıca teyit
   edilmelidir.
6. **`apps/render` bu turda gerçek video/ses asset boru hattına bağlı değil.**
   `AdComposition`, video ve audio track item'larını açıkça "PLACEHOLDER"
   etiketli renkli dikdörtgenler / ekran üstü metin uyarıları olarak render
   eder; hiçbir gerçek gameplay veya AI-üretilmiş klip henüz yoktur. Bu,
   final bir reklam render'ı DEĞİLDİR — yalnızca Remotion iskeletinin timeline
   sözleşmesini doğru uyguladığının kanıtıdır.

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
