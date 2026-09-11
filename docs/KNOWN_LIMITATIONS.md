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
5. ~~Seslendirme Asset'lerinde `duration_us` hesaplanmıyor~~ — **çözüldü
   (2026-09-11, beşinci tur)**: `generate_voice_asset` artık gerçek
   `ffprobe` ile süreyi ölçüyor (probe başarısız olursa `None`'a düşüyor,
   asla uydurmuyor). Gerçek bir seslendirme yeniden üretilerek CANLI
   doğrulandı: 48,527 baytlık gerçek MP3 için `duration_us=2,972,154`
   (2.97sn) doğru şekilde kaydedildi.

## Safha 9 — gerçek timeline + render (2026-09-11)

1. ~~Altyazı (subtitle) track'i hâlâ pozisyon placeholder'ı~~ — **çözüldü
   (2026-09-11, üçüncü tur)**: `timeline.py` artık `transform.captionText`
   içinde gerçek `caption_text`'i taşıyor, `AdComposition` bunu gerçekten
   ekrana basıyor. Gerçek Synova projesinde yeniden render edilip bir kare
   bağımsız olarak çıkarıldı — Türkçe altyazı ("Sekiz farklı oyunla her
   gün yeni bir beyin harikası keşfedin.") gerçek AI sahnesinin üzerinde
   doğru şekilde görünüyor.
2. ~~Ses karıştırma/kısma (ducking) yok~~ — **kısmen çözüldü (2026-09-11,
   beşinci tur)**: bir sahnenin seslendirmesi varsa (`voice_items`'ta aynı
   `shot_id`), o sahnenin video klibinin kendi gömülü sesi otomatik olarak
   kısılıyor (`volume=0.2`), yoksa tam seviyede kalıyor —
   `timeline.py`'nin ürettiği `transform.hasVoiceOver` alanına göre
   `AdComposition`'da uygulanıyor. Gerçek Synova projesinde yeniden
   render edilerek hatasız çalıştığı doğrulandı; sabit `0.2` değeri bir
   sezgisel varsayım, gerçek ses seviyesi ölçümüyle kalibre edilmedi.
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
   bozar, bu yüzden bilinçli olarak yapılmadı. ~~UI'da bu incelemeyi
   tetikleyecek bir düğme de henüz yok~~ — **çözüldü (2026-09-11, beşinci
   tur)**: `GET .../shots/{shot_id}/review` uç noktası eklendi (son
   içerik incelemesini döner, hiç incelenmemişse `null`), Taslak
   ekranındaki her AI sahne kartına "İçerik incele (AI)" düğmesi ve
   geçti/reddedildi/belirsiz rozeti + gerekçe/kusur listesi eklendi.
   Backend tarafı gerçek Synova projesindeki Hook sahnesi üzerinde CANLI
   doğrulandı: önce `GET .../review` → `null` (hiç incelenmemiş), sonra
   `POST .../review` ile gerçek bir vision LLM çağrısı (job
   `7fcc9059-…`, `anthropic/claude-haiku-4.5`, 4 kare) → `outcome: pass`,
   ardından tekrar `GET .../review` → aynı gerçek `reasoning`/`outcome`
   bilgisini döndü. Frontend tarafı `tsc -b` ile temiz derlendi; ancak bu
   oturumdaki tarayıcı önizleme sandbox'ı host'un `127.0.0.1:8765`
   backend'ine ağ erişimi olmadığından (`net::ERR_FAILED`), düğmenin
   gerçek bir tarayıcıda tıklanıp render edildiği görsel olarak
   doğrulanamadı — bu dürüstçe açık bir boşluk, sahte bir "tarayıcıda
   test edildi" iddiası değil.
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

## Şemada var, hiçbir yerde kullanılmayan tablolar (2026-09-11, sekizinci tur — envanter)

Kod tabanı sistematik olarak taranarak her model için gerçek bir
servis/API/job referansı olup olmadığı kontrol edildi. Üç tablo şemada
(ve muhtemelen migration'da) var ama uygulamanın hiçbir yerinde
okunmuyor/yazılmıyor — bunlar gizli bir hata değil, henüz inşa
edilmemiş spec özelliklerinin şema iskeleti:

1. **`character_profiles`** (`app/models/creative.py::CharacterProfile`)
   — spec §9.4/Safha 8'in "insanlı sahneler aynı karakter referansını
   kullanır" gereksinimine karşılık geliyor (wardrobe, location,
   voice_profile_id, reference_asset_ids_json, continuity_notes).
   `Shot.character_id` alanı da var ama hiçbir yerde set edilmiyor/
   okunmuyor. Synova'nın gerçek reklamları insan aktör içermediği
   (oynanış + AI b-roll) için bu turda gerçek bir test senaryosu yoktu;
   inşa etmek "gerçek model testi yoksa bu safha canlı doğrulaması
   tamamlandı sayılmaz" ilkesini ihlal ederdi — bu yüzden bilinçli
   olarak yapılmadı.
2. **`asset_rights`** (`AssetRights` — source_name, source_url,
   license_note, user_provided) — kullanıcı tarafından yüklenen
   varlıkların (stok görüntü vb.) telif/kaynak bilgisini tutmak için;
   uygulamada henüz bir "varlık yükle" akışı olmadığı için (tüm
   varlıklar ya gerçek çekim ya da AI üretimi) kullanılmıyor.
3. **`performance_notes`** (`PerformanceNote` — impressions, views,
   clicks, installs, spend) — export sonrası gerçek reklam performansını
   kaydetmek için; bunun gerçek anlamı olması için bir reklam platformu
   entegrasyonu (Meta/Google Ads API vb.) gerekir, bu oturumda hiç
   kapsam dahilinde değildi.

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
   satıra dönüştü). ~~`discover`/`capture_shot`/`generate_voice`/
   `render_preview`/`export_final` hâlâ hiçbir maliyet kaydı yazmıyor —
   chat completion (yönetmen/operatör) çağrılarının gerçek maliyeti hâlâ
   izlenmiyor~~ — **chat completion tarafı çözüldü (2026-09-11, beşinci
   tur devamı)**: gerçek bir OpenRouter `/chat/completions` çağrısıyla
   doğrulandı ki yanıt her zaman gerçek, sağlayıcı onaylı bir
   `usage.cost` alanı taşıyor (aynı `usage.cost` sözleşmesi, video
   poll'daki gibi). `OpenRouterTextVisionProvider` artık her
   `generate_structured` çağrısının `usage.cost` değerini
   `total_cost_usd`'de biriktiriyor (tek bir job içinde birden fazla LLM
   çağrısı yapan operatör döngüsü/yönetmen retry'ı için doğru toplam);
   `discover`, `capture_shot` ve `review_take` job'ları artık bu toplamı
   gerçek bir `BudgetEntry` satırına yazıyor, `generate_ai_scene` ise
   video maliyetiyle metin/prompt maliyetini tek bir satırda topluyor
   (`settle()` job başına yalnızca bir kayda izin verdiği için). CANLI
   doğrulandı: gerçek Synova projesinde bir `review_take` job'u koştu,
   gerçek bir vision LLM çağrısı yaptı, ve tam olarak
   `amount_microusd=5957` (`$0.005957`) değerinde gerçek bir
   `settlement` satırı yazıldığı DB'den doğrudan okunarak teyit edildi.
   `generate_ai_scene`'in birleşik (video+metin) yolu ayrı bir gerçek
   API çağrısıyla değil, aynı mekanizmayı (`_settle_llm_cost`) kullandığı
   ve toplama mantığı gerçek sayılarla birim testiyle doğrulandığı için
   canlı olarak ayrıca denenmedi (bir video üretimi ~$0.12–0.32 arası
   gerçek harcamaya yol açtığından gereksiz tekrar harcamadan kaçınıldı).
   `generate_voice` (ElevenLabs) hâlâ maliyet yazmıyor — ElevenLabs'in
   `POST /text-to-speech` yanıtı ham ses baytlarından ibaret, ne bir
   `usage`/`cost` alanı ne de karakter sayısı döner; gerçek maliyet
   kullanıcının hangi ElevenLabs abonelik katmanında olduğuna bağlı ve
   bu bilgi API'den okunamıyor — bu yüzden uydurma bir fiyat tablosu
   yazmak yerine bilinçli olarak izlenmeden bırakıldı. `render_preview`/
   `export_final` yerel ffmpeg/Remotion çalıştırıyor, hiçbir ücretli API
   çağrısı yapmıyor — bu ikisi için "maliyet kaydı yok" zaten doğru
   davranış.
4. **npm audit: 4 orta/yüksek risk uyarısı** (`react-router-dom` açık
   yönlendirme, `esbuild` dev-server isteği sızıntısı). İkisi de yalnızca
   majör sürüm atlamasıyla (`react-router-dom` 6→7, `vite` 5→8) düzeltiliyor;
   bu safhada kapsam dışı bırakıldı, bkz. DECISIONS.md.

## Donanım / oyun durumu (olumlu not)

- Hedef oyun `Synova` gerçek `.aab` dosyası ve iki AVD (`synova_shot`,
  `synova_test`) mevcut. Bu, emülatör köprüsü ve kontrol döngüsü testlerinin
  (Safha 4) API anahtarı gerekmeden canlı yapılabileceği anlamına gelir.

## Kullanıcı yönetmen incelemesi bulguları (2026-09-11, onuncu tur)

Gerçek export (`exports/v001/export-70c5965b.mp4`, sha256 `298935b1...`)
kullanıcı tarafından izlendi. Doğrulanan sorunlar:

1. **AI sahneleri gerçek Synova'yı göstermiyordu — DÜZELTİLDİ VE CANLI DOĞRULANDI (2026-09-11).**
   Kök neden: `generate_ai_scene_take` `reference_image_paths`'i hiç
   kullanmıyordu. Düzeltme: yeni `_find_real_gameplay_reference_image`
   (`app/services/generation.py`), projedeki en son gerçek
   `emulator_capture` gameplay videosundan bir kare örnekleyip base64
   `data:image/png;base64,...` URI'ına çevirip `reference_image_paths`'e
   geçiriyor. Bu değişikliği canlı denerken **provider katmanının
   `frame_images` şeması da hiç gerçek API'ye karşı test edilmemişti ve
   yanlıştı** — iki ayrı gerçek `400 ZodError` alındı ve düzeltildi
   (bkz. TEST_REPORT.md "OpenRouter frame_images şeması" bölümü).
   Düzeltmeden sonra 3 sahne de gerçekten yeniden üretildi
   (`google/veo-3.1-lite`, gerçek maliyet), hepsi
   `grounded_in_real_gameplay: true` ile işaretlendi, ve çıkarılan
   kareler görsel olarak doğrulandı: artık gerçek Synova'nın "Repeat the
   pattern" hafıza oyunu ızgarası (yeşil hücreler, aynı tipografi/renk
   paleti) görünüyor — önceki tamamen jenerik/uydurma içerikten çok
   büyük bir iyileşme.
