# İlerleme Takibi (PROGRESS.md)

Durumlar: `not-started`, `in-progress`, `implemented` (kod var, testler geçti),
`live-blocked` (kod/test tamam, canlı doğrulama donanım/anahtar eksikliğinden
engelli), `done` (kod + test + canlı doğrulama tamam).

Son güncelleme: 2026-09-11 (koordinatör oturumu — Safha 0-11 canlı
doğrulandı, Safha 12 kısmi/in-progress; ayrıntı bu dosyanın altında).

## Onuncu tur (2026-09-11): gerçek Synova projesi ilk kez uçtan uca tamamlandı, sonra kullanıcı yönetmen incelemesi 2 kök sorun buldu

`_pick_generation_duration_s` düzeltmesi canlı doğrulandı: CTA sahnesi
(hedef 2.5sn) artık gerçekten 4.0sn olarak Veo'ya istendi ve üretim
başarılı oldu (job d1a70392, gerçek maliyet $0.32). Ardından eksik 3.
gameplay sahnesi gerçek emülatörden yeniden yakalandı (ilk deneme
`blank_or_frozen` QC'sinden haklı olarak reddedildi, 2. deneme geçti).
QA çalıştırıldığında brief'in daha önce bu oturumda 750 kareye
düzenlenmiş olması (plan 600 kare üzerine kurulmuştu) yüzünden
`run_revision_qa`'nın `get_latest_brief` kullanması gerçek bir hataya
yol açtı — düzeltme: `session.get(Brief, revision.brief_id)` (bkz.
`app/services/qa.py`, regresyon testi `test_qa_frame_budget_check_uses_the_revision_own_brief_not_the_latest_one`).
Düzeltmeden sonra QA ilk kez gerçekten **PASS** verdi (0 issue), final
export gerçekten üretildi: asset `6f880891-d34d-43e4-a686-d4be834973b5`,
`exports/v001/export-70c5965b.mp4`, 10.79MB, 20.1sn, sha256
`298935b1...bccb4d84` — kullanıcının indirdiği dosyayla (`preview-81ec6287.mp4`)
sha256 birebir aynı, yani gerçekten aynı üretim.

Kullanıcı bu videoyu izleyip "uzman yönetmen gözüyle" değerlendirme
istedi. Ben ffmpeg ile gerçek kareler çıkarıp görsel inceleme yaptım ve
5 sorun buldum (donuk/statik gameplay algısı, CTA'da bozuk/anlamsız
metin, bir deformasyon artefaktı, dil uyuşmazlığı, altyazı rozeti
konumlandırma tutarsızlığı). Kullanıcı bunları doğruladı AMA daha temel
iki kök sorunu BEN gözden kaçırmıştım:

1. **"synova bu değil. görüntüler tamamen uydurma."** — AI ile üretilen
   sahneler gerçek Synova oyununu hiç göstermiyor, jenerik/halüsine
   mobil oyun görüntüsü üretiliyor. Kök neden: `generate_ai_scene_take`
   (`app/services/generation.py`), `VideoGenerationRequest`'i hiçbir
   zaman `reference_image_paths` ile doldurmuyor — oysa bu alan
   provider katmanında (`app/providers/base.py`, `app/providers/openrouter.py`)
   zaten var ve `google/veo-3.1-lite` modeli canlı katalogda
   `supports_reference_images: true` döndürüyor. Yani üretim hiçbir
   zaman gerçek oyun görüntüsüne "grounded" olmadan tamamen metin
   promptundan (halüsinasyona açık) çalıştırılıyordu. **Bu bir uygulama
   hatası** — spec'in reference-image desteğini varsayan tasarımı hiç
   uygulanmamıştı.
2. **"ses çok robotik."** — ElevenLabs TTS sesi kullanıcıya robotik
   geliyor; hangi `voice_id`/model ayarlarının kullanıldığı ve
   `stability`/`similarity_boost`/`style` gibi ayarlanabilir
   parametrelerin hiç geçilmediği araştırılacak.

Kullanıcının talimatı: bulgulara göre gerçek uygulama kodu revize
edilecek ve gerçek (ücretli API'lerle) bir örnek video yeniden
üretilecek.

## Reference-image grounding + robotik ses düzeltmesi CANLI DOĞRULANDI (2026-09-11, onbirinci tur)

Her iki kök neden düzeltildi ve gerçek API çağrılarıyla doğrulandı:

**1. AI sahneleri artık gerçek Synova görüntüsüne "grounded":**
`app/services/generation.py`'ye `_find_real_gameplay_reference_image`
eklendi — projedeki en son gerçek `emulator_capture` gameplay
videosundan `technical_qc.sample_frames_png` ile bir kare örnekleyip
base64 `data:image/png;base64,...` URI'a çevirip
`VideoGenerationRequest.reference_image_paths`'e geçiriyor. Bunu ilk
canlı denemede `app/providers/openrouter.py`'nin `frame_images` gövde
şeması da hiç gerçek API'ye karşı sınanmamıştı ve YANLIŞTI — gerçek
`POST /videos` isteği art arda 2 farklı `400 ZodError` döndürdü:

1. `{"frame_type": "first_frame", "image_url": path}` → hata:
   `frame_images[0].type` `"image_url"` bekliyor,
   `frame_images[0].image_url` string değil obje olmalı.
2. `{"type": "image_url", "image_url": {"url": path}}` → hata:
   `frame_images[0].frame_type` eksik, `"first_frame"|"last_frame"`
   bekleniyor.

Gerçek/doğru şema: `{"type": "image_url", "image_url": {"url": ...},
"frame_type": "first_frame"}` — ikisi birden gerekiyor. Düzeltmeden
sonra 3. denemede 3 sahne de (Hook, montaj, CTA) gerçekten
`google/veo-3.1-lite` ile yeniden üretildi (gerçek harcama), hepsi
`metadata_json.provider.grounded_in_real_gameplay: true` ile işaretli,
teknik QC hepsinde `pass`. Kareler çıkarılıp görsel olarak incelendi:
artık gerçek Synova'nın "Repeat the pattern" hafıza oyunu ızgarası
(yeşil seçili hücreler, "Round 1 of 5" / "2 of 4 selected" gibi gerçek
UI metni) görünüyor — önceki tamamen jenerik/uydurma mobil oyun
görüntüsünden büyük bir iyileşme. (Not: CTA sahnesindeki bozuk/anlamsız
metin sorunu grounding'den bağımsız, hâlâ mevcut — bkz.
KNOWN_LIMITATIONS.md.)

**2. Ses artık tuned `voice_settings` ile üretiliyor:**
`ElevenLabsProvider.synthesize()` artık her zaman `voice_settings`
gönderiyor (`stability=0.4, similarity_boost=0.8, style=0.25,
use_speaker_boost=true` varsayılan olarak, çağıran override edebilir).
3 seslendirme gerçekten yeniden üretildi, hem tuned ayarlarla hem de
daha enerjik bir sesle ("Jessica - Playful, Bright, Warm",
`cgSgspJ2msm6clMCkdW9`) — önceki "Sarah - Mature, Reassuring,
Confident" yerine.

**Yeni tam export:** asset `d7202bae-893a-44f1-a0d8-4cedd6d5e67a`,
`exports/v001/export-94f2c181.mp4`, 8.76MB, 20.1sn, teknik QC pass, QA
pass (0 issue). Kullanıcıya `SendUserFile` ile gönderildi.

Birim testleri: `test_generate_ai_scene_take_grounds_the_request_in_a_real_gameplay_capture`,
`test_generate_ai_scene_take_has_no_reference_image_when_no_gameplay_capture_exists`,
`test_submit_sends_frame_images_in_the_real_documented_content_part_shape`,
`test_synthesize_posts_text_and_returns_audio_bytes_with_default_voice_settings`,
`test_synthesize_uses_caller_supplied_voice_settings_when_given`.

`pytest -q`: **259 passed, 11 deselected**.

**Henüz düzeltilmedi (kapsam dışı bırakıldı, ayrıntı KNOWN_LIMITATIONS.md):**
CTA'daki bozuk/anlamsız uygulama metni, ardışık gameplay çekimlerinin
donuk görünmesi (tek-tek QC her birini geçiyor), altyazı rozeti
konumlandırma tutarsızlığı.

## KRİTİK bulgu: proje baştan yanlış build'e karşı çalışmış (2026-09-11, onikinci tur)

Kullanıcı düzeltilmiş videoyu da "bu görüntüler de benim değil" diye
reddetti. Kök neden bulundu: emülatörde şimdiye kadar kurulu olan
`com.example.synova.dev` (v0.1.0) markasız/jenerik bir dev build'miş;
gerçek `.aab` (`SYNOVA-0.1.1-2.aab`, gerçek paket `com.noriloop.synova`,
v0.1.1) hiç kurulmamıştı. Bu, EN BAŞTAN İTİBAREN tüm gameplay
yakalamalarının ve bunlardan türeyen AI grounding referanslarının
yanlış/eksik içerik gösterdiği anlamına geliyor — gerçek uygulamanın
5 farklı oyun kategorisi (Memory/Attention/Logic/Speed/Math) var,
oysa proje boyunca hep aynı tek "Pattern Memory" ekranı yakalanmış.

Düzeltilen (ücretsiz) kısım: gerçek `.aab` `bundletool` ile gerçek APK'ya
çevrildi, emülatöre kuruldu ve canlı doğrulandı (gerçek "SYNOVA" splash
ekranı); `device_profiles.package_id` veritabanında doğru pakete
güncellendi.

**BLOKE (çözüldü):** Kullanıcı gerçek bakiye ekledi
(`total_credits: 25`). Devamında `discover` job'u iki kez daha
`request_takeover` verdi — gerçek kök neden bulundu: `adb.launch_app`
sonrası sabit 2sn bekleme, gerçek (65MB) uygulamanın soğuk başlangıcı
için yetersizdi. Düzeltme: `app/device/adb.py::wait_for_foreground`
eklendi (mCurrentFocus'u pollar, bounded timeout), `discovery.py` ve
`capture.py`'de kullanılıyor; mock testler eklendi
(`tests/unit/test_adb.py`).

3 gameplay sahnesi GERÇEK uygulamaya (`com.noriloop.synova` v0.1.1)
karşı yeniden yakalandı (hepsi teknik QC pass), 3 AI sahnesi bu doğru
referanslarla yeniden üretildi — kareler görsel doğrulandı: artık
gerçek marka renkleri, gerçek "Baseline 1 of 5"/"Repeat the pattern" UI
metni ve hatta doğru yazılmış "synova" kelimesi görünüyor. Yeni final
export üretildi (asset `cd5a8f69-...`, 10.35MB, QA PASS) ve kullanıcıya
gönderildi.

`pytest -q`: **264 passed, 11 deselected**.

Kalan sınırlama: gerçek uygulamanın 5 oyun kategorisi var
(Memory/Attention/Logic/Speed/Math) ama bu turda yakalanan içerik hâlâ
yalnızca Memory kategorisi (görü ajanı yavaş oynuyor, baseline akışını
bütçe içinde tamamlayamadı) — "sekiz farklı oyun" çeşitliliği tam
sağlanmadı, ama kullanıcının asıl kritik itirazı (yanlış/markasız
uygulama) çözüldü. Ayrıntı KNOWN_LIMITATIONS.md.

## Onbeşinci tur: AI klipler ortadan sapıp halüsinasyona dönüyordu — kök neden prompt'lardaydı, düzeltildi

Kullanıcı yeniden reddetti ("videoda kullandığı görseller Synova'ya
ait değil"). Bu sefer export'un TEK bir orta karesi değil, TÜM kareleri
(2fps, uçtan uca) tek tek incelendi: Hook sahnesinin ilk ~1sn'si
gerçek (gerçek açılış logosu) ama sonraki ~3sn tamamen halüsinasyon —
3 sahte oyun (kelime bulmaca, neon üçgen, emoji eşleştirme) iç içe.

Kök neden: bu 3 sahnenin `generation_prompt`'ları grounding hiç yokken
yazılmıştı ve AÇIKÇA "4 farklı oyun", "8 farklı oyun sahnesi" gibi
sahte çeşitlilik istiyordu — model tam olarak istenen şeyi yaptı,
referans görüntü yalnızca zayıf bir öneriydi. Üç prompt da tek gerçek
ekrana sadık kalacak ve "no scene changes/other apps/different game
types" kısıtları içerecek şekilde yeniden yazıldı, 3 sahne yeniden
üretildi. Bu sefer HER klibin TÜM kareleri incelendi (yalnızca orta
kare değil) — hepsi artık tutarlı. Yeni final export: asset
`6206ab6a-...`, sha256 `580113f2...`, QC/QA pass. Kullanıcıya
gönderildi.

Ders (KNOWN_LIMITATIONS.md'ye de yazıldı): AI klip doğrulaması artık
her zaman TÜM karelerle yapılacak, tek orta kareye güvenilmeyecek.

## Safha durumu

| Safha | Konu | Durum | Not |
|---|---|---|---|
| 0 | Depo, ortam, kararlar | in-progress | İskelet kuruldu, bu commit ile |
| 1 | Kalıcı proje ve temel arayüz | done (bu round için) | Tam yığın CANLI doğrulandı: gerçek backend + gerçek derlenmiş UI, tarayıcıda proje oluşturma → brief kaydetme → klasör açma uçtan uca çalıştı. Entegrasyon sırasında bulunan 5 hata aynı oturumda düzeltildi, bkz. TEST_REPORT.md |
| 2 | İş motoru, olaylar, bütçe | implemented | Job queue + SSE + bütçe defteri kodlandı ve test edildi (110→116 testin parçası); main.py'a bağlandı, canlı proje/job akışı çalıştı. **Bütçe UI'ı eklendi (2026-09-11, sekizinci tur):** `budget_service.get_budget_summary` bu ana kadar (gerçek video/LLM maliyet kayıtları biriktiği hâlde) hiçbir uç noktadan okunamıyordu — `GET /projects/{id}/budget` eklendi, Stüdyo başlığına her zaman görünen bir "Bütçe: $harcanan / $tavan" göstergesi eklendi (15sn'de bir kendiliğinden yenileniyor). Gerçek Synova projesinde CANLI doğrulandı: `$0.325957 / $5.00` — bu oturum boyunca gerçekten settle edilmiş Veo video ($0.32) + LLM review ($0.005957) maliyetlerinin doğru toplamı. |
| 3 | Sağlayıcılar ve model keşfi | implemented (canlı katalog dahil) | GET /providers/models CANLI: 437 model (OpenRouter), video kataloğu 29 model. generate_structured/video submit-poll-download/ElevenLabs mock (key yok, provider_live marker ile ayrı). 67/67 test geçti |
| 4 | Emülatör köprüsü, eşzamanlı kayıt | done | synova_test AVD üzerinde CANLI doğrulandı: ADB keşif/screenshot/tap/swipe, normalize koordinat + stale-observation reddi, scrcpy ile 17.7sn gerçek kayıt (3 eylem sırasında, H264+opus, ffprobe ile doğrulandı), /devices preflight API'si (screenshot+touch+kayıt+ses testi) — 9/9 device_live pytest geçti |
| 5 | Görsel operatör, gerçek çekim | in-progress | Sınırlı oyun KEŞFİ CANLI doğrulandı: gerçek Synova uygulamasında, gerçek ekran görüntüleriyle karar veren LLM operatör, 6 eylem sınırıyla gerçekten oynadı ve doğru bir GameProfile üretti ("4x4 grid'de sıra ezberleme oyunu", güven 0.72 — gerçek gözleme dayalı, uydurulmamış). Ayrı bir denemede gerçek bir sistem ANR diyaloğunu doğru tanıyıp `request_takeover` ile durdu (spec 11.8, gizli otomatik onay yok). Gerçek çekim (shot capture, olay tespiti) henüz yok — bu sadece keşif |
| 6 | Yönetmen, senaryo, animatic | in-progress | ConceptSet + ShotPlan (Script dahil) üretimi CANLI doğrulandı: seçili fikirden 600 kareye tam oturan 6 sahnelik gerçek bir plan üretildi (3 AI sahne + 3 gerçek oynanış sahnesi), Revision+Shot olarak DB'ye kaydedildi, tarayıcıda görüntülendi. Model, kare toplamını ilk denemede tutturamayınca spec §10.4'teki tek düzeltme denemesi devreye girdi ve ikinci denemede başarılı oldu — gerçek kanıt. Animatic (sesli/zamanlı önizleme) henüz yok |
| 7 | Çekim arşivi, retake | in-progress | Gerçek oynanış çekimi CANLI doğrulandı: Safha 6'da üretilen gerçek ShotPlan'ın "gameplay" sahneleri için, görsel operatör döngüsü (Safha 5) artık gerçek scrcpy kaydı altında çalışıyor. Stüdyo'ya gerçek bir "Çekim" adımı eklendi (cihaz seçimi, sahne başına "Çek"/"Yeniden çek", take listesi + video önizleme + "Bu çekimi seç") — tarayıcıda CANLI denendi: buton tıklaması gerçek bir capture job'u tetikledi, gerçek scrcpy süreci (PID doğrulandı) kaydetti, iş bitince take listesi otomatik yenilendi, "Bu çekimi seç" gerçek `shots.selected_take_id`'yi DB'de güncelledi. Retake sayacı (attempt) ve kontrol-devrinde kısmi kaydı silmeden reddedilmiş Take olarak saklama da doğrulandı. Henüz yok: otomatik olay tespitiyle in/out kırpma |
| 8 | İnsanlı AI sahneler, ses | in-progress | AI sahne üretimi (video) ve seslendirme (TTS) CANLI doğrulandı, gerçek paralı API çağrılarıyla: `google/veo-3.1-lite` ile gerçek 4.01sn h264+aac MP4 üretildi (ffprobe ile bağımsız doğrulandı, teknik QC 4/4 geçti), aynı sahne için yönetmenin gerçek bir video-üretim prompt'u yazdığı ve `Shot.generation_prompt`'a kaydedildiği doğrulandı. ElevenLabs ile aynı sahnenin gerçek Türkçe seslendirme metninden gerçek 4.46sn MP3 üretildi. Stüdyo'ya gerçek bir "Taslak" ekranı eklendi (her AI sahnesi için üret/yeniden üret + önizleme, her seslendirme için gerçek ses listesinden seçim + üret, tarayıcıda CANLI denendi — bir sahne gerçekten üretildi, "Yeniden üret" durumuna geçti). **Gerçek bir hata bulundu ve düzeltildi (2026-09-11, dokuzuncu tur):** `generate_ai_scene_take` sahnenin tam süresini (ör. CTA'nın 2.5sn'si) doğrudan Veo'dan istiyordu; model yalnızca [4,6,8]sn destekliyor, bu yüzden CTA gibi sahneler HER ZAMAN `validate_request` hatasıyla başarısız oluyordu — hatanın kendi mesajı bile ("planner must render the nearest supported duration and trim the used span") aslında yapılması gerekeni tarif ediyordu ama kod bunu hiç uygulamıyordu. `_pick_generation_duration_s` eklendi: modelin katalogundan (`video_provider.list_models()`) gerçek desteklenen süreleri okuyup hedefe eşit veya ondan büyük en yakın süreyi seçiyor; Remotion tarafı zaten her video öğesini `Sequence durationInFrames` ile sahnenin gerçek süresine kırpıyor (`apps/render/src/compositions/AdComposition.tsx`), yani fazladan bir "trim" adımına gerek yok — talep edilen video daha uzun gelse bile render otomatik olarak doğru süreye kesiyor. Henüz yok: lipsync (LipSyncProvider hâlâ arayüz düzeyinde) |
| 9 | Timeline ve final render | in-progress | Gerçek asset boru hattı CANLI doğrulandı (FR-15 devamı): `POST /projects/{id}/timeline/build` gerçek Revision+Shot'lardan gerçek bir Timeline JSON üretip `Revision.timeline_json`'a yazıyor (var olan Take/voice Asset'leri referanslıyor, henüz çekilmemiş sahneler için `asset_id: null` — uydurma yok). `POST /projects/{id}/render/preview`, bu timeline'ı gerçek dosyaları `apps/render/public/`'a kopyalayıp gerçek bir `remotion render` çalıştırarak 20.05sn/1080x1920 gerçek bir kompozit MP4'e dönüştürdü: aynı videoda hem gerçek Google Veo AI sahnesi, hem gerçek Synova oynanış kaydı, hem de çekilmemiş bir sahne için dürüst PLACEHOLDER art arda göründü (üç kare bağımsız olarak çıkarılıp görsel olarak doğrulandı). Taslak ekranına "Timeline oluştur" + "Önizleme render et" eklendi ve tarayıcıda CANLI denendi — gerçek 8.3MB/20sn bir önizleme videosu üretilip oynatıcıda göründü. Gerçek altyazı metni render de CANLI doğrulandı: `timeline.py` artık `transform.captionText` taşıyor, `AdComposition` bunu ekrana basıyor — gerçek Synova projesi yeniden render edilip bir kare çıkarılarak Türkçe altyazının AI sahnesi üzerinde doğru göründüğü görsel olarak doğrulandı. **Ses seviyesi normalizasyonu eklendi (2026-09-11, dokuzuncu tur):** spec §16.4'ün ürün miks varsayılanı (-16 LUFS integrated, -1 dBTP true peak) — `app/media/audio.py::normalize_loudness`, ffmpeg'in iki geçişli `loudnorm` filtresiyle (EBU R128) her render'ın gerçek ses seviyesini ölçüp hedefe doğru düzeltiyor; ölçülemeyen/sessize yakın içerikte (ffmpeg'in kendi `-inf` LUFS eşiği) dosyayı olduğu gibi bırakıyor, render'ı asla başarısız etmiyor. `render_timeline_to_asset`'e bağlandı, ölçüm `Asset.audio_info_json`'a kaydediliyor. **Geliştirirken gerçek bir hata bulundu ve düzeltildi:** `-c:v copy` bayrağı, video akışı olmayan girdilerde (ör. tek başına bir ElevenLabs ses dosyası) ffmpeg'i "Invalid argument" ile başarısız ediyordu — artık girdide gerçekten video akışı varsa ekleniyor. Gerçek kanıt: (1) gerçek bir ElevenLabs seslendirme örneğiyle entegrasyon testi — ölçüm gerçek bir LUFS değeri verdi, normalize edilmiş çıktı yeniden ölçüldüğünde hedefe (-16 LUFS, ±1.5 tolerans) yaklaştığı doğrulandı; (2) gerçek, sessize yakın bir scrcpy kaydıyla — fonksiyonun dosyayı olduğu gibi bıraktığı doğrulandı; (3) gerçek Synova projesinde tam bir önizleme render'ı tetiklendi, sonuçtaki Asset'in `audio_info_json`'ı gerçek ölçümü taşıyordu (`measured_integrated_lufs: -17.15` → hedef `-16.0`). Henüz yok: editör arayüzü (kırpma/bölme/fade), crop (§16.3), cache (§16.5) |
| 10 | Revizyon, kilit, varyasyon | in-progress | `POST /projects/{id}/revisions/{revision_id}/variation` CANLI doğrulandı: gerçek Synova projesinde tek bir sahneye ("CTA'yı daha aciliyetli yap, sınırlı süreli ücretsiz deneme vurgusu ekle") gerçek bir talimat verildi; yönetmen o sahneyi (`target_frames` sabit kalarak) gerçekten yeniden yazdı (yeni caption/voice_text talimatı doğru yansıttı), diğer 5 sahne değişmeden yeni revizyona taşındı. **Bu canlı test sırasında gerçek bir hata bulundu ve düzeltildi:** taşıma mantığı yalnızca `shots.selected_take_id` açıkça set edilmişse (yani biri "Bu çekimi seç" demişse) take'i taşıyordu; hiç seçilmemiş ama var olan bir take (ör. bir AI sahnesi, hiç "seç" düğmesi olmayan bir tür) sessizce kayboluyordu. Artık `timeline.selected_or_best_take` ile aynı "seçili veya en iyi uygun" mantığı kullanılıyor — gerçek Synova projesinde AI Hook sahnesinin video'sunun kaybolmadığı yeni bir testle doğrulandı. Görsel kilitli bir sahneye talimat verilirse istek sessizce yok sayılmıyor, açık 422 ile reddediliyor. **İkinci bir gerçek hata daha bulundu ve düzeltildi (2026-09-11, altıncı tur):** seslendirme (voice-over) Asset'leri hangi sahneye ait olduklarını `metadata_json.shot_id` ile tutuyor (Take'lerin aksine ayrı bir bağlantı tablosu yok); taşınan (carry-forward) bir sahne her zaman yeni bir Shot id'si aldığı için, o sahnenin zaten üretilmiş/ödenmiş seslendirmesi bir varyasyondan sonra sessizce kayboluyordu (Taslak ekranında "Seslendirme üret" olarak görünüp gereksiz yeniden ödeme riski doğuruyordu). `_carry_forward_voice_asset` eklendi — taşınan her sahne için varsa mevcut seslendirme Asset'inin `shot_id`'si yeni sahneye güncelleniyor. Gerçek Synova projesinde CANLI doğrulandı: montaj sahnesine gerçek bir talimat verilip yeni bir revizyon oluşturuldu; Hook ve CTA'nın gerçek ElevenLabs seslendirmeleri yeni sahne id'lerine doğru taşındığı hem Asset tablosundan hem yeniden inşa edilen timeline'ın `hasVoiceOver` alanından doğrulandı (değişen montaj sahnesi için ise beklendiği gibi `False` — o sahnenin metni değiştiği için eski ses artık geçerli değil). Aynı taşıma, talimatla revize edilen ama sesi kilitli (`locks.voice`) bir sahne için de eklendi (voice_text bit bit aynı kaldığından eski ses hâlâ geçerli). **Kilit açma/kapama + varyasyon UI'ı eklendi (2026-09-11, yedinci tur):** bu revizyon motoru bu ana kadar hiçbir arayüzden erişilemiyordu, yalnızca doğrudan API çağrılarıyla test edilmişti. `PATCH /projects/{id}/shots/{shot_id}/locks` eklendi (`select_take`'in `selected_take_id`'yi yerinde güncellemesiyle aynı desen — yeni bir revizyon açmaz), Senaryo ekranındaki her sahne kartına 4 kilit onay kutusu (görsel/ses/yazı/süre) ve bir talimat kutusu + "Varyasyon oluştur" düğmesi eklendi. Gerçek Synova projesinde CANLI doğrulandı: Hook sahnesinin ses kilidi gerçekten açıldı (`PATCH .../locks`), sonra aynı sahneye gerçek bir görsel-değişikliği talimatı verildi — yeni revizyonda sesin (daha önce yalnızca birim testiyle doğrulanmış olan bu ikinci taşıma yolu) gerçekten korunduğu doğrulandı. **Bu canlı test sırasında üçüncü, altyapısal bir hata daha bulundu ve düzeltildi:** aynı varyasyon isteği ilk denemede gerçek bir HTTP 500 döndü, hiçbir kod değişikliği olmadan anında tekrar denendiğinde başarılı oldu — SQLite'ın varsayılan `busy_timeout=0` olması, arka plan job worker'ı (veya frontend'in sürekli `GET /jobs` yoklaması) ile çok satırlı bir yazma işlemi çakıştığında yazıcının beklemek yerine anında "database is locked" ile başarısız olmasına yol açıyordu. `app/core/db.py`'e `PRAGMA busy_timeout=5000` eklendi. Gerçek backend'e karşı 8 thread'le sürekli `GET /jobs` yokluğu yapılırken CANLI yazma testleri ve — daha güçlü bir kanıt olarak — 24 eşzamanlı gerçek `PATCH .../locks` isteği (gerçek yazıcı-yazıcı çakışması) hepsi 200 ile tamamlandı. **Revizyon geçmişi eklendi (2026-09-11, yedinci tur devamı):** `GET /projects/{id}/revisions` (yeni, salt-okunur, `plans_service.list_revisions`) ve Senaryo ekranında bir "Revizyon geçmişi" listesi — her revizyonun sıra no'su, sahne sayısı, değişiklik özeti ve zaman damgası, güncel olan işaretli. Gerçek Synova projesinde CANLI doğrulandı: bu oturum boyunca gerçekten oluşan 4 revizyonun tamamı (doğru üst-alt zincirleriyle) döndü. Bu, tam "önceki sürümle karşılaştırma" değil (yan yana diff/geri alma yok) — yalnızca hangi varyasyonun ne zaman/ne değiştirdiğini görme. **Dördüncü, daha derin bir gerçek hata bulundu ve düzeltildi (2026-09-11, yedinci tur devamı):** revizyon geçmişi eklenince fark edildi ki revizyonlar aslında düz bir zincir değil, dallanan bir ağaç — aynı `parent_id`'den birden fazla varyasyon (kardeş revizyon) türeyebiliyor (revizyon geçmişi ekranı bunu tam olarak gösteriyor). `_carry_forward_voice_asset`'in önceki hâli mevcut Asset satırını YERİNDE güncelliyordu; aynı temel sahneden türeyen iki kardeş varyasyon oluşturulduğunda, hangisi önce çalışırsa seslendirmeyi "çalıyor", diğer kardeş sessizce sessiz kalıyordu — gerçek Synova projesinde tam olarak bu şekilde oluştu (bu oturumun kendi test varyasyonları birbirinin kardeşiydi). Düzeltme: artık mevcut Asset satırı hiç değiştirilmiyor, bunun yerine aynı dosyaya (`relative_path`/`sha256` paylaşılır — Take'lerin zaten aynı `asset_id`'yi paylaşan birden fazla satırla yaptığı gibi) işaret eden YENİ bir Asset satırı klonlanıp yeni sahneye bağlanıyor. Gerçek Synova projesinde CANLI doğrulandı: aynı temel revizyondan iki kardeş varyasyon oluşturuldu, ikisi de kendi Hook/CTA sahnelerinde gerçek seslendirmeyi bağımsız olarak koruduğu doğrulandı — bu düzeltme aynı zamanda projenin önceki turdaki hatadan dolayı sessizlik kalmış güncel revizyonunu da onardı (Hook/CTA artık `hasVoiceOver: true`). **Altyazı düzeltme eklendi (2026-09-11, sekizinci tur):** spec §5.3'ün editör zorunlu işlemlerinden biri — `PATCH /projects/{id}/shots/{shot_id}/caption` (yerinde günceller, yeni revizyon açmaz, LLM çağrısı yok/ücretsiz), Senaryo ekranındaki her sahne kartına düzenlenebilir bir "Ekran yazısı" alanı + "Kaydet" düğmesi eklendi. Gerçek Synova projesinde CANLI doğrulandı: Hook sahnesinin yazısı gerçekten değiştirildi, `POST .../timeline/build` yeniden çağrıldığında yeni metnin altyazı kanalına doğru yansıdığı görüldü (sonra orijinal metin geri yüklendi). **Klip taşıma (sahne sıralama) eklendi (2026-09-11, sekizinci tur devamı):** spec §5.3'ün bir diğer zorunlu işlemi — `PUT /projects/{id}/revisions/{revision_id}/order` (`shot_order`'ın revizyonun tüm sahnelerinin bir permütasyonu olduğunu doğrular, yerinde `order_index` günceller, yeni revizyon açmaz/LLM çağrısı yok), Senaryo ekranındaki her sahne kartına ▲/▼ taşıma düğmeleri eklendi. Gerçek Synova projesinde CANLI doğrulandı: iki oynanış sahnesi yer değiştirildi, `POST .../timeline/build` yeniden çağrıldığında `start_frame` sırasının doğru yansıdığı görüldü, sonra orijinal sıra geri yüklendi. Henüz yok: revizyonlar arası görsel diff, eski bir revizyona geri dönme/onu aktif yapma, kırpma/bölme/fade/metin-logo konumlandırma |
| 11 | QA, yerleşim, teslim | in-progress | `GET /projects/{id}/revisions/{revision_id}/qa` ve `POST .../export` CANLI doğrulandı. QA gerçek Synova revizyonuna karşı çalıştırıldığında dürüstçe FAILED döndü (kalan eksik sahneleri tek tek listeledi). Ayrı, minimal gerçek bir projede: bir `ai_generated` sahne gerçek Veo videosuyla üretildi → QA gerçekten PASSED döndü → export job'u gerçek bir `remotion render` çalıştırıp `exports/v001/` altına 4.05sn/1080x1920 gerçek bir export MP4 yazdı (teknik QC 4/4, ffprobe ile bağımsız doğrulandı). QA, `synthetic_test` kökenli asset'leri ve başarısız/belirsiz teknik QC'yi de doğru şekilde reddediyor (mock testlerle). Stüdyo'ya gerçek bir "Çıktı" ekranı eklendi (QA raporu + dışa aktar düğmesi, QA geçmeden devre dışı) — tarayıcıda CANLI denendi: gerçek eksik sahneler doğru listelendi, "Dışa aktar" düğmesi doğru şekilde devre dışı görünüyordu. İçerik/marka güvenliği reviewer'ı da eklendi ve CANLI doğrulandı: `POST /projects/{id}/shots/{shot_id}/review` gerçek bir gameplay klibinden 4 kare örnekleyip gerçek bir vision LLM çağrısıyla değerlendirdi — model "0 of 4 selected" → "2 of 4" gibi somut, gerçekten ekrandan okunan ayrıntılarla `pass` verdisi verdi, sonuç `qa_reports` tablosuna kalıcı yazıldı ve `run_revision_qa` bunu otomatik hesaba kattı (inceleme isteğe bağlı — hiç çalıştırılmamış bir take QA'yı bloklamıyor). İnceleme için UI düğmesi de eklendi: `GET .../shots/{shot_id}/review` uç noktası + Taslak ekranında her AI sahnesine "İçerik incele (AI)" düğmesi, geçti/reddedildi/belirsiz rozeti ve gerekçe/kusur listesi — gerçek Synova Hook sahnesinde CANLI doğrulandı (bkz. TEST_REPORT.md). Gerçek LLM maliyet kaydı da genişletildi: `discover`/`capture_shot`/`review_take` artık OpenRouter'ın chat completion yanıtındaki gerçek `usage.cost`'u bir `BudgetEntry` satırına yazıyor (`generate_ai_scene` zaten video maliyetini yazıyordu, artık üzerine sahne prompt'unun metin maliyetini de ekliyor) — gerçek Synova projesinde bir `review_take` job'unun tam olarak `$0.005957`'lik gerçek bir settlement satırı yazdığı DB'den doğrudan okunarak doğrulandı. `generate_voice` (ElevenLabs) hâlâ izlenmiyor — API yanıtı hiçbir maliyet/kullanım alanı taşımıyor. Henüz yok: yerleşime (placement_id) özgü format doğrulaması |
| 12 | Windows paketleme, regresyon | in-progress | `SETUP.bat`/`START.bat`/`STOP.bat` bu gece defalarca gerçekten çalıştırıldı (backend restart, kod değişikliği sonrası yeniden derleme dahil) — kaynak koddan çalışan bir Windows kurulumu gerçekten kanıtlandı. Bu oturumun sonunda tam regresyon çalıştırıldı: `pytest -q` 188/188, `apps/web` build temiz, `apps/render` typecheck temiz, soğuk backend restart + gerçek health/SPA kontrolü başarılı. `GET /health`'in `worker.status` alanı gerçek worker durumunu yansıtmıyordu (her zaman sabit "not_started") — bu gece fark edilip düzeltildi. Henüz yok: bağımsız/tek-tıkla kurulan bir installer (Python/Node önkoşulsuz paketlenmiş .exe), kod imzalama, otomatik güncelleme — kaynak koddan SETUP.bat ile kurulum hâlâ gerekli önkoşul |

## Gereksinim (FR) durumu

| FR | Durum |
|---|---|
| FR-01..FR-14, FR-16..FR-22 | not-started (bkz. yukarıdaki safha eşlemesi, spec §21) |
| FR-15 | in-progress — Remotion composition + placeholder render canlı doğrulandı; editor/asset entegrasyonu, crop/QA (§16.3), cache (§16.5) kapsam dışı |

## Kritik test matrisi (AT-01..AT-46)

Henüz çalıştırılmadı (`not-run`). Her AT, ilgili safha tamamlandığında bu
dosyada `passed / failed / blocked / not-run` olarak güncellenecek.
Ayrıntılı sonuçlar `docs/TEST_REPORT.md` içinde.

## Bilinen engeller (özet — ayrıntı KNOWN_LIMITATIONS.md)

- OpenRouter / ElevenLabs API anahtarı yapılandırılmamış → LLM, video, TTS
  canlı çağrıları `live-blocked`.
- ~~`ffmpeg`, `scrcpy` bu makinede kurulu değildi~~ → **çözüldü**, bkz. aşağıdaki
  agent günlüğü satırı.
- Node sürümü LTS değil (bkz. DECISIONS.md) — Remotion render'ı bu sürümle
  GERÇEKTEN doğrulandı, ama resmi LTS değil.

## Agent koordinasyon günlüğü

| Zaman | Agent / dal | Kapsam | Sonuç |
|---|---|---|---|
| 2026-09-11 | coordinator (main) | Repo iskeleti, sözleşmeler | done, main'e push edildi |
| 2026-09-11 | coordinator (device-bridge) | Safha 4: ADB/scrcpy köprüsü | done, canlı doğrulandı |
| 2026-09-11 | agent/backend-jobs-api | Safha 1-2: job motoru, proje API | done, merge edildi (110/110 test) |
| 2026-09-11 | agent/provider-adapters | Safha 3: OpenRouter/TTS adaptörleri | done, merge edildi (canlı katalog) |
| 2026-09-11 | agent/frontend-web | Frontend UI iskeleti | tamamlandı, merge bekliyor |
| 2026-09-11 | agent/render-ffmpeg | `scripts/setup/fetch_binaries.py`, `scripts/doctor/check_env.py`, `apps/render` Remotion iskeleti (FR-15) | ffmpeg 9.0.1 ve scrcpy v4.1 gerçekten indirildi/doğrulandı/çalıştırıldı; `npx remotion render` ile 1080x1920/30fps/200 kare örnek MP4 gerçekten üretildi (out/sample.mp4, ~207 KB, ffprobe ile süre=6.667s doğrulandı). Ayrıntı: bu dosyanın sonundaki "Render ve araç doğrulama kanıtı" bölümü. |

## Render ve araç doğrulama kanıtı (2026-09-11, agent/render-ffmpeg)

**`scripts/setup/fetch_binaries.py` (gerçek çalıştırma çıktısı):**

```
[ffmpeg] Indiriliyor: https://github.com/GyanD/codexffmpeg/releases/download/9.0.1/ffmpeg-9.0.1-essentials_build.zip
[ffmpeg] Indirme dogrulandi (boyut+SHA-256): backend/.tools/_downloads/ffmpeg-9.0.1.zip
[ffmpeg] Cikartildi: backend/.tools/ffmpeg
[scrcpy] Indiriliyor: https://github.com/Genymobile/scrcpy/releases/download/v4.1/scrcpy-win64-v4.1.zip
[scrcpy] Indirme dogrulandi (boyut+SHA-256): backend/.tools/_downloads/scrcpy-v4.1.zip
[scrcpy] Cikartildi: backend/.tools/scrcpy

=== Ozet ===
ffmpeg 9.0.1: ffmpeg version 9.0.1-essentials_build-www.gyan.dev Copyright (c) 2000-2026 the FFmpeg developers
scrcpy v4.1: scrcpy 4.1 <https://github.com/Genymobile/scrcpy>
```

`scripts/doctor/check_env.py` aynı ortamda `node`, `npm`, `python`, `adb`,
`ffmpeg`, `ffprobe`, `scrcpy` için OK raporu verdi, exit code 0.

**`npx remotion versions` (Node v25.9.0 altında):**

```
Node.JS = v25.9.0, OS = win32
On version: 4.0.523
...
All packages have the correct version.
```

**`npx remotion render src/index.ts AdComposition out/sample.mp4`:** başarıyla
tamamlandı, `out/sample.mp4` (207 KB) üretti. `ffprobe` ile doğrulama:

```
codec_name=h264, width=1080, height=1920, r_frame_rate=30/1
duration=6.666667 (200 kare / 30fps ile birebir uyumlu)
size=206977, bit_rate=248372
```

Render edilen kareler manuel olarak PNG'ye çıkarılıp görsel olarak da
kontrol edildi: video track'teki placeholder dikdörtgenler "PLACEHOLDER" +
item/shot id metniyle görünüyor, grafik track'teki `title`/`cta_card`/`logo`
şablonları doğru zamanlamada beliriyor, audio track'ler için ekran üstü
"AUDIO PLACEHOLDER" uyarıları doğru sürelerde görünüp kayboluyor.

## Frontend (2026-09-11, agent/frontend-web)

`apps/web` Vite+React+TS(strict)+Tailwind kurulumu; TanStack Query +
Zustand; API client (spec §8.1 sözleşmesine göre tiplendi); Projeler/
Stüdyo(Brief)/Malzemeler/İşler/Ayarlar ekranları + sol menü + router.
`npm install` ve `npm run build` hatasız; `npm run dev` ile canlı
doğrulandı — geliştirildiği anda backend'in çoğu uç noktası (projects,
credentials, providers/models) henüz yoktu, bu yüzden tüm ekranlar o anda
gerçek "bağlantı yok" durumunu gösteriyordu (sahte veri yok). Bu backend
uç noktaları artık main'e merge edildi (bkz. yukarıdaki backend-jobs-api/
provider-adapters satırları) — frontend'in gerçek backend'e karşı ne
gösterdiği koordinatör tarafından ayrıca doğrulanacak, bkz. aşağıdaki not.
