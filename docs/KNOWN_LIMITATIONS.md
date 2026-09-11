# Bilinen Sınırlamalar (KNOWN_LIMITATIONS.md)

Bu dosya, gerçek sağlayıcı/oyun/OS sınırlamalarını ve canlı doğrulaması
yapılamamış alanları listeler (spec §24.1). "Tüm testler geçti" iddiası bu
liste boşalana kadar kullanılmaz.

## Canlı doğrulama engelleri (2026-09-11 itibarıyla)

1. ~~OpenRouter API anahtarı yok~~ — **çözüldü (2026-09-11)**: kullanıcı
   gerçek anahtarını Ayarlar ekranından girdi, Windows Credential Manager'a
   kaydedildi. Yönetmen (concept/plan/sahne prompt üretimi), operatör (oyun
   kontrol stratejisi, keşif+çekim) ve video üretimi (`/videos` submit-
   poll-download) artık hepsi CANLI doğrulandı. Reviewer ajanı (spec §10,
   otomatik take değerlendirmesi) henüz uygulanmadı — Take'ler şu an
   yalnızca teknik QC'ye göre `pending`/`rejected`/`uncertain` oluyor,
   içerik/marka uyumu bir insan veya ayrı bir reviewer çağrısı gerektiriyor.
2. ~~ElevenLabs API anahtarı yok~~ — **çözüldü (2026-09-11)**: kullanıcı
   gerçek anahtarını girdi, `list_voices()` ile canlı doğrulandı (21 ses
   bulundu). TTS üretimi (`synthesize`) artık CANLI doğrulandı — gerçek
   Türkçe bir seslendirme metninden gerçek bir MP3 üretildi.
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

## Safha 7 — gerçek çekim (2026-09-11)

1. **Operatör kararı şeması, Safha 5'in keşif şeması ile aynı** (bilinçli
   yeniden kullanım). `finish_discovery` eylemi bu bağlamda "istenen olay bu
   sahnede gerçekleşti" anlamına geliyor — spec §11.2'nin ayrı
   start/stop/mark_event operatör eylemleri henüz modele doğrudan
   sunulmuyor; kayıt başlatma/durdurma tamamen `CaptureManager` tarafında,
   operatörün haberi olmadan yönetiliyor. Çalışıyor ve canlı doğrulandı, ama
   spec'in tam eylem setine göre daraltılmış.
2. ~~Stüdyo arayüzünde "Çekim" adımı yok~~ — **çözüldü (2026-09-11, aynı
   gün ikinci tur)**: `apps/web`'e gerçek bir Çekim ekranı eklendi (cihaz
   seçimi, sahne başına çek/yeniden çek, take listesi + video önizleme,
   "Bu çekimi seç") ve gerçek tarayıcıda uçtan uca CANLI doğrulandı.
3. **Reddedilmiş bir take'i geri getirme/arşivden çıkarma UI'ı yok** —
   `status="rejected"` bir take listede görünür ve seçilemez durumda
   kalır, ama onu silme veya "yine de kullan" gibi bir eylem yok.
4. **Olay tabanlı otomatik in/out kırpma yok.** Her take'in tamamı
   (`in_us=0`, `out_us=süre`) saklanıyor; `success_predicate`'e göre gerçek
   olay anını video içinde bulup kırpmak (spec §11.6/12.x) ayrı bir iş.

## Safha 8 — AI sahne + ses üretimi (2026-09-11)

1. **`OpenRouterVideoProvider.estimate_cost()` gerçek fiyatlandırma
   şekillerinin çoğunu okuyamıyor.** Yalnızca eski
   `pricing.cents_per_second_output` alanını arıyor; gerçek katalogdaki 29
   modelin çoğu bunun yerine `duration_seconds_*` (dolar, sent değil) veya
   `video_tokens*` gibi farklı anahtarlar kullanıyor — bu yüzden çoğu model
   için maliyet tahmini "unknown" dönüyor (sessizce sıfır DEĞİL, ama yine de
   yanlış bilgilendirici). Canlı doğrulanan `google/veo-3.1-lite` çağrısının
   gerçek maliyeti bu tahminden değil, OpenRouter'ın kendi kullanım
   panelinden teyit edilmelidir.