2. **ElevenLabs sesi robotikti — DÜZELTİLDİ VE CANLI DOĞRULANDI (2026-09-11).**
   Kök neden: `synthesize()` hiçbir zaman `voice_settings` göndermiyordu,
   ElevenLabs hesabın kayıtlı varsayılanına düşüyordu. Kullanılan ses de
   "Sarah - Mature, Reassuring, Confident" idi — enerjik bir mobil oyun
   reklamı için uygun olmayan bir ton. Düzeltme:
   `ElevenLabsProvider.DEFAULT_VOICE_SETTINGS` eklendi
   (`stability=0.4, similarity_boost=0.8, style=0.25,
   use_speaker_boost=true`) ve her zaman (override edilmedikçe)
   gönderiliyor; 3 seslendirme "Jessica - Playful, Bright, Warm" sesiyle
   gerçekten yeniden üretildi, gerçek asset metadata'sında tuned
   `voice_settings` doğrulandı.
3. Donuk/statik görünen ardışık gameplay çekimleri — her çekim kendi
   başına `blank_or_frozen` QC'sini geçiyor ama zaman çizelgesinde yan
   yana geldiklerinde komşu çekimle karşılaştıran bir kontrol yok. QC
   şu an her take'i izole değerlendiriyor. **Henüz düzeltilmedi** —
   kapsam dışı bırakıldı çünkü kök neden (uydurma görüntü) düzeltilirse
   AI sahneleri muhtemelen zaten daha dinamik olacak; gameplay
   çekimleri için ayrı bir iyileştirme gerekirse sonraki turda ele
   alınacak.
