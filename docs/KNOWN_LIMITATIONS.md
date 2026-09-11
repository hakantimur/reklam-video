# Bilinen Sınırlamalar (KNOWN_LIMITATIONS.md)

Bu dosya, gerçek sağlayıcı/oyun/OS sınırlamalarını ve canlı doğrulaması
yapılamamış alanları listeler (spec §24.1). "Tüm testler geçti" iddiası bu
liste boşalana kadar kullanılmaz.

## Canlı doğrulama engelleri (2026-09-11 itibarıyla)

1. ~~OpenRouter API anahtarı yok~~ — **çözüldü (2026-09-11)**: kullanıcı
   gerçek anahtarını Ayarlar ekranından girdi, Windows Credential Manager'a
   kaydedildi. Yönetmen (concept/plan/sahne prompt üretimi), operatör (oyun
   kontrol stratejisi, keşif+çekim) ve video üretimi (`/videos` submit-
   poll-download) artık hepsi CANLI doğrulandı. ~~Reviewer ajanı (spec
   §10, otomatik take değerlendirmesi) henüz uygulanmadı~~ — **çözüldü
   (2026-09-11, dördüncü tur)**: `POST /projects/{id}/shots/{shot_id}/review`
   gerçek sahneden 4 kare örnekleyip (spec'in reviewer prompt'unun
   gerektirdiği gibi, metin açıklamasından değil) gerçek bir vision LLM
   çağrısıyla `pass`/`fail`/`uncertain` + somut kanıt/kusur listesi
   üretiyor, `qa_reports` tablosuna kalıcı yazıyor. `run_revision_qa` artık
   varsa en son içerik incelemesini de kontrol ediyor (fail ise export'u
   bloklar) — ama içerik incelemesi ZORUNLU değil: hiç incelenmemiş bir
   take yalnızca teknik gerekçelerle geçebilir. Gerçek Synova projesinde
   CANLI doğrulandı: gerçek gameplay kaydından 4 kare örneklenip modele
   gönderildi, model "0 of 4 selected" → "2 of 4" gibi somut, gerçek
   ekrandan gözlemlenen ayrıntılarla `pass` verdisi verdi (uydurma değil).
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
2. ~~Toplu/otomatik üretim yok, Stüdyo'da ekran yok~~ — **çözüldü
   (2026-09-11, üçüncü tur)**: Stüdyo'ya gerçek bir "Taslak" ekranı
   eklendi (her AI sahnesi için üret/yeniden üret + video önizleme, her
   seslendirme için gerçek ElevenLabs ses listesinden seçim + üret + audio
   önizleme). Toplu üretim hâlâ yok — her sahne/seslendirme tek tek
   tetikleniyor, sırayla değil paralel de değil.
3. **Lipsync (`LipSyncProvider`) hâlâ yalnızca arayüz düzeyinde.** Üretilen
   ses ile bir AI insan sahnesini senkronlamak bu turda kapsam dışı.
4. **Ses varlığı `shots.voice_asset_id` gibi bir kolona değil, sadece
   `Asset.metadata_json.shot_id`'ye bağlı.** Bu, sorgulanabilir ve doğru
   çalışıyor, ama şemada birinci sınıf bir ilişki değil — Safha 9/10'da
   timeline'a bağlarken bu sözleşmeye dikkat edilmeli.
5. **Seslendirme Asset'lerinde `duration_us` hesaplanmıyor.**
   `generate_voice_asset` ElevenLabs'ten gelen mp3 bayt dizisini doğrudan
   diske yazıyor, süresini probe etmiyor — Malzemeler ekranında bu yüzden
   ses dosyaları için süre "—" görünüyor (dosyanın kendisi gerçek ve
   çalıyor, yalnızca metadata eksik).

## Safha 9 — gerçek timeline + render (2026-09-11)

