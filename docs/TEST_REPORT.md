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

## Safha 12 — final regresyon (2026-09-11, oturum sonu)

Tüm gece boyunca eklenen Safha 5-11 kodunun tek bir tutarlı `main` HEAD
üzerinde birlikte çalıştığını doğrulamak için tam bir regresyon yapıldı:

```
backend: pytest -q              -> 188 passed, 11 deselected
apps/web: npm run build         -> basarili, TypeScript strict hatasiz
apps/render: npm run build      -> basarili (tsc --noEmit), hatasiz
Soguk backend yeniden baslatma + GET /health + GET / (SPA)  -> ikisi de basarili
```

Bu geçişte fark edilip düzeltilen gerçek hata: `GET /health`'in
`worker.status` alanı, arka plan job worker'ı gerçekten çalışırken bile
her zaman sabit `"not_started"` döndürüyordu (`app/jobs/worker.py`'a
gerçek durumu döndüren `is_running()` eklendi, `app/api/health.py` buna
bağlandı). Bu gece boyunca worker'ın onlarca gerçek job'u (discover,
capture_shot, generate_ai_scene, generate_voice, render_preview,
export_final) başarıyla işlediği zaten doğrudan job durumu sorgularıyla
kanıtlanmıştı — yalnızca health endpoint'i bunu yanlış raporluyordu.

`SETUP.bat`/`START.bat`/`STOP.bat` bu oturumda defalarca gerçekten
çalıştırıldı (her kod değişikliğinden sonra backend'i yeniden başlatmak
için) — kaynak koddan gerçek bir Windows kurulumunun çalıştığı tekrar
tekrar kanıtlandı. Bağımsız/önkoşulsuz bir installer paketi bu oturumda
üretilmedi (bkz. KNOWN_LIMITATIONS.md).

## Safha 8-11 UI + gerçek bir revizyon hatası (2026-09-11, üçüncü tur)

Stüdyo'ya "Taslak" (AI sahne/seslendirme üretimi + timeline + önizleme
render) ve "Çıktı" (QA + dışa aktarma) ekranları eklendi. Gerçek Synova
projesinde tarayıcıda uçtan uca denendi:

- Var olan bir AI sahnesinin videosu ve var olan bir seslendirmenin sesi
  doğru şekilde `<video>`/`<audio>` oynatıcılarında göründü (gerçek asset
  içeriğine bağlı).
- "Sahneyi üret" tıklaması gerçek bir `generate_ai_scene` job'unu
  tetikledi, ~60 saniyede tamamlandı, buton otomatik "Yeniden üret"e
  döndü.
- "Timeline oluştur" → "Önizleme render et" gerçek bir 8.3MB/20sn önizleme
  MP4'ü üretip oynatıcıda gösterdi.
- "Çıktı" ekranı gerçek eksik sahneleri listeleyip "Dışa aktar"ı doğru
  şekilde devre dışı bıraktı.