4. CTA sahnesinde bozuk/anlamsız uygulama ikonu metni — Veo'nun UI-mockup
   ağırlıklı sahnelerde sahte metin üretme eğilimi, muhtemelen prompt
   mühendisliğiyle (metin/ikon içeren sahnelerden kaçınma) azaltılabilir.
   **Henüz düzeltilmedi** — reference-image grounding düzeltmesinden
   sonra yeniden üretilen CTA sahnesinde de aynı sorun tekrar gözlemlendi
   ("Hext.. Nernd, Next & Next Round..", "Chtttotantatts yund ale wd
   counyind..." gibi anlamsız metin), yani grounding bunu çözmüyor —
   ayrı bir prompt-mühendisliği çalışması gerekiyor. Kapsam dışı.
5. Altyazı rozeti kısa metinlerde ("Şimdi İndir") konumlandırma
   tutarsızlığı. **Henüz düzeltilmedi**, kapsam dışı.

## KRİTİK: Tüm proje boyunca yanlış/eski bir build kullanılmış (2026-09-11, onikinci tur)

Kullanıcı düzeltilmiş örnek videoyu izledikten sonra "bu görüntüler de
benim değil" dedi — reference-image grounding düzeltmesi teknik olarak
çalışmasına rağmen. Araştırma gerçek kök nedeni ortaya çıkardı:

Emülatörde (`emulator-5554`) şimdiye kadar yüklü olan paket
`com.example.synova.dev`, `versionName=0.1.0`, 2026-09-06'da kurulmuş —
markasız, jenerik bir dev/placeholder build. Masaüstünde duran gerçek
`.aab` (`Desktop/SYNOVA_yeni_surum/SYNOVA-0.1.1-2.aab`, `versionName
0.1.1`, `versionCode 2`, gerçek paket adı `com.noriloop.synova`) hiçbir
zaman bu emülatöre kurulmamıştı. Bu, projenin EN BAŞINDAN BERİ — ilk
gerçek gameplay yakalamasından (`device_profiles`/`game_profiles`
tablosundaki `2026-09-11 05:50`'den itibaren tüm kayıtlar) bugüne kadar
— yanlış uygulamaya karşı çalıştığı anlamına geliyor. `game_profiles`
tablosundaki 3 ayrı keşif kaydı da yalnızca tek bir mekanik
tanımlıyor ("pattern-recall memory game... 4x4 grid") — oysa gerçek
uygulamanın onboarding akışı Memory/Attention/Logic/Speed/Math gibi
BEŞ farklı oyun kategorisi olduğunu gösteriyor (bkz. gerçek uygulamanın
"What do you want to work on?" ekranı). Yani proje boyunca hem "gerçek"
gameplay çekimleri hem de bunlardan türetilen AI grounding referansları
hep AYNI tek mini-oyunu (Pattern Memory / "Repeat the pattern") tekrar
tekrar gösterdi — kullanıcının "sekiz farklı oyun" talebine rağmen.

**Şu ana kadar yapılan (ücretsiz kısım, düzeltildi):**
- Gerçek `.aab`'den `bundletool` ile universal APK üretildi, yanlış
  build kaldırılıp gerçek `com.noriloop.synova` (v0.1.1) emülatöre
  kuruldu ve canlı doğrulandı (gerçek splash ekranı: "SYNOVA — Train
  your mind, five minutes a day", gerçek logo/renk paleti).
- `device_profiles.package_id` veritabanında `com.noriloop.synova`
  olarak güncellendi (bir `discover` job'unun kısmi/başarısız
  çalışması sırasında flush edildi, OpenRouter hatasından ETKİLENMEDEN
  kalıcı oldu — doğrudan DB'den doğrulandı).

**BLOKE (kullanıcı eylemi gerekiyor):** Gerçek uygulamayı yeniden
keşfetmek (`discover` job'u, görü tabanlı ajan) ve gerçek/çeşitli
gameplay'i yeniden yakalamak (`capture` job'u) OpenRouter'a gerçek
sohbet/vision API çağrıları gerektiriyor. İki deneme de gerçek `402`
hatasıyla başarısız oldu: `GET /credits` ile doğrudan kontrol edildi —
hesabın `total_credits: 15`, `total_usage: 15.15` — yani gerçek bakiye
tükenmiş. Bu geçici bir "in-flight" hatası değil, gerçek bir kredi
sınırı. **Kullanıcının OpenRouter hesabına gerçek bakiye eklemesi
gerekiyor** (https://openrouter.ai/settings/credits) — bu, doğrudan bir
para işlemi olduğu için otomatik yapılmadı, kullanıcıya bırakıldı.

Bakiye eklendikten sonra yapılacaklar (sırayla): 1) `discover` job'unu
gerçek uygulamaya karşı çalıştırıp `game_profiles`'ı gerçek, çeşitli
oyun modu bilgisiyle güncellemek, 2) 3 gameplay sahnesini gerçek/farklı
oyun modlarından yeniden yakalamak, 3) AI sahnelerinin grounding
referanslarını bu yeni çeşitli çekimlerden yeniden üretmek, 4) timeline/
QA/export'u yeniden çalıştırıp yeni örnek videoyu kullanıcıya
göndermek.

## BLOKE ÇÖZÜLDÜ: gerçek uygulamayla tam düzeltme canlı doğrulandı (2026-09-11, onüçüncü tur)

Kullanıcı OpenRouter hesabına gerçek bakiye ekledi (`GET /credits`:
`total_credits: 25`, `total_usage: 15.15`). Devam edildi:

- `discover` job'u iki kez daha "Android home screen" gerekçesiyle
  `request_takeover` verdi — gerçek kök neden bulundu: `adb.launch_app`
  sonrası sabit `time.sleep(2)` gerçek, ağır (65MB) bir uygulamanın soğuk
  başlangıcı için yetersizdi; görü ajanının ilk gözlemi hâlâ launcher'ı
  görüyordu. **Düzeltme:** `app/device/adb.py`'ye `foreground_package`/
  `wait_for_foreground` eklendi (`dumpsys window`'un `mCurrentFocus`
  satırını parse ediyor, hedef paket foreground olana kadar bekliyor,
  bounded timeout ile) — hem `discovery.py` hem `capture.py`'de sabit
  sleep'in ÖNÜNE eklendi. Mock testler eklendi (`tests/unit/test_adb.py`).
- `discover` job'u yine de GameProfile'ı gerçek çeşitli oyun modlarıyla
  güncelleyemedi (görü ajanı yavaş/dikkatli oynuyor, bütçe içinde tek bir
  "Pattern Memory" alıştırmasından öteye geçemedi) — ama bu artık kritik
  değil, çünkü asıl kullanılan `device_profiles.package_id` zaten doğru
  pakete işaret ediyor.
- 3 gameplay sahnesi de (`capture_shot` job'u) GERÇEK uygulamaya
  (`com.noriloop.synova` v0.1.1) karşı yeniden yakalandı — hepsi teknik
  QC'yi geçti (3. sahne 2 deneme `blank_or_frozen` ile reddedildi, 3.
  denemede geçti — normal/beklenen bir retry deseni).
  Kareler çıkarılıp görsel doğrulandı: artık gerçek marka renkleri/
  "Pattern Memory" kartı görünüyor.
- 3 AI sahnesi de bu YENİ, doğru referanslarla yeniden üretildi
  (`google/veo-3.1-lite`, gerçek maliyet). Kareler görsel olarak
  incelendi: üçü de artık gerçek "Baseline 1 of 5", "Repeat the pattern",
  "Round 1 of 5" gibi gerçek UI metnini ve gerçek marka renklerini
  doğru şekilde gösteriyor; CTA sahnesi hatta doğru yazılmış "synova"
  kelimesini bile ekledi (önceki anlamsız/bozuk metin yerine).
- Yeni take'ler seçildi, QA yeniden çalıştırıldı (**PASS**, 0 issue),
  yeni final export üretildi: asset `cd5a8f69-efb6-4d30-ac06-12b7033ef342`,
  `exports/v001/export-2b9ec7d5.mp4`, 10.35MB, 20.1sn, teknik QC pass.
  Kullanıcıya gönderildi.

**Hâlâ kapsam dışı/henüz tam çözülmedi:** Gerçek uygulamanın 5 farklı
oyun kategorisi (Memory/Attention/Logic/Speed/Math) var, ama bu turda
yakalanan gerçek gameplay hâlâ yalnızca "Pattern Memory" (Memory
kategorisi) — çünkü uygulamanın kendi ilerleme/baseline akışı yavaş ve
görü ajanı temkinli oynuyor. Bu, "sekiz farklı oyun" talebini tam
karşılamıyor ama kullanıcının asıl kritik itirazını ("bu görüntüler
benim değil" — yanlış/markasız uygulama) çözüyor. Gerçek çeşitlilik
için ileride ayrı, daha uzun bütçeli bir keşif/yakalama turu (veya
baseline akışını atlayıp doğrudan bir oyun moduna gitmeyi öğrenen bir
navigation_json) gerekebilir.

## KRİTİK: reference-image grounding yalnızca ilk kareyi çapalıyor, klibin geri kalanı hâlâ halüsinasyon üretiyor (2026-09-11, ondördüncü tur)

Kullanıcı gerçek-uygulama düzeltmesinden sonra gönderilen videoyu da
"videoda kullandığı görseller Synova'ya ait değil" diye reddetti. Bu
sefer videonun TAMAMI (kaynak take'lerden tek kare değil, gerçek
export'un 1fps ile çıkarılmış TÜM kareleri) tek tek incelendi ve kesin
kanıt bulundu:

- Hook sahnesinin (0-4sn) yalnızca ilk ~1 saniyesi gerçek: uygulamanın
  gerçek açılış/yükleme logosu (pembe-turkuaz-sarı "S" ikonu — bu
  GERÇEK, canlı ADB screencap ile ayrıca doğrulandı, ham yakalama
  dosyasının aynı karesinde de var).
- Ondan sonraki ~3 saniye TAMAMEN halüsinasyon: bir kelime bulmaca
  oyunu (turuncu harfler), neon üçgen eşleştirme oyunu (mor), ve
  emoji/karikatür eşleştirme oyunu (yeşil) — üçü de ekranı bölerek iç
  içe geçmiş halde. Bunların hiçbiri gerçek Synova'da yok; modelin
  "sekiz farklı oyun" konseptini betimlemeye çalışırken TEK referans
  kareden ötesini uydurmasının sonucu.
- Montaj ve CTA sahneleri incelenen karelerde büyük ölçüde doğru/gerçek
  göründü (gerçek "synova" yazısı, gerçek UI metni), yalnızca Hook
  sahnesinde bu şiddette bir kayma var — muhtemelen Hook'un prompt'unun
  açıkça "sekiz farklı oyun" çeşitliliğini betimlemeyi istemesi
  (`purpose: "Hook and establish product with colorful game variety
  theme"`), oysa grounding yalnızca TEK bir gerçek ekran görüntüsü
  sağlıyor — model geri kalanını uydurmak zorunda kalıyor.

**Kök neden (netleşti):** `frame_type: "first_frame"` yalnızca klibin
AÇILIŞ karesini gerçek referansa yakın tutuyor; OpenRouter/Veo'nun
`reference_image_paths`/`frame_images` özelliği klip boyunca sürekli
bir "bu gerçek ekranı göster" kısıtı UYGULAMIYOR. Bu, önceki turlarda
tek bir orta kareye bakarak yaptığım doğrulamanın (frame index 15/37)
şans eseri iyi bir ana denk gelip bu kaymayı kaçırmasına neden oldu —
bir dahaki sefere bir AI klibin kalitesini doğrularken KLİBİN TAMAMINI
(birden fazla kare, ideal olarak `fps=1` ile tüm süre) incelemek
gerekiyor, tek bir orta kare yeterli değil.

**DÜZELTİLDİ VE CANLI DOĞRULANDI (aynı gün, devam eden tur).** Kök
neden netleşti: bu 3 sahnenin `generation_prompt`'ları (bu oturumun çok
daha erken bir aşamasında, grounding hiç yokken director agent
tarafından yazılmıştı) AÇIKÇA "4 farklı oyun", "8 farklı oyun sahnesi",
"eight colorful mini-game icons" gibi ifadelerle sahte çeşitlilik
istiyordu — Veo modeli tam olarak istenen şeyi yapıp bunu uydurdu,
referans görüntü yalnızca zayıf bir öneri, metin prompt'u kadar
belirleyici değil. Üç prompt de gerçek referans ekranına ("Repeat the
pattern" / "Round 1 of 5" grid) sadık kalacak ve "no scene changes, no
other apps, no different game types" gibi açık kısıtlar içerecek
şekilde yeniden yazıldı (DB'de `shots.generation_prompt` doğrudan
güncellendi). 3 sahne yeniden üretildi ve bu sefer HER KLİBİN TÜM
kareleri (2fps, uçtan uca) tek tek incelendi — hepsi artık klip boyunca
tutarlı şekilde gerçek ekranı gösteriyor. Yeni final export de aynı
şekilde tam kare taramasıyla doğrulandı: asset
`6206ab6a-193d-47c0-9fc9-75d7a074aa26`,
`exports/v001/export-f5b5b589.mp4`, sha256 `580113f2...`, QC pass, QA
pass. Kullanıcıya gönderildi.

**Ders:** Bir AI klibinin gerçek referansa sadık kaldığını doğrulamak
için TEK bir orta kareye bakmak yeterli değil — klip metin prompt'unun
kendisi "farklı sahneler/çeşitlilik" istiyorsa (özellikle grounding
eklenmeden önce yazılmış eski prompt'larda), model referans görüntüyü
yalnızca gevşek bir öneri olarak kullanıp geri kalanını prompt'un
kelimelerine göre üretir. Bundan sonra: (1) yeni bir AI sahnesi
üretirken prompt'un "farklı/çeşitli/multiple" gibi kelimeler
içermediğini önceden kontrol et, (2) her üretilen klibi göndermeden
önce TÜM karelerini (fps=1-2, uçtan uca) tek tek incele.

Bu bölüm ilerledikçe güncellenecektir.