1. ~~Altyazı (subtitle) track'i hâlâ pozisyon placeholder'ı~~ — **çözüldü
   (2026-09-11, üçüncü tur)**: `timeline.py` artık `transform.captionText`
   içinde gerçek `caption_text`'i taşıyor, `AdComposition` bunu gerçekten
   ekrana basıyor. Gerçek Synova projesinde yeniden render edilip bir kare
   bağımsız olarak çıkarıldı — Türkçe altyazı ("Sekiz farklı oyunla her
   gün yeni bir beyin harikası keşfedin.") gerçek AI sahnesinin üzerinde
   doğru şekilde görünüyor.
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
   üretiliyor. Taslak ekranı "Timeline oluştur"/"Önizleme render et"
   düğmeleriyle bunu tetikleyip sonucu oynatabiliyor (2026-09-11, üçüncü
   tur, tarayıcıda CANLI denendi), ama sırayı/kırpmayı değiştiremiyor.

## Safha 10 — revizyon/kilit/varyasyon (2026-09-11)

1. **UI yok.** Varyasyon üretimi yalnızca API üzerinden kullanılabilir;
   Stüdyo'da revizyonlar arası karşılaştırma, kilit açma/kapama veya
   "bu sahneyi revize et" ekranı henüz eklenmedi.
2. **~~Bir take hiç "seçilmemişse" varyasyonda sessizce kaybolabiliyordu~~
   — çözüldü (2026-09-11, canlı test sırasında bulundu):** taşıma mantığı
   artık `selected_take_id` yoksa da `timeline.selected_or_best_take`
   fallback'ini kullanıyor; ayrıntı için bkz. PROGRESS.md Safha 10 satırı.
3. **Yalnızca tek-sahne revizyonu var.** Bir çağrıda birden fazla sahne
   revize edilebilir (`shot_instructions` bir dict), ama her biri ayrı bir
   LLM çağrısıyla, sırayla işleniyor — toplu/tutarlı bir "tüm reklamı yeniden
   düşün" modu yok.
4. **Kilit yalnızca `visual` alanı için zorunlu kılınıyor.** `voice`/
   `caption`/`timing` kilitleri varsa, yönetmenin döndürdüğü yeni değer
   yerine eski değer korunuyor (kodda var), ama bu üç kilit için `visual`
   gibi açık bir 422 reddi yok — yalnızca sessizce eski değer kullanılıyor.
   `visual` özel: onu değiştirmeye çalışmak baştan reddediliyor, çünkü
   hangi Take'in kullanılacağı LLM çıktısına değil ayrı bir çekim/üretim
   adımına bağlı.

## Safha 11 — QA + teslim (2026-09-11)

1. ~~İçerik/marka güvenliği reviewer'ı yok~~ — **çözüldü (2026-09-11,
   dördüncü tur)**: `app/services/review.py` + `POST .../review` eklendi,
   gerçek kare örneklemesi + gerçek vision LLM çağrısıyla CANLI doğrulandı
   (bkz. yukarıdaki Safha 8/10 dışı "OpenRouter API anahtarı" satırındaki
   ayrıntı). Ama içerik incelemesi **isteğe bağlı** — hiç çalıştırılmamışsa
   QA'yı bloklamıyor, yalnızca çalıştırılıp `fail` dönerse bloklar. Bu
   yüzden "QA geçti" hâlâ "teknik (ve varsa incelenmiş içerik açısından)
   dışa aktarılabilir" anlamına gelir, "her kare mutlaka bir LLM tarafından
   incelendi" anlamına gelmez — bunu zorunlu kılmak, önceden doğrulanmış
   canlı export akışını (hiç reviewer çalıştırmadan geçen) geriye dönük
   bozar, bu yüzden bilinçli olarak yapılmadı. UI'da bu incelemeyi
   tetikleyecek bir düğme de henüz yok (yalnızca API).
2. **Yerleşime (placement_id) özgü format doğrulaması yok.** Brief'teki
   `placement_id` hiçbir yerde gerçek bir platform format kuralına
   (en-boy oranı, maksimum süre, codec sınırı vb.) eşlenmiyor — bu,
   uydurma bir kural tablosu yazmamak için bilinçli olarak atlandı.
3. ~~UI yok~~ — **çözüldü (2026-09-11, üçüncü tur)**: Stüdyo'ya gerçek bir
   "Çıktı" ekranı eklendi (QA raporu + "Dışa aktar", QA geçmeden devre
   dışı) ve tarayıcıda CANLI denendi — gerçek eksik sahneler doğru
   listelendi, düğme doğru şekilde devre dışı görünüyordu.