2. **Toplu/otomatik üretim yok.** Her `ai_generated` sahne ve her
   seslendirme tek tek, elle (API çağrısıyla) tetikleniyor; Stüdyo'da bunun
   için bir ekran henüz eklenmedi (Çekim ekranı yalnızca `gameplay`
   sahneleri kapsıyor).
3. **Lipsync (`LipSyncProvider`) hâlâ yalnızca arayüz düzeyinde.** Üretilen
   ses ile bir AI insan sahnesini senkronlamak bu turda kapsam dışı.
4. **Ses varlığı `shots.voice_asset_id` gibi bir kolona değil, sadece
   `Asset.metadata_json.shot_id`'ye bağlı.** Bu, sorgulanabilir ve doğru
   çalışıyor, ama şemada birinci sınıf bir ilişki değil — Safha 9/10'da
   timeline'a bağlarken bu sözleşmeye dikkat edilmeli.

## Safha 9 — gerçek timeline + render (2026-09-11)

1. **Altyazı (subtitle) track'i hâlâ pozisyon placeholder'ı.** `caption_text`
   bir sahnede varsa timeline'a doğru start/duration ile ekleniyor, ama
   `AdComposition`'da hâlâ `[altyazı placeholder — item-id]` yazısı
   gösteriyor — gerçek metni ekrana basmak bu turda kapsam dışı kaldı.
2. **Ses karıştırma/kısma (ducking) yok.** Gameplay/AI klibinin kendi
   gömülü sesi (varsa) ve ayrı seslendirme aynı anda, hiçbir seviye
   ayarlaması olmadan çalıyor.
3. **Canvas sabit 1080x1920.** `placement_id`'den gerçek bir en-boy oranı
   türetilmiyor; farklı native çözünürlükteki kaynaklar (gameplay
   1080x2400, AI sahne 720x1280) `object-fit: cover` ile kırpılarak
   sığdırılıyor — kasıtlı bir kırpma/kompozisyon aracı yok.
4. **Render senkron ve tek seferlik.** `render_preview` job'u tüm render
   süresince (dakikalar sürebilir) worker thread'ini bloke ediyor; ilerleme
   yüzdesi raporlanmıyor, sadece queued/running/succeeded/failed durumu var.
5. **Editör arayüzü (sahne sırasını değiştirme, crop, manuel senkron) yok**
   — timeline tamamen sunucu tarafında, sahne sırasına göre otomatik
   üretiliyor.

## Safha 10 — revizyon/kilit/varyasyon (2026-09-11)

1. **UI yok.** Varyasyon üretimi yalnızca API üzerinden kullanılabilir;
   Stüdyo'da revizyonlar arası karşılaştırma, kilit açma/kapama veya
   "bu sahneyi revize et" ekranı henüz eklenmedi.
2. **Yalnızca tek-sahne revizyonu var.** Bir çağrıda birden fazla sahne
   revize edilebilir (`shot_instructions` bir dict), ama her biri ayrı bir
   LLM çağrısıyla, sırayla işleniyor — toplu/tutarlı bir "tüm reklamı yeniden
   düşün" modu yok.
3. **Kilit yalnızca `visual` alanı için zorunlu kılınıyor.** `voice`/
   `caption`/`timing` kilitleri varsa, yönetmenin döndürdüğü yeni değer
   yerine eski değer korunuyor (kodda var), ama bu üç kilit için `visual`
   gibi açık bir 422 reddi yok — yalnızca sessizce eski değer kullanılıyor.
   `visual` özel: onu değiştirmeye çalışmak baştan reddediliyor, çünkü
   hangi Take'in kullanılacağı LLM çıktısına değil ayrı bir çekim/üretim
   adımına bağlı.

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
