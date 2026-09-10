# Test Raporu (TEST_REPORT.md)

**Ortam:** Windows 11 Pro (build 10.0.26100), Node v25.9.0 (LTS değil, bkz.
DECISIONS.md), Python 3.13.14, gerçek Android emülatörü (AVD `synova_test`,
`sdk_gphone64_x86_64`, gerçek Synova paketi `com.example.synova.dev`
kurulu), ffmpeg 9.0.1 + scrcpy v4.1 (resmi kaynaklardan indirildi).

**Tarih:** 2026-09-11 (gece boyu koordinatör oturumu).

## Otomatik testler

```
backend: pytest -q          → 116 passed, 11 deselected (device_live+provider_live)
backend: pytest -m device_live   → 10 passed (gerçek AVD gerektirir)
backend: pytest -m provider_live → 0 passed, 1 skipped (OPENROUTER_API_KEY yok)
apps/web: npm run build     → başarılı, TypeScript strict hatasız
apps/render: npx remotion render → başarılı, gerçek MP4 üretildi
```

Mock/contract testler ile canlı (device_live/provider_live) testler ayrı
pytest marker'larıyla ayrıştırılmıştır; "tüm testler geçti" ifadesi hiçbir
zaman ikisini birbirine karıştırmaz.

## Gerçek cihaz kanıtı (Safha 4)

- `synova_test` AVD gerçekten başlatıldı, gerçek Synova paketi başlatıldı
  (ekran görüntüsüyle doğrulandı).
- Normalize [0,1] koordinatla gerçek tap; eski (stale) gözlemle yapılan
  eylem reddedildi.
- 17.76 saniyelik gerçek scrcpy kaydı, kayıt sırasında 3 programatik tap;
  ffprobe ile h264+opus, temiz kapanış doğrulandı.
- Emulator snapshot save/list/load/delete roundtrip'i gerçek AVD'de çalıştı.
- `/devices/{serial}/preflight`: screenshot_ok, touch_ok, recording_ok,
  audio_detected hepsi gerçek donanımla `true`.

## Gerçek sağlayıcı kanıtı (Safha 3)

- `GET /api/v1/providers/models` canlı OpenRouter kataloğunu gerçekten
  çekti: 466 model (tarayıcı üzerinden de doğrulandı, bkz. aşağıda).
- Video/TTS/structured-chat gibi anahtar gerektiren yollar mock/contract
  testleriyle doğrulandı; gerçek ücretli çağrı yapılmadı (anahtar yok).

## Uçtan uca tarayıcı testi (koordinatör tarafından, bu oturumda)

Gerçek backend (`uvicorn`) + gerçek derlenmiş `apps/web` build'i FastAPI
üzerinden tek origin'den sunularak, gerçek bir tarayıcıda uçtan uca
denendi:

1. Projeler ekranı boşken "Örnek proje oluştur" ile gerçek bir proje
   oluşturuldu (gerçek `POST /projects`, gerçek proje klasörü yolu).
2. Stüdyo → Brief formu dolduruldu (ürün adı, açıklama, CTA) ve
   kaydedildi — gerçek `PUT /projects/{id}/brief` çağrısı, "Kaydedildi"
   durumu gerçekten göründü.
3. "Klasörde göster" gerçek `POST /projects/{id}/open-folder` çağırdı.
4. Ayarlar ekranında çalışma zamanı tanılaması gerçek node/adb/scrcpy/
   ffmpeg/ffprobe durumunu gösterdi (`all_required_present: true`).
5. "Modelleri yenile" gerçek OpenRouter kataloğunu (466 model) tarayıcıda
   listeledi.

Bu akış sırasında bulunup **aynı oturumda düzeltilen** entegrasyon
hataları (dört agent'ın bağımsız ürettiği kodlar arasında):

| # | Hata | Kök neden | Düzeltme |
|---|---|---|---|
| 1 | Projeler listesi hep boş görünüyordu (ne kart ne boş-durum) | Backend `GET /projects` `{items:[...]}` sarmalı döndürüyor, frontend çıplak dizi bekliyordu | `apps/web/src/api/client.ts`: `.items` unwrap edildi |
| 2 | Brief kaydetme HTTP 422 ile başarısız oluyordu | Frontend `duration_seconds`/`budget_usd` gönderiyordu, backend `target_frames`/`budget_microusd` bekliyordu; `audience`/`single_message` boşken backend reddediyordu | `client.ts`'te birim dönüşümü eklendi; backend'de bu iki alan spec §3.2 uyarınca varsayılana düşecek şekilde gevşetildi |
| 3 | Marka bilgisi (ürün adı/açıklama/CTA) hiçbir yere kaydedilmiyordu | Backend'in `BriefPut` şeması bu alanları hiç kabul etmiyordu; `brand_profiles` tablosu dolduruluyor değildi | `BriefPut` şemasına eklendi, `put_brief` artık aynı işlemde `brand_profiles` satırını upsert ediyor (revizyonlanmıyor, tek satır) |
| 4 | `POST /projects/{id}/open-folder` yoktu | Bu round'da hiç implement edilmemişti | Koordinatör tarafından eklendi (`os.startfile`, spec §8.1) |
| 5 | Türkçe proje adları slug'da harf kaybediyordu (`Örnek` → `rnek`) | `_slugify` Türkçe harfleri silip atıyordu, çeviri yapmıyordu | ç/ğ/ı/ö/ş/ü → c/g/i/o/s/u çeviri tablosu eklendi |

Her düzeltme için gerçek pytest testi eklendi (bkz. `backend/tests/unit/`)
ve tam paket (`116 passed`) tekrar doğrulandı.

## Bilinen, bu gece düzeltilmeyen entegrasyon eksikleri

- Brief formu, projeye daha önce kaydedilmiş brief'i geri yükleyip forma
  doldurmuyor (her zaman varsayılanlardan başlıyor). Veri kaybı yok (DB'de
  revizyon olarak duruyor), sadece UX eksikliği.
- `BriefResponse` TS tipi backend'in gerçek `BriefOut` şemasından biraz
  farklı (marka alanlarını içeriyor gibi görünüyor); UI şu an yanıt gövdesini
  okumadığı için çalışma zamanında sorun yaratmıyor, ama tip doğruluğu için
  ayrıca düzeltilmeli.
- Malzemeler/İşler ekranları backend'de karşılık gelen endpoint olmadığı
  için iskelet düzeyinde (bilinçli, açıkça işaretli).

## Canlı doğrulama engelleri (değişmedi)

OpenRouter/ElevenLabs API anahtarı hâlâ girilmedi — LLM yönetmen/operatör/
reviewer, gerçek video/TTS üretimi canlı doğrulanamadı. Kullanıcı anahtarı
Ayarlar ekranından girdiğinde bu akışlar test edilebilir.