4. **Export ve preview render aynı mekanizmayı paylaşıyor**
   (`render_timeline_to_asset`) — export'a özgü ekstra bir doğrulama
   (ör. gerçek yerleşim format kontrolü) eklenmedi, yalnızca QA kapısı var.

## Safha 12 — Windows paketleme (2026-09-11)

1. **Bağımsız/tek-tıkla kurulan bir installer yok.** Kullanıcı hâlâ
   Python 3.11+, Node.js ve (canlı cihaz özellikleri için) Android SDK
   platform-tools'u kendisi kurmalı; `SETUP.bat` bunların üzerine gerçek
   bir kurulum yapıyor (venv, pip install, alembic migrate, ffmpeg/scrcpy
   indirme, npm install/build) ama bunları bir Python/Node çalışma
   zamanını da içeren tek bir `.exe`/`.msi` içine paketlemiyor.
2. **Kod imzalama yok.** Üretilecek herhangi bir installer/exe Windows
   SmartScreen tarafından "tanınmayan yayıncı" olarak işaretlenir.
3. **Otomatik güncelleme yok.** Yeni bir sürüm almak, `git pull` +
   `SETUP.bat`'ı tekrar çalıştırmak anlamına geliyor.
4. **Bu regresyon tek makinede (geliştirme makinesi) çalıştırıldı.**
   Temiz bir ikinci Windows makinesinde `SETUP.bat`'tan itibaren tüm
   akışın çalıştığı bu oturumda ayrıca doğrulanmadı.

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
3. ~~Malzemeler ve İşler ekranları bilinçli olarak iskelet düzeyinde~~ —
   **çözüldü (2026-09-11, üçüncü tur)**: `GET /projects/{id}/jobs` eklendi
   (liste yoktu, yalnızca tekil `GET /jobs/{id}` vardı); her iki ekran da
   artık aktif projenin gerçek verisini gösteriyor — Malzemeler gerçek
   video/ses önizlemeleriyle (tarayıcıda CANLI denendi, tüm gecenin gerçek
   çıktıları: gameplay kayıtları, AI sahneleri, seslendirme, önizleme/
   export render'ları göründü), İşler gerçek iş geçmişiyle (tür/durum/
   geçen süre/hata + duraklat/devam ettir/iptal, tüm gecenin gerçek
   discover/capture/generate/render job'ları göründü, biri gerçek bir
   `handler_error` ile). **Maliyet takibi kısmen çözüldü (2026-09-11,
   dördüncü tur)**: `generate_ai_scene` artık OpenRouter'ın video poll
   yanıtındaki gerçek `usage.cost` alanını (tahmin değil, sağlayıcının
   kendi onayladığı gerçek harcama) okuyup hem Asset metadata'sına hem
   gerçek bir `BudgetEntry` (`entry_type=settlement, confidence=confirmed`)
   satırına yazıyor — CANLI doğrulandı (gerçek $0.32 harcama gerçek bir
   satıra dönüştü). `discover`/`capture_shot`/`generate_voice`/
   `render_preview`/`export_final` hâlâ hiçbir maliyet kaydı yazmıyor —
   chat completion (yönetmen/operatör) çağrılarının gerçek maliyeti hâlâ
   izlenmiyor, ElevenLabs TTS'in de kendi yanıtında kullanılabilir bir
   maliyet alanı doğrulanmadı.
4. **npm audit: 4 orta/yüksek risk uyarısı** (`react-router-dom` açık
   yönlendirme, `esbuild` dev-server isteği sızıntısı). İkisi de yalnızca
   majör sürüm atlamasıyla (`react-router-dom` 6→7, `vite` 5→8) düzeltiliyor;
   bu safhada kapsam dışı bırakıldı, bkz. DECISIONS.md.

## Donanım / oyun durumu (olumlu not)

- Hedef oyun `Synova` gerçek `.aab` dosyası ve iki AVD (`synova_shot`,
  `synova_test`) mevcut. Bu, emülatör köprüsü ve kontrol döngüsü testlerinin
  (Safha 4) API anahtarı gerekmeden canlı yapılabileceği anlamına gelir.

Bu bölüm ilerledikçe güncellenecektir.
