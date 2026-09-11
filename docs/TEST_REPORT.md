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

## Safha 5 canlı keşif kanıtı (2026-09-11, gerçek Synova + gerçek OpenRouter anahtarı)

`POST /projects/{id}/discover` → arka plan worker'da `discover` job'u çalıştı
(`emulator-5554`, paket `com.example.synova.dev`, model
`anthropic/claude-haiku-4.5`, `max_actions=6`).

**Deneme 1 — güvenlik davranışı doğrulandı:** Emülatör önceki çökme/yeniden
başlatma döngüsünden dolayı gerçek bir Android "System UI isn't responding"
(ANR) diyaloğu gösteriyordu. Operatör gerçek ekran görüntüsünü görüp bunu
doğru sınıflandırdı ve `request_takeover` eylemini seçti; iş
`DiscoveryTakeoverRequested` ile `failed` oldu, GameProfile YAZILMADI. Bu,
spec §11.8'in ("beklenmeyen ekranda duraklat, gizli otomatik onay yok") tam
istediği davranış — sahte başarı yerine dürüst engel raporlandı.

**Deneme 2 — gerçek keşif başarılı:** ANR diyaloğu elle kapatıldıktan sonra
aynı iş tekrar tetiklendi. Sonuç (`job.result_json`):

```
mechanic_summary: "Synova is a pattern memory game where players observe a
sequence of cells lighting up in a 4x4 grid, then reproduce that exact
sequence by tapping the cells in the correct order. The game progresses
through multiple rounds with increasing difficulty, tracking performance
as a baseline calibration for brain training."
confidence: 0.72
```

`game_profiles` ve `device_profiles` tablolarına gerçekten yazıldı
(doğrudan DB sorgusuyla doğrulandı). "4x4 grid" detayı brief/concept
metninde hiç geçmiyor — bu, modelin gerçekten ekranı gözlemleyerek
öğrendiğinin kanıtı, brief'i tekrarlaması değil. Toplam süre ~43 saniye,
6 eylem + 1 sentez çağrısı ile.

## Safha 7 canlı çekim kanıtı (2026-09-11, gerçek Synova + gerçek OpenRouter anahtarı)

`POST /projects/{id}/shots/{shot_id}/capture` → arka plan worker'da `capture_shot`
job'u çalıştı, Safha 6'da gerçek LLM ile üretilmiş ShotPlan'ın "gameplay"
tipli ikinci sahnesi (`a75662a1-...`, amaç: "Showcase first colorful brain
training game in action") için, aynı görsel-operatör döngüsünü (Safha 5)
şimdi gerçek bir kayıt altında çalıştırarak.

Gerçek `scrcpy` süreci (PID doğrudan `Get-Process` ile görüldü) kayda başladı,
operatör 5 gerçek ekran görüntüsü + LLM kararı sonunda oyunun gerçekten
oynandığını gözlemleyip `finish_discovery` ile sahneyi bitirdi, kayıt
durduruldu. Sonuç:

```
Asset: captures/raw/shot-a75662a1-...-take1.mp4, 209003 bytes
ffprobe (bagimsiz dogrulama, koordinator tarafindan ayrica calistirildi):
  codec: h264 1080x2400 + opus audio, duration=34.705521s
Teknik QC: probe=pass, decode=pass, scene_detect=pass, blank_or_frozen=pass
Take: status=pending, attempt=1
```

Ayrıca doğrulanan davranışlar:
- **Retake sayacı:** aynı shot için ikinci çağrı `attempt=2` üretiyor (mock
  testle doğrulandı, `test_capture_second_attempt_increments`).
- **Kontrol devri sırasında kayıp yok:** operatör `request_takeover` derse,
  o ana kadarki kısmi kayıt silinmiyor — gerçek bir Asset+Take olarak
  `status="rejected"`, `rejection_reason` dolu şekilde saklanıyor (kanıt
  hiçbir zaman sessizce atılmıyor).
- **Kapsam sınırı:** yalnızca `source_type="gameplay"` sahneler bu yoldan
  çekiliyor; `ai_generated` sahneler için deneme, `ValidationAppError` ile
  açıkça reddediliyor (video üretim sağlayıcısı entegrasyonu Safha 8'de).

`pytest -q`: 149 passed, 11 deselected (6 yeni servis testi +
`test_capture_service.py`, 2 yeni API testi `test_capture_api.py`).

**Takes listesi/seçimi + Stüdyo "Çekim" ekranı, gerçek tarayıcıda uçtan uca
CANLI doğrulandı** (aynı gün, ikinci tur):

1. `GET/POST /projects/{id}/shots/{shot_id}/takes[/…/select]` eklendi
   (`app/services/takes.py`, 4 yeni test — `test_takes_api.py`) → 153 passed.
2. `apps/web`'e gerçek bir "Çekim" adımı eklendi (cihaz seçici, sahne başına
   çek/yeniden çek, take listesi + `<video>` önizleme, seçim düğmesi).
3. Gerçek backend + gerçek derlenmiş build üzerinden tarayıcıda: cihaz
   seçildi, "Çek" tıklandı → gerçek bir `capture_shot` job'u kuyruğa girdi,
   `Get-Process scrcpy` ile gerçek kayıt süreci doğrulandı, iş bitince UI
   otomatik "Deneme 1 — İncelemede" + video önizlemesini gösterdi (ikinci
   gameplay sahnesi için de canlı çekildi). "Bu çekimi seç" tıklandı →
   doğrudan SQLite sorgusuyla `shots.selected_take_id`'nin gerçekten
   güncellendiği doğrulandı.

## Safha 8 canlı üretim kanıtı (2026-09-11, gerçek OpenRouter + gerçek ElevenLabs anahtarı)

Yeni `generate_ai_scene` ve `generate_voice` job'ları, Safha 6'nın ürettiği
gerçek ShotPlan'ın ilk `ai_generated` sahnesi (`dd4d9c89-...`, "Hook and
establish product with colorful game variety theme") için tetiklendi.

**Video (`POST /projects/{id}/shots/{shot_id}/generate-scene`):** önce
yönetmen (director) ajanı, Synova marka bilgisinden gerçek bir LLM
çağrısıyla İngilizce bir video-üretim prompt'u yazdı (`Shot.generation_prompt`
alanına kaydedildi), ardından bu prompt gerçek `google/veo-3.1-lite`
modeline gönderildi. Gerçek submit→poll→download döngüsü ~51 saniyede
tamamlandı:

```
Asset: generated/video/shot-dd4d9c89-...-take1.mp4, 1,447,495 bytes
ffprobe (bagimsiz dogrulama): h264 720x1280 + aac audio, duration=4.010000s
Teknik QC: probe=pass, decode=pass, scene_detect=pass, blank_or_frozen=pass
Take: status=pending, attempt=1
```

**Ses (`POST /projects/{id}/shots/{shot_id}/generate-voice`):** aynı
sahnenin gerçek Türkçe seslendirme metni ("Synova ile sekiz farklı oyunla
her gün yeni bir beyin harikası keşfedin.") gerçek ElevenLabs sesiyle
("Sarah", `eleven_multilingual_v2`, `language_code=tr`) seslendirildi:

```
Asset: audio/voice/shot-dd4d9c89-...-voice-....mp3, 72,351 bytes
ffprobe (bagimsiz dogrulama): mp3, duration=4.458231s
```

Ses varlığı bir Take'e değil doğrudan Asset'e bağlanır
(`metadata_json.shot_id`) — bir sahne aynı anda hem gameplay/AI görüntüsü
hem de ayrı bir seslendirmeye sahip olabilir (spec'te ayrı bir
`shots.voice_asset_id` kolonu yok).

`pytest -q`: 162 passed, 11 deselected (13 yeni test:
`test_generation_service.py` + `test_generation_api.py`).

## Safha 9 canlı render kanıtı (2026-09-11, gerçek karma render)

`POST /projects/{id}/timeline/build`, gerçek Synova projesinin gerçek
6 sahnelik ShotPlan'ından gerçek bir Timeline ürettti — 3 sahnede o ana
kadar çekilmiş/üretilmiş gerçek Take/Asset'ler referanslandı, kalan 3
sahne dürüstçe `asset_id: null` bırakıldı (uydurma yok). Toplam
`duration_frames: 600` brief'in `target_frames`'iyle birebir eşleşti.

`POST /projects/{id}/render/preview` bu timeline'ı gerçekten render etti:

```
Asset: renders/preview/preview-....mp4, 4,929,840 bytes
ffprobe (bagimsiz dogrulama): h264 1080x1920 + aac audio, duration=20.053333s
Teknik QC: probe=pass, decode=pass, scene_detect=pass, blank_or_frozen=pass
```

Koordinatör tarafından bağımsız olarak üç kare çıkarılıp görsel olarak
incelendi:

- **t=2sn:** gerçek Google Veo AI sahnesi (renkli bulmaca/hafıza oyunları
  gösteren bir telefon tutan el) gerçekten oynuyor.
- **t=6sn:** gerçek Synova oynanış kaydı ("Repeat the pattern", "Round 1
  of 5", 4x4 grid) doğru zamanlamada kesiliyor.
- **t=11sn:** henüz çekilmemiş üçüncü oynanış sahnesi için sistem dürüstçe
  kırmızı "PLACEHOLDER" kartı gösteriyor — sahte/eksik veri asla gerçek
  içerik gibi sunulmuyor.

`pytest -q`: 172 passed, 11 deselected (10 yeni test:
`test_timeline_service.py`, `test_render_service.py`, `test_render_api.py`).

## Safha 10 canlı varyasyon kanıtı (2026-09-11, gerçek OpenRouter anahtarı)

`POST /projects/{id}/revisions/{revision_id}/variation`, gerçek Synova
projesinin revizyon 1'i üzerinden, yalnızca CTA sahnesine gerçek bir
talimatla ("CTA'yı daha aciliyetli yap, sınırlı süreli ücretsiz deneme
vurgusu ekle") çağrıldı:

- Yeni revizyon (`sequence_no: 2`, `parent_id`: revizyon 1) gerçekten
  oluşturuldu.
- CTA sahnesi gerçekten yeniden yazıldı: `caption_text` → "Ücretsiz
  Deneyin - Sınırlı Süre", `voice_text` talimatı yansıtan yeni bir Türkçe
  cümleye dönüştü, `target_frames` talep edilmediği için 75 olarak
  **değişmedi** (spec'in kilitli/sabit alan kuralı doğrulandı).
- Diğer 5 sahne birebir taşındı; gerçek bir gameplay Take'i (`asset_id
  f421aa8e-...`), yeni revizyondaki yeni Shot id altında **aynı
  asset_id**'yi referanslayan **yeni bir Take satırı** olarak yeniden
  bağlandı — doğrudan SQL sorgusuyla doğrulandı (Take.shot_id hard FK
  olduğu için, fiziksel video dosyası değişmeden yeniden ilişkilendirildi).
- Ayrı bir mock testte, görsel kilitli bir sahneye talimat verildiğinde
  isteğin sessizce yok sayılmadığı, açık bir 422 ile reddedildiği
  doğrulandı.

`pytest -q`: 178 passed, 11 deselected (6 yeni test:
`test_revisions_service.py` + `test_revisions_api.py`).

## Safha 11 canlı QA + export kanıtı (2026-09-11)

**Gerçek Synova revizyonuna karşı (`GET .../qa`):** dürüstçe
`"passed": false` döndü, 3 sahne için ayrı ayrı "hiç kabul edilebilir
çekim/üretim yok" uyarısı verdi — hiçbir sahte "hazır" iddiası yok.

**Ayrı, minimal gerçek bir projede (tek `ai_generated` sahne, gerçek
`google/veo-3.1-lite` çağrısıyla üretildi):**

```
GET  .../qa      -> {"passed": true, "issues": []}
POST .../export  -> is basarili, sonuc:
  Asset: exports/v001/export-09e6f3cd.mp4, type=export, origin=derived
  ffprobe (bagimsiz dogrulama): h264 1080x1920 + aac, duration=4.053333s
  Teknik QC: probe=pass, decode=pass, scene_detect=pass, blank_or_frozen=pass
  metadata_json.qa_report: {"passed": true, "issues": []}
```

Mock testlerle ayrıca doğrulanan QA reddi durumları: sahnesiz/take'siz
revizyon, başarısız teknik QC, `synthetic_test` kökenli asset, brief
kare toplamıyla uyuşmayan plan — hepsi export'a hiç ulaşmadan reddediliyor.

`pytest -q`: 188 passed, 11 deselected (10 yeni test:
`test_qa_service.py`, `test_export_service.py`, `test_qa_export_api.py`).

## Canlı doğrulama engelleri (değişmedi)

OpenRouter/ElevenLabs API anahtarı hâlâ girilmedi — LLM yönetmen/operatör/
reviewer, gerçek video/TTS üretimi canlı doğrulanamadı. Kullanıcı anahtarı
Ayarlar ekranından girdiğinde bu akışlar test edilebilir.