**Bu canlı test, Safha 10'da gerçek bir hata buldu:** daha önce oluşturulan
bir varyasyon revizyonu "en son revizyon" haline geldiğinde, hiç açıkça
"seçilmemiş" ama var olan bir AI sahnesi take'i (bir "seç" düğmesi hiç
tıklanmadığı için) yeni revizyona taşınmıyordu — kod yalnızca
`shots.selected_take_id` açıkça set edilmişse taşıyordu. Düzeltme:
`app/services/revisions.py` artık `app/services/timeline.py`'nin
render'da kullandığı aynı `selected_or_best_take` fallback'ini kullanıyor.
Bunu keşfeden test verisi (kendi Safha 10 doğrulamamdan kalan bir
varyasyon revizyonu) temizlendi, gerçek revizyon 1 (tüm gerçek take'leriyle)
tekrar "en son revizyon" oldu.

`pytest -q`: 189 passed, 11 deselected (1 yeni regresyon testi).

## Gerçek altyazı render'ı (2026-09-11, üçüncü tur devamı)

`app/services/timeline.py`'nin altyazı öğeleri artık `transform.captionText`
içinde gerçek `Shot.caption_text`'i taşıyor; `AdComposition.tsx`'teki
`SubtitleItemRenderer` bunu (yoksa eski pozisyon placeholder'ına dönerek)
gerçekten ekrana basıyor. Gerçek Synova projesi yeniden render edildi,
sonuçtan bağımsız bir kare çıkarıldı: gerçek AI sahnesinin üzerinde
gerçek Türkçe altyazı ("Sekiz farklı oyunla her gün yeni bir beyin
harikası keşfedin.") doğru konumda ve okunaklı şekilde görünüyor.

`pytest -q`: 189 passed, 11 deselected (mevcut bir test güncellendi).

## Malzemeler + İşler ekranları gerçek veriye bağlandı (2026-09-11)

`GET /projects/{id}/jobs` eklendi (3 yeni test — `test_jobs_list_api.py`,
192 passed). `MaterialsPage`/`JobsPage` artık aktif projenin gerçek
verisini gösteriyor, sahte iskelet değil. Gerçek Synova projesinde
tarayıcıda CANLI denendi:

- **Malzemeler:** tüm gecenin gerçek çıktıları tek listede — 2 gerçek
  Synova oynanış kaydı, 2 gerçek Google Veo AI sahnesi, 1 gerçek
  ElevenLabs seslendirmesi, 3 gerçek önizleme/export render'ı — hepsi
  gerçek `<video>`/`<audio>` oynatıcılarıyla.
- **İşler:** tüm gecenin gerçek job geçmişi — discover/capture_shot/
  generate_ai_scene/generate_voice/render_preview job'ları, gerçek
  süreleriyle (ör. "Önizleme render — 3 dk 45 sn") ve gerçek bir
  başarısızlık (`Keşif — Başarısız — handler_error`, Safha 5'in canlı
  kontrol-devri testinden kalan gerçek kanıt).

`pytest -q`: 192 passed, 11 deselected.

## Gerçek maliyet kaydı: video üretimi (2026-09-11, dördüncü tur)

`OpenRouterVideoProvider.poll()` gerçek API yanıtında zaten var olan ama
hiç okunmayan `usage.cost` alanını (sağlayıcının kendi onayladığı gerçek
harcama — tahmin değil) `VideoPollResult.cost_usd`'ye taşıyacak şekilde
düzeltildi. `generate_ai_scene` job handler'ı bunu artık gerçek bir
`BudgetEntry` (settlement, confidence=confirmed) satırına yazıyor —
bir bütçe/gate değil, saf harcama defteri; bir ayarlama hatası asla
başarılı bir job'u başarısız hale getirmiyor (`_settle_real_cost` her
zaman best-effort, testlerle doğrulandı: eksik maliyet, eksik asset,
çift settle — hiçbiri exception fırlatmıyor).

Gerçek Synova projesinde bir AI sahnesi yeniden üretilerek CANLI
doğrulandı:

```
Asset.metadata_json.provider.actual_cost_usd: 0.32
BudgetEntry: entry_type=settlement, amount_microusd=320000, confidence=confirmed
```

`pytest -q`: 196 passed, 11 deselected (4 yeni test:
`test_settle_real_cost.py`, artı `test_openrouter_video_flow.py`'ye bir
assertion eklendi).

## İçerik/marka güvenliği reviewer'ı (2026-09-11, dördüncü tur)

Spec §10'un reviewer ajanı gerçekten uygulandı: `app/agents/reviewer.py`
+ `app/services/review.py` + `POST /projects/{id}/shots/{shot_id}/review`.
Gerçek Synova projesindeki gerçek gameplay Take'ine karşı CANLI
doğrulandı:

```
sample_frames_png() gercek videodan 4 kare cikardi
review_take() -> outcome: pass
reasoning: "The sampled frames clearly demonstrate active gameplay...
  Frame 1 shows the initial state (0 of 4 selected), frames 2-4 show
  progressive player engagement with visible cell selections (1 of 4,
  then 2 of 4)..."
```

Bu, modelin gerçekten kareleri görüp somut, doğrulanabilir ayrıntılar
verdiğinin kanıtı (genel/şablon bir cevap değil). Sonuç `qa_reports`
tablosuna (`scope=content`) kalıcı yazıldı; `GET .../qa` bu revizyona
tekrar çağrıldığında, incelenen sahne için hiçbir yeni sorun eklenmedi
(pass olduğu için), eksik 2 sahne için eski hatalar aynen kaldı — içerik
incelemesinin QA'ya doğru şekilde entegre olduğu, ama zorunlu olmadığı
(hiç incelenmemiş sahneleri bloklamadığı) doğrulandı.

`pytest -q`: 204 passed, 11 deselected (8 yeni test: `test_review_service.py`,
`test_review_api.py`, artı `test_qa_service.py`'ye 2 yeni test).

## Basit ses kısma (ducking) (2026-09-11, beşinci tur)

`timeline.py` artık her video öğesine `transform.hasVoiceOver` ekliyor
(o sahnenin bir seslendirmesi varsa `true`). `AdComposition.tsx`'teki
`VideoItemRenderer` bunu okuyup `OffthreadVideo`'nun `volume` prop'unu
ayarlıyor (`0.2` seslendirme varsa, `1` yoksa) — böylece bir sahnenin
kendi gömülü sesi (gerçek oynanışın oyun sesi veya Veo'nun ürettiği
ortam sesi) ayrı bir seslendirmeyle çakışmıyor. Gerçek Synova projesi
yeniden render edilerek hatasız tamamlandığı doğrulandı (`hasVoiceOver`
alanlarının doğru sahnelerde `true` döndüğü de ayrıca kontrol edildi).

`pytest -q`: 206 passed, 11 deselected (2 yeni test).

## İçerik incelemesi için UI tetikleyicisi (2026-09-11, beşinci tur devamı)

Önceki turda eklenen reviewer ajanı yalnızca `POST .../review` ile API
üzerinden tetiklenebiliyordu (bkz. yukarıdaki "İçerik/marka güvenliği
reviewer'ı" bölümü, KNOWN_LIMITATIONS.md madde 1). Bu turda:

- `GET /projects/{id}/shots/{shot_id}/review` eklendi
  (`backend/app/api/review.py`) — sahnenin en son (varsa) içerik
  incelemesini döner, hiç incelenmemişse `null`.
- Taslak ekranındaki her AI sahne kartına (`DraftStep.tsx`
  `AiSceneCard`) "İçerik incele (AI)" düğmesi, geçti/reddedildi/belirsiz
  rozeti ve gerekçe + kusur listesi eklendi.
- `apps/web/src/api/types.ts` / `client.ts`'e `ShotReview`,
  `getShotReview`, `startShotReview` eklendi.

**Backend canlı kanıt** (gerçek Synova projesi, Hook sahnesi
`dd4d9c89-…`, gerçek OpenRouter anahtarı):
1. `GET .../review` → `200 null` (hiç incelenmemiş).
2. `POST .../review {"model":"anthropic/claude-haiku-4.5"}` → `202`,
   job `7fcc9059-ff39-4205-87f5-b1305c0b5728`.
3. Job ~13 saniyede `succeeded`: gerçek 4 kare örneklemesi + gerçek
   vision LLM çağrısı, `outcome: "pass"`, gerçek, sahneye özgü gerekçe
   metni ("Multiple distinct games are visible across the four
   frames…").
4. `GET .../review` tekrar çağrıldı → aynı gerçek `outcome`/`reasoning`/
   `reviewer_model` (`anthropic/claude-haiku-4.5`) döndü — yani job'un
   yazdığı `QAReport` satırı GET uç noktasından doğru okunuyor.

**Frontend:** `npm run build` (`tsc -b && vite build`) temiz geçti.
Backend testleri (`pytest -q` — `backend/` dizininden, çünkü
`alembic.ini`'deki `migrations` yolu göreli): **208 passed, 11
deselected** (2 yeni API testi: hiç incelenmemiş → `null`, gerçek
`QAReport` satırı varken → doğru alanlar).

**Doğrulanamayan kısım (dürüstçe belirtiliyor):** Bu oturumdaki tarayıcı
önizleme aracı (Browser pane) ayrı bir ağ sandbox'ında çalışıyor ve
host makinenin `127.0.0.1:8765` backend'ine bağlanamıyor
(`net::ERR_FAILED` — hem `/health` hem `/projects` istekleri için).
Bu yüzden yeni düğmenin gerçek bir tarayıcıda tıklanıp rozetin/
gerekçenin göründüğü görsel olarak doğrulanamadı; yalnızca kod/tip
düzeyinde (temiz derleme) ve backend'in gerçek HTTP kanıtıyla
doğrulandı.

## Gerçek LLM maliyet kaydı: chat completions (2026-09-11, beşinci tur devamı)

Önceki turda yalnızca video üretiminin (`generate_ai_scene`'in Veo
çağrısı) gerçek maliyeti izleniyordu. Bu turda önce gerçek bir OpenRouter
`/chat/completions` çağrısı doğrudan (uygulama dışından) yapılarak
yanıtın gerçekten `usage.cost` alanı taşıdığı doğrulandı:

```
POST https://openrouter.ai/api/v1/chat/completions (anthropic/claude-haiku-4.5)
-> usage: {"prompt_tokens": 10, "completion_tokens": 5, "cost": 3.5e-05, ...}
```

Sonra:

- `OpenRouterTextVisionProvider` her `generate_structured` çağrısından
  sonra `usage.cost`'u `self.total_cost_usd`'ye ekliyor (aynı provider
  örneği bir job içinde birden çok kez kullanılırsa — operatör
  döngüsü, yönetmen retry'ı — doğru toplamı verir).
- `discover`, `capture_shot`, `review_take` job handler'ları artık
  `_settle_llm_cost(session, job, cost_usd=provider.total_cost_usd)`
  çağırıyor.
- `generate_ai_scene` artık `_settle_generation_cost` kullanıyor: Asset
  metadata'sındaki gerçek video maliyetiyle `text_provider.total_cost_usd`'yi
  (sahne prompt'u üretimi) tek bir `BudgetEntry` satırında topluyor —
  `budget.settle()` job başına yalnızca bir settlement'a izin verdiği
  için.

**Canlı kanıt** (gerçek Synova projesi, montaj sahnesi `0a38e7fe-…`):
1. `POST .../review` → job `d52c405a-…`.
2. Job `succeeded`, gerçek bir vision LLM incelemesi yaptı (`outcome:
   pass`).
3. DB'den doğrudan okundu: `BudgetEntry(job_id="d52c405a-…",
   entry_type="settlement", amount_microusd=5957, confidence="confirmed")`
   — yani gerçek `$0.005957` harcama gerçek bir bütçe satırına döndü.

`generate_ai_scene`'in birleşik (video+metin) toplama yolu ayrıca canlı
denenmedi: bir video üretimi tek başına ~$0.12–0.32 gerçek harcamaya yol
açıyor ve toplama mantığının kendisi (`video_cost + text_provider.
total_cost_usd`) `test_settle_real_cost.py::
test_settle_generation_cost_sums_video_and_text_cost` ile gerçek
sayılarla birim testinde doğrulandı; aynı oturumda ayrıca tetiklenen
gerçek bir `generate_ai_scene` job'u (CTA sahnesi) beklenen bir süre
doğrulama hatasıyla (`target_frames` 2.5 sn'ye denk geliyor, Veo yalnızca
[4,6,8] sn destekliyor) başarısız oldu — bu, bu turun değişikliğinden
kaynaklanmayan, önceden de dokümante edilmiş bilinen bir davranış.

`generate_voice` (ElevenLabs) hâlâ izlenmiyor: `POST
/text-to-speech/{voice_id}` yanıtı ham `audio/mpeg` baytlarından ibaret,
ne `usage` ne `cost` alanı taşıyor; gerçek maliyet kullanıcının
ElevenLabs abonelik planına bağlı ve API'den okunamıyor — uydurma bir
fiyat tablosu yazmak yerine bilinçli olarak boş bırakıldı.

`pytest -q` (backend dizininden): **212 passed, 11 deselected** (6 yeni
test: `test_settle_real_cost.py` tamamen yeniden yazıldı —
`_settle_llm_cost`/`_settle_generation_cost` için 6 test; ayrıca
`test_openrouter_structured.py`'ye `usage.cost` birikimi için 2 test
eklendi).

## Gerçek hata: varyasyonlar seslendirmeyi sessizce kaybediyordu (2026-09-11, altıncı tur)

Safha 10'da daha önce bulunan "taşınan bir sahnenin take'i kayboluyor"
hatasının (bkz. yukarıdaki Safha 10 kanıtı) tam bir eşleniği,
seslendirme (voice-over) Asset'leri için de vardı ve o zaman
fark edilmemişti: `app/services/timeline.py::_voice_asset_for_shot`
bir seslendirmeyi yalnızca `metadata_json.shot_id == <bu sahnenin id'si>`
eşleşmesiyle buluyor; ama `create_revision_variation`'ın carry-forward
yolu (`revisions.py`), talimat verilmeyen HER sahne için (talimat
verilen için değil) her zaman yepyeni bir `Shot` satırı/id'si üretiyor.
Yani: bir sahneye seslendirme üretildikten SONRA, o sahneyi hiç
hedeflemeyen bir varyasyon oluşturulduğunda, o seslendirme sessizce
"kayıp" görünüyordu — Taslak ekranı "Seslendirme üret" gösterip
kullanıcıyı zaten ödediği bir sesi tekrar (gerçek parayla) üretmeye
yönlendirebilirdi.

**Bulma yöntemi:** Kod incelemesi sırasında, `_voice_asset_for_shot`'ın
katı `shot_id` eşleşmesi ile `create_revision_variation`'ın carry-forward
sahneleri için her zaman yeni bir Shot id'si ürettiği fark edildi —
gerçek Synova projesinde önceden üretilmiş iki gerçek ElevenLabs
seslendirmesi (Hook + CTA) olduğu bilindiğinden, bu doğrudan canlı test
edilebilir bir hipotezdi.

**Düzeltme:** `revisions.py`'e `_carry_forward_voice_asset(session,
project_id, old_shot_id, new_shot_id)` eklendi — carry-forward edilen
her sahne için (yalnızca talimat verilmeyenler, take carry-forward ile
aynı kapsam) varsa mevcut seslendirme Asset'inin `metadata_json.shot_id`
alanı yeni sahne id'sine güncelleniyor.

**Canlı kanıt** (gerçek Synova projesi, revizyon `c835445c-…`):
1. Değişiklik öncesi: seslendirme Asset'leri `dd4d9c89-…` (Hook) ve
   `aa10b56a-…` (CTA) sahnelerine bağlıydı.
2. Gerçek bir varyasyon isteği gönderildi — yalnızca montaj sahnesine
   ("Add a touch more energy to the montage description text.") gerçek
   bir yönetmen talimatı verildi; Hook ve CTA hedeflenmedi.
3. Yeni revizyon `8d44364a-…` oluştu; Hook artık `396b2872-…`, CTA artık
   `0c331bca-…` id'sinde.
4. `GET .../assets?type=audio` ile doğrudan kontrol edildi: iki
   seslendirme Asset'i de artık tam olarak bu yeni id'lere işaret
   ediyordu (`role: voice_over` dahil diğer alanlar değişmedi).
5. `POST .../timeline/build` tekrar çağrıldı: yeni Hook/CTA sahneleri
   `hasVoiceOver: true`, değişen montaj sahnesi ise beklendiği gibi
   `hasVoiceOver: false` (metni değiştiği için eski ses artık geçerli
   değil — bilinçli olarak taşınmadı).

Birim test eklendi:
`test_revisions_service.py::
test_variation_carries_forward_a_voice_over_asset_to_the_new_shot_id`.

**İlgili bir ikinci durum da aynı turda ele alındı:** bir sahne talimatla
revize edilirken (`if instruction:` yolu) sesi kilitliyse (`locks.voice`),
`voice_text` base sahneyle bit bit aynı kalıyor — yani önceden üretilmiş
seslendirme hâlâ geçerli, ama önceki kodda yalnızca metin korunuyordu,
ses Asset'i o yolda hiç taşınmıyordu. Aynı `_carry_forward_voice_asset`
şimdi bu yol için de (yalnızca `locks.voice` true iken) çağrılıyor. Bu
durum gerçek Synova projesinde CANLI denenmedi: hiçbir sahnede şu an
`voice` kilidi açık değil ve kilitleri değiştirecek bir API/ekran henüz
yok (bkz. KNOWN_LIMITATIONS.md — "kilit açma/kapama ekranı henüz yok");
bunu canlı denemek ya gerçek planı sıfırdan yeniden üretmeyi (mevcut
gerçek asset'leri riske atarak) ya da kapsam dışı yeni bir kilit-toggle
endpoint'i gerektirirdi. Bunun yerine aynı, zaten canlı kanıtlanmış
`_carry_forward_voice_asset` fonksiyonunun ikinci bir çağrı noktasından
doğru parametrelerle tetiklendiği birim testiyle doğrulandı:
`test_revisions_service.py::
test_variation_carries_forward_voice_asset_when_voice_locked_on_an_instructed_shot`.

`pytest -q`: **214 passed, 11 deselected**.

## Canlı doğrulama engelleri (güncel)

OpenRouter ve ElevenLabs API anahtarları bu oturumun başında Ayarlar
ekranından girildi ve o zamandan beri onlarca gerçek, ücretli API
çağrısı yapıldı (Veo video üretimi, ElevenLabs TTS, OpenRouter chat
completions/vision) — yukarıdaki "Canlı doğrulama engelleri (değişmedi)"
notu artık güncel değil, bilgi için burada bırakıldı. Bu oturumun tek
gerçek doğrulama engeli, yukarıda açıklanan tarayıcı-sandbox ağ
izolasyonu.

## Kilit/varyasyon UI'ı ve gerçek bir SQLite eşzamanlılık hatası (2026-09-11, yedinci tur)

Safha 10'un (revizyon/kilit/varyasyon motoru) hiçbir arayüzü yoktu — bu
oturum boyunca yalnızca doğrudan API çağrılarıyla (curl/python) test
edilmişti. Bu turda:

- `PATCH /projects/{id}/shots/{shot_id}/locks` eklendi
  (`app/services/revisions.py::set_shot_locks` — `takes.select_take`'in
  `selected_take_id`'yi yerinde güncellemesiyle aynı desen, yeni bir
  revizyon açmıyor).
- Senaryo ekranındaki (`ConceptsStep.tsx`) her sahne kartına 4 kilit
  onay kutusu (görsel/ses/yazı/süre) ve bir talimat kutusu, altına da
  "Varyasyon oluştur" düğmesi eklendi.

**Canlı kanıt** (gerçek Synova projesi):
1. `PATCH .../shots/396b2872-.../locks {"voice": true}` → `200`, kilit
   gerçekten kaydedildi (`GET .../plan` ile doğrulandı).
2. Aynı sahneye gerçek bir görsel-değişikliği talimatı verilerek
   `POST .../variation` çağrıldı — yeni revizyonda sesin (daha önce
   yalnızca birim testiyle doğrulanabilmiş olan ikinci taşıma yolu, bkz.
   yukarıdaki "Ses kilitli, talimatla revize edilen sahnelerde de
   seslendirme taşınsın" bölümü) gerçekten korunduğu doğrulandı.

**Bu canlı test sırasında üçüncü, altyapısal bir hata bulundu ve
düzeltildi:** adım 2'deki `POST .../variation` isteği ilk denemede
gerçek bir `500 Internal Server Error` döndü. Aynı istek, hiçbir kod
değişikliği yapılmadan hemen tekrar gönderildiğinde başarıyla `201`
döndü — bu, transient bir alt sistem hatasına işaret ediyordu.
`app/api/errors.py` incelenince görüldü ki `ServiceError`'ın varsayılan
`status_code`'u 500'dür — yani hata düzgün yakalanıp JSON zarfına
sarılmıştı (kod çökmedi, log'da traceback de yoktu), ama alttaki gerçek
istisna 500'e denk düşüyordu. `app/core/db.py` incelenince: SQLite'ın
kendi varsayılan `busy_timeout`'u `0` — yani bir yazıcı, yazma kilidini
(WAL modunda bile aynı anda yalnızca bir yazıcıya izin verilir) hemen
alamazsa beklemek yerine anında "database is locked" ile başarısız
oluyor. Bu uygulamada arka planda sürekli çalışan bir job worker thread'i
VE (log'lardaki sürekli `GET /jobs` isteklerinden anlaşıldığı üzere)
muhtemelen açık bir frontend sekmesi aynı SQLite dosyasına eşzamanlı
yazıyor/okuyor; `create_revision_variation` gibi çok satırlı bir yazma
işlemi bu ikisinden biriyle çakıştığında bu hataya yol açabiliyordu.

**Düzeltme:** `app/core/db.py::make_engine`'in bağlantı pragma'larına
`PRAGMA busy_timeout=5000` eklendi — bir yazıcı artık kilidi hemen
alamazsa 5 saniyeye kadar bekliyor, anında başarısız olmuyor.

**Canlı doğrulama (gerçek backend'e karşı, gerçek eşzamanlılık ile):**
1. 8 thread'den sürekli gerçek `GET /projects/{id}/jobs` isteği atılırken
   5 gerçek `PATCH .../locks` yazma isteği gönderildi — hepsi `200`,
   sıfır hata.
2. Daha güçlü bir kanıt (gerçek yazıcı-yazıcı çakışması): 6 gerçek
   sahnenin her biri için 4'er kez, toplam 24 gerçek `PATCH .../locks`
   isteği TAM OLARAK AYNI ANDA (24 ayrı thread, hepsi `.start()` sonra
   hepsi `.join()`) gönderildi — hepsi `200`, sıfır hata.

Birim test eklendi: `tests/unit/test_db_pragmas.py` — gerçek uygulama
motorunun bağlantılarında `PRAGMA busy_timeout` değerinin gerçekten 5000
olduğunu doğrudan sorgulayan bir test, iki gerçek SQLite bağlantısının
(thread'lerde) aynı satır için çakıştığında `busy_timeout=5000` ile
beklediğini (hata vermediğini) kanıtlayan bir test, ve aynı senaryonun
`busy_timeout=0` ile (düzeltmeden önceki gerçek varsayılan) gerçekten
`OperationalError` ürettiğini kanıtlayan bir "sağlık kontrolü" testi
(böylece testin kendisinin bir şey kanıtlamadığı, yanlışlıkla her zaman
geçtiği ihtimali de elenmiş oluyor).

Ayrıca `PATCH .../locks` ve `POST .../variation` için backend testleri
eklendi (`test_revisions_service.py`, `test_revisions_api.py`).

`npm run build` (`tsc -b && vite build`) temiz geçti — ama önceki
turlarda olduğu gibi, tarayıcı önizleme sandbox'ı backend'e ağdan
erişemediği için yeni kilit onay kutularının/varyasyon düğmesinin
gerçek bir tarayıcıda tıklanması görsel olarak doğrulanamadı; yalnızca
gerçek HTTP uç noktaları üzerinden (yukarıdaki gibi) doğrulandı.

`pytest -q` (backend dizininden): **222 passed, 11 deselected**.

## Revizyon geçmişi (2026-09-11, yedinci tur devamı)

`GET /projects/{id}/revisions` eklendi (`plans_service.list_revisions`,
salt-okunur, en yeni önce) ve Senaryo ekranına 2+ revizyon varsa görünen
bir "Revizyon geçmişi" listesi eklendi (sıra no, sahne sayısı, değişiklik
özeti, oluşturulma zamanı, güncel revizyon işaretli).

**Canlı kanıt:** gerçek Synova projesinde `GET .../revisions` çağrıldı —
bu oturum boyunca gerçekten oluşturulmuş 4 revizyonun tamamı, doğru
`sequence_no` sırasıyla (4,3,2,1) ve doğru `parent_id` zincirleriyle
döndü (`#1` → ilk plan, `#2`/`#3`/`#4` → gerçek varyasyonlar).

Birim testleri eklendi: `test_list_revisions_api.py` (yeni-eskiye sıra +
sahne sayısı + parent zinciri, plansız proje için boş liste, projeler
arası veri sızıntısı olmadığı).

`npm run build` temiz. `pytest -q`: **225 passed, 11 deselected**.

## Dördüncü gerçek hata: kardeş varyasyonlar seslendirmeyi birbirinden çalıyordu (2026-09-11, yedinci tur devamı)

Revizyon geçmişi ekranını canlı incelerken (bkz. yukarıdaki bölüm) fark
edildi: gerçek Synova projesinin GÜNCEL revizyonundaki Hook sahnesi
(`cf1a7d6f-…`) `hasVoiceOver: false` gösteriyordu — daha önce (bir önceki
bölümde) ses kilidiyle CANLI doğrulanmış olan taşıma mekanizmasının
kendisi bu sefer çalışmamıştı. Kök nedeni bulmak için gerçek revizyon
zincirini sorgulayınca görüldü: aynı `parent_id`'den (`8d44364a-…`) İKİ
farklı varyasyon türemişti — biri bir bug-tekrar-üretme script'i, biri
gerçek UI-benzeri API testi, ikisi de AYNI temel Hook sahnesini (voice
kilidiyle) hedefliyordu. `_carry_forward_voice_asset`'in önceki hâli
(bkz. bir önceki bölüm) mevcut ses Asset'ini YERİNDE güncelliyordu; ilk
çalışan kardeş (sequence #3) ses Asset'ini kendi yeni Hook sahnesine
taşıdı, sonra ikinci kardeş (sequence #4, gerçek proje şu an bunu
gösteriyordu) aynı eski `shot_id`'yi arayınca artık hiçbir Asset onu
göstermiyordu — sessizce hiçbir şey yapmadı.

**Düzeltme:** `_carry_forward_voice_asset` artık mevcut Asset satırını
hiç değiştirmiyor; bunun yerine aynı dosyaya işaret eden (`relative_path`/
`sha256`/`byte_size` aynı, disk'e ikinci bir kopya yazılmıyor) YENİ bir
Asset satırı oluşturup onu yeni sahneye bağlıyor — Take'lerin zaten aynı
`asset_id`'yi birden çok satırla paylaştığı desenin birebir aynısı.

**Canlı kanıt** (gerçek Synova projesi, revizyon `2458dfbc-…`'nin Hook/CTA
sahneleri — bunlar orijinal, doğru ses referanslarına sahip tek revizyondu):
1. Aynı temel revizyondan (`2458dfbc-…`) montaj sahnesine iki FARKLI
   gerçek talimat verilerek iki KARDEŞ varyasyon oluşturuldu (revizyon
   `57be8864-…` ve `4f3f7dc4-…`).
2. `GET .../assets?type=audio` ile doğrudan kontrol edildi: her iki
   kardeşin de kendi Hook VE CTA sahne id'lerine işaret eden, bağımsız
   ses Asset satırları vardı — biri diğerini çalmamıştı.
3. Bu düzeltme aynı zamanda gerçek projeyi de onardı: yeni güncel
   revizyon (`4f3f7dc4-…`) artık `POST .../timeline/build` ile yeniden
   inşa edildiğinde Hook VE CTA için `hasVoiceOver: true` gösteriyor
   (önceki turda kırılmış olan gerçek durum düzeltildi).

Birim testleri güncellendi/eklendi:
`test_variation_carries_forward_a_voice_over_asset_to_the_new_shot_id`
ve `test_variation_carries_forward_voice_asset_when_voice_locked_on_an_instructed_shot`
artık "orijinal Asset değişmedi, yeni bir klon oluştu" doğruluyor; yeni
`test_variation_does_not_steal_a_voice_over_from_a_sibling_variation` bu
tam senaryoyu (iki kardeş, aynı temel sahne) birim testinde tekrarlıyor.

`pytest -q`: **226 passed, 11 deselected**.

## Bütçe UI'ı: harcanan/kalan bütçe artık görünür (2026-09-11, sekizinci tur)

Bu oturum boyunca gerçek video (Veo) ve gerçek LLM chat completion
maliyetleri `BudgetEntry` tablosuna doğru şekilde yazılıyordu (bkz.
yukarıdaki "Gerçek LLM maliyet kaydı" bölümleri), ama `budget_service.
get_budget_summary`'yi okuyan hiçbir uç nokta yoktu — tüm bu maliyet
takibi kullanıcıya tamamen görünmezdi.

- `GET /projects/{id}/budget` eklendi (`app/api/budget.py`,
  `BudgetSummaryOut` — `user_cap_microusd`, `settled_cost_microusd`,
  `active_reservations_microusd`, `available_microusd`).
- Stüdyo ekranının başlığına, aktif proje varken her zaman görünen bir
  "Bütçe: $X / $Y" göstergesi eklendi (aktif rezervasyon varsa ayrıca
  gösteriliyor, bütçe aşılmışsa kırmızı), 15 saniyede bir kendiliğinden
  yenileniyor.

**Canlı kanıt:** gerçek Synova projesinde `GET .../budget` çağrıldı →
`{"user_cap_microusd": 5000000, "settled_cost_microusd": 325957,
"active_reservations_microusd": 0, "available_microusd": 4674043}` —
yani `$0.325957 / $5.00`, bu oturum boyunca gerçekten settle edilmiş
Veo video maliyeti (`$0.32`) ile LLM review maliyetinin (`$0.005957`)
tam doğru toplamı.

Birim testleri eklendi: `test_budget_api.py` — aktivite yokken tam
tavan, gerçek bir settlement sonrası doğru düşme, brief'siz projede
`null` tavan.

`npm run build` temiz. `pytest -q`: **229 passed, 11 deselected**.

## Altyazı düzeltme (2026-09-11, sekizinci tur devamı)

Spec §5.3'ün editör zorunlu işlemlerinden biri: "altyazı düzeltme". Bir
sahnenin `caption_text`'i saf bir metin alanı (Asset işaretçisi değil,
Take gibi bir taşıma sorunu yok) olduğundan, `select_take`/`set_shot_locks`
ile aynı "yerinde güncelle, yeni revizyon açma" deseniyle
`set_shot_caption` eklendi — `PATCH /projects/{id}/shots/{shot_id}/caption`.
Hiçbir LLM çağrısı yapmıyor, tamamen ücretsiz. Senaryo ekranındaki her
sahne kartına düzenlenebilir bir metin alanı + "Kaydet" düğmesi eklendi.

**Canlı kanıt** (gerçek Synova projesi, Hook sahnesi):
1. `PATCH .../caption {"caption_text": "CANLI DUZELTME TESTI - ..."}` →
   `200`, yanıt yeni metni doğru yansıttı.
2. `POST .../timeline/build` yeniden çağrıldı — altyazı kanalındaki
   `transform.captionText` gerçekten yeni metni gösterdi (diğer iki
   sahnenin metni değişmedi).
3. Orijinal metin geri yüklendi (`PATCH .../caption` ile), gerçek proje
   verisi test öncesi hâline döndürüldü.

Birim testleri eklendi: `test_revisions_service.py` (3 test — üzerine
yazma, temizleme/`null`, bilinmeyen sahne 404), `test_revisions_api.py`
(2 test).

`npm run build` temiz. `pytest -q`: **234 passed, 11 deselected**.

## Klip taşıma: sahne sıralama (2026-09-11, sekizinci tur devamı)

Spec §5.3'ün bir diğer editör zorunlu işlemi: "klip taşıma". `order_index`
saf bir pozisyon alanı olduğundan (Asset işaretçisi değil), kilit/altyazı
düzenlemeleriyle aynı "yerinde güncelle, yeni revizyon açma" deseniyle
`reorder_shots` eklendi — `PUT /projects/{id}/revisions/{revision_id}/order`,
`shot_order`'ın revizyonun TÜM sahnelerinin bir permütasyonu olduğunu
doğruluyor (eksik/fazla/yabancı id varsa 422). Senaryo ekranındaki her
sahne kartına ▲/▼ taşıma düğmeleri eklendi.

**Canlı kanıt** (gerçek Synova projesi, revizyon `4f3f7dc4-…`):
1. İki oynanış sahnesi (`0c749b7f-…`/`d4b346d2-…`) yer değiştirildi —
   `PUT .../order` yanıtı doğru yeni `order_index` sırasını döndü.
2. `POST .../timeline/build` yeniden çağrıldı — video track'indeki
   `start_frame` sıralaması gerçekten yeni sahne sırasını yansıttı.
3. Orijinal sıra geri yüklendi, gerçek proje verisi test öncesi hâline
   döndürüldü.

Birim testleri eklendi: `test_revisions_service.py` (3 test — yerinde
güncelleme, permütasyon olmayan giriş reddi, bilinmeyen revizyon 404),
`test_revisions_api.py` (2 test).

`npm run build` temiz. `pytest -q`: **239 passed, 11 deselected**.

## Ses seviyesi normalizasyonu (2026-09-11, dokuzuncu tur)

Spec §16.4: "Ses hedefi başlangıç preset'i olarak yaklaşık -16 LUFS
integrated ve true peak ≤ -1 dBTP; bu değerler platform zorunluluğu
değil ürün miks varsayılanı." `app/media/audio.py::normalize_loudness`
eklendi — ffmpeg'in `loudnorm` filtresiyle iki geçişli (ölç, sonra ölçülen
değerlerle uygula) EBU R128 normalizasyonu yapıyor. `render_timeline_to_asset`
(`app/services/render.py`) Remotion render'ı bitirdikten sonra bunu
çağırıyor; başarılıysa dosyayı yerinde normalize edilmiş kopyayla
değiştiriyor, ölçümü `Asset.audio_info_json`'a yazıyor. Ölçülemeyen
girdide (`ffmpeg`'in kendi `-inf` LUFS eşiği — gerçek anlamda sessiz/
ölçülemez sinyal) veya herhangi bir ffmpeg geçişi başarısız olursa dosya
olduğu gibi bırakılıyor — bir mix iyileştirmesi asla zaten başarılı bir
render'ı başarısız etmiyor.

**Geliştirirken gerçek bir hata bulundu ve düzeltildi:** ilk yazımda
`-c:v copy` bayrağı koşulsuz ekleniyordu; gerçek bir ElevenLabs ses
dosyasıyla (video akışı olmayan bir MP3) test edilince ffmpeg "Invalid
argument" ile başarısız oldu — kopyalanacak bir video akışı yoktu.
`technical_qc.probe_media` ile girdinin gerçekten video akışı olup
olmadığı kontrol edilip bayrak yalnızca varsa ekleniyor artık; mp3 çıktısı
için de `aac` yerine `libmp3lame` kullanılıyor.

**Canlı kanıt (üç ayrı gerçek dosyayla):**
1. **Gerçek ElevenLabs seslendirme örneği** (bu oturumun Safha 8'inde
   üretilmiş gerçek bir MP3, `backend/.tools/test_capture/` altına
   kopyalandı — yerel geliştirme artefaktı, commit edilmiyor):
   ölçüm gerçek bir LUFS değeri verdi; çıktı dosyası yeniden ölçüldüğünde
   sonucun hedefe (-16 LUFS, ±1.5 tolerans) yaklaştığı doğrulandı — yani
   düzeltme gerçekten "çalıştı" iddiası, yalnızca ffmpeg'in 0 döndüğü
   değil.
2. **Gerçek, sessize yakın bir scrcpy kaydı** (Safha 4'ün
   `safha4_live_test.mp4`'ü — `test_technical_qc.py` da aynı dosyayı
   kullanıyor): ffmpeg bunun `input_i: -inf` (ölçülemez) olduğunu
   raporladı; fonksiyonun bunu doğru şekilde `None` döndürüp dosyaya
   dokunmadığı doğrulandı — bu gerçek bir bulgu (bu kaydın gerçekten
   ölçülebilir sesi yok), fonksiyon hatası değil.
3. **Gerçek Synova projesi, tam bir önizleme render'ı**: `POST
   .../render/preview` tetiklendi, gerçek bir Remotion render'ı
   tamamlandı, sonuçtaki Asset'in `audio_info_json`'ı gerçek ölçümü
   taşıyordu: `measured_integrated_lufs: -17.15` (hedef: `-16.0`),
   `measured_true_peak_dbtp: -5.33`.

Birim testleri eklendi: `test_audio_media.py` (6 test — ffmpeg eksik,
ölçüm+uygulama akışı, sessiz girdi atlama, ölçüm/uygulama/timeout hata
yolları, audio-only girdi için `-c:v` atlanması), `test_render_service.py`'e
2 yeni test (normalizasyon başarılı/başarısız yolları için
`audio_info_json` doğrulaması). `tests/integration/test_audio_normalization.py`
gerçek dosyalarla iki test (yukarıdaki 1 ve 2).

`pytest -q`: **251 passed, 11 deselected**.

## Gerçek hata: desteklenmeyen süreli sahneler her zaman video üretimini başarısız ediyordu (2026-09-11, dokuzuncu tur)

Kullanıcı gerçek Synova projesini tamamlamak isteyince (Hook + montaj
+ CTA sahnelerinin gerçek videosu eksikti), CTA sahnesinin video
üretiminin HER ZAMAN başarısız olduğu yeniden teyit edildi:
`generate_ai_scene_take`, sahnenin tam süresini (`target_frames/fps`,
CTA için 2.5sn) doğrudan Veo'ya istek olarak gönderiyordu, ama
`google/veo-3.1-lite` yalnızca [4,6,8]sn destekliyor. `validate_request`
zaten doğru şekilde reddediyordu — ama hatanın kendi mesajı ("planner
must render the nearest supported duration and trim the used span, not
arbitrarily speed up the clip") aslında ne yapılması gerektiğini
söylüyordu; kod bunu hiç uygulamıyordu.

**Düzeltme:** `_pick_generation_duration_s` eklendi —
`video_provider.list_models()`'dan modelin gerçek
`supported_durations_s` listesini okuyup hedef süreye eşit veya ondan
büyük en yakın süreyi seçiyor (asla daha kısa — bu, klibi hızlandırmak
yerine kesmek anlamına gelirdi). Katalog isteği başarısız olursa
(örn. geçici bir ağ hatası) sessizce eski davranışa (tam hedef süre)
geri dönüyor, üretimi asla bloklamıyor.

Ayrı bir kod incelemesiyle doğrulandı ki Remotion render tarafı zaten
her video öğesini `<Sequence durationInFrames={item.duration_frames}>`
ile sahnenin gerçek süresine kırpıyor (`AdComposition.tsx`) — yani
`out_us`/ek bir "trim" adımına hiç gerek yok; talep edilen video daha
uzun gelse bile (örn. CTA için 2.5sn yerine 4sn), timeline zaten yalnızca
ilk 2.5sn'sini gösteriyor. Bu, kodun geri kalanına dokunulmadan yalnızca
istek süresini düzeltmenin yeterli olduğu anlamına geliyordu.

Birim testleri eklendi (`test_generation_service.py`, 3 test): desteklenmeyen
tam süre → en yakın büyük desteklenen süre istendiği, zaten desteklenen
tam süre → aynen istendiği, katalog erişimi başarısız → eski davranışa
(tam hedef süre) düşüldüğü.

`pytest -q`: **254 passed, 11 deselected**.
