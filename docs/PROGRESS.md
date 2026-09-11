# İlerleme Takibi (PROGRESS.md)

Durumlar: `not-started`, `in-progress`, `implemented` (kod var, testler geçti),
`live-blocked` (kod/test tamam, canlı doğrulama donanım/anahtar eksikliğinden
engelli), `done` (kod + test + canlı doğrulama tamam).

Son güncelleme: 2026-09-11 (koordinatör oturumu — Safha 0-11 canlı
doğrulandı, Safha 12 kısmi/in-progress; ayrıntı bu dosyanın altında).

## Safha durumu

| Safha | Konu | Durum | Not |
|---|---|---|---|
| 0 | Depo, ortam, kararlar | in-progress | İskelet kuruldu, bu commit ile |
| 1 | Kalıcı proje ve temel arayüz | done (bu round için) | Tam yığın CANLI doğrulandı: gerçek backend + gerçek derlenmiş UI, tarayıcıda proje oluşturma → brief kaydetme → klasör açma uçtan uca çalıştı. Entegrasyon sırasında bulunan 5 hata aynı oturumda düzeltildi, bkz. TEST_REPORT.md |
| 2 | İş motoru, olaylar, bütçe | implemented | Job queue + SSE + bütçe defteri kodlandı ve test edildi (110→116 testin parçası); main.py'a bağlandı, canlı proje/job akışı çalıştı |
| 3 | Sağlayıcılar ve model keşfi | implemented (canlı katalog dahil) | GET /providers/models CANLI: 437 model (OpenRouter), video kataloğu 29 model. generate_structured/video submit-poll-download/ElevenLabs mock (key yok, provider_live marker ile ayrı). 67/67 test geçti |
| 4 | Emülatör köprüsü, eşzamanlı kayıt | done | synova_test AVD üzerinde CANLI doğrulandı: ADB keşif/screenshot/tap/swipe, normalize koordinat + stale-observation reddi, scrcpy ile 17.7sn gerçek kayıt (3 eylem sırasında, H264+opus, ffprobe ile doğrulandı), /devices preflight API'si (screenshot+touch+kayıt+ses testi) — 9/9 device_live pytest geçti |
| 5 | Görsel operatör, gerçek çekim | in-progress | Sınırlı oyun KEŞFİ CANLI doğrulandı: gerçek Synova uygulamasında, gerçek ekran görüntüleriyle karar veren LLM operatör, 6 eylem sınırıyla gerçekten oynadı ve doğru bir GameProfile üretti ("4x4 grid'de sıra ezberleme oyunu", güven 0.72 — gerçek gözleme dayalı, uydurulmamış). Ayrı bir denemede gerçek bir sistem ANR diyaloğunu doğru tanıyıp `request_takeover` ile durdu (spec 11.8, gizli otomatik onay yok). Gerçek çekim (shot capture, olay tespiti) henüz yok — bu sadece keşif |
| 6 | Yönetmen, senaryo, animatic | in-progress | ConceptSet + ShotPlan (Script dahil) üretimi CANLI doğrulandı: seçili fikirden 600 kareye tam oturan 6 sahnelik gerçek bir plan üretildi (3 AI sahne + 3 gerçek oynanış sahnesi), Revision+Shot olarak DB'ye kaydedildi, tarayıcıda görüntülendi. Model, kare toplamını ilk denemede tutturamayınca spec §10.4'teki tek düzeltme denemesi devreye girdi ve ikinci denemede başarılı oldu — gerçek kanıt. Animatic (sesli/zamanlı önizleme) henüz yok |
| 7 | Çekim arşivi, retake | in-progress | Gerçek oynanış çekimi CANLI doğrulandı: Safha 6'da üretilen gerçek ShotPlan'ın "gameplay" sahneleri için, görsel operatör döngüsü (Safha 5) artık gerçek scrcpy kaydı altında çalışıyor. Stüdyo'ya gerçek bir "Çekim" adımı eklendi (cihaz seçimi, sahne başına "Çek"/"Yeniden çek", take listesi + video önizleme + "Bu çekimi seç") — tarayıcıda CANLI denendi: buton tıklaması gerçek bir capture job'u tetikledi, gerçek scrcpy süreci (PID doğrulandı) kaydetti, iş bitince take listesi otomatik yenilendi, "Bu çekimi seç" gerçek `shots.selected_take_id`'yi DB'de güncelledi. Retake sayacı (attempt) ve kontrol-devrinde kısmi kaydı silmeden reddedilmiş Take olarak saklama da doğrulandı. Henüz yok: otomatik olay tespitiyle in/out kırpma |
| 8 | İnsanlı AI sahneler, ses | in-progress | AI sahne üretimi (video) ve seslendirme (TTS) CANLI doğrulandı, gerçek paralı API çağrılarıyla: `google/veo-3.1-lite` ile gerçek 4.01sn h264+aac MP4 üretildi (ffprobe ile bağımsız doğrulandı, teknik QC 4/4 geçti), aynı sahne için yönetmenin gerçek bir video-üretim prompt'u yazdığı ve `Shot.generation_prompt`'a kaydedildiği doğrulandı. ElevenLabs ile aynı sahnenin gerçek Türkçe seslendirme metninden gerçek 4.46sn MP3 üretildi. Stüdyo'ya gerçek bir "Taslak" ekranı eklendi (her AI sahnesi için üret/yeniden üret + önizleme, her seslendirme için gerçek ses listesinden seçim + üret, tarayıcıda CANLI denendi — bir sahne gerçekten üretildi, "Yeniden üret" durumuna geçti). Henüz yok: lipsync (LipSyncProvider hâlâ arayüz düzeyinde) |
| 9 | Timeline ve final render | in-progress | Gerçek asset boru hattı CANLI doğrulandı (FR-15 devamı): `POST /projects/{id}/timeline/build` gerçek Revision+Shot'lardan gerçek bir Timeline JSON üretip `Revision.timeline_json`'a yazıyor (var olan Take/voice Asset'leri referanslıyor, henüz çekilmemiş sahneler için `asset_id: null` — uydurma yok). `POST /projects/{id}/render/preview`, bu timeline'ı gerçek dosyaları `apps/render/public/`'a kopyalayıp gerçek bir `remotion render` çalıştırarak 20.05sn/1080x1920 gerçek bir kompozit MP4'e dönüştürdü: aynı videoda hem gerçek Google Veo AI sahnesi, hem gerçek Synova oynanış kaydı, hem de çekilmemiş bir sahne için dürüst PLACEHOLDER art arda göründü (üç kare bağımsız olarak çıkarılıp görsel olarak doğrulandı). Taslak ekranına "Timeline oluştur" + "Önizleme render et" eklendi ve tarayıcıda CANLI denendi — gerçek 8.3MB/20sn bir önizleme videosu üretilip oynatıcıda göründü. Gerçek altyazı metni render de CANLI doğrulandı: `timeline.py` artık `transform.captionText` taşıyor, `AdComposition` bunu ekrana basıyor — gerçek Synova projesi yeniden render edilip bir kare çıkarılarak Türkçe altyazının AI sahnesi üzerinde doğru göründüğü görsel olarak doğrulandı. Henüz yok: ses kısma/mixing, editör arayüzü, crop/QA (§16.3), cache (§16.5) |
| 10 | Revizyon, kilit, varyasyon | in-progress | `POST /projects/{id}/revisions/{revision_id}/variation` CANLI doğrulandı: gerçek Synova projesinde tek bir sahneye ("CTA'yı daha aciliyetli yap, sınırlı süreli ücretsiz deneme vurgusu ekle") gerçek bir talimat verildi; yönetmen o sahneyi (`target_frames` sabit kalarak) gerçekten yeniden yazdı (yeni caption/voice_text talimatı doğru yansıttı), diğer 5 sahne değişmeden yeni revizyona taşındı. **Bu canlı test sırasında gerçek bir hata bulundu ve düzeltildi:** taşıma mantığı yalnızca `shots.selected_take_id` açıkça set edilmişse (yani biri "Bu çekimi seç" demişse) take'i taşıyordu; hiç seçilmemiş ama var olan bir take (ör. bir AI sahnesi, hiç "seç" düğmesi olmayan bir tür) sessizce kayboluyordu. Artık `timeline.selected_or_best_take` ile aynı "seçili veya en iyi uygun" mantığı kullanılıyor — gerçek Synova projesinde AI Hook sahnesinin video'sunun kaybolmadığı yeni bir testle doğrulandı. Görsel kilitli bir sahneye talimat verilirse istek sessizce yok sayılmıyor, açık 422 ile reddediliyor. Henüz yok: varyasyonlar arası UI karşılaştırma, kilit açma/kapama ekranı |
| 11 | QA, yerleşim, teslim | in-progress | `GET /projects/{id}/revisions/{revision_id}/qa` ve `POST .../export` CANLI doğrulandı. QA gerçek Synova revizyonuna karşı çalıştırıldığında dürüstçe FAILED döndü (kalan eksik sahneleri tek tek listeledi). Ayrı, minimal gerçek bir projede: bir `ai_generated` sahne gerçek Veo videosuyla üretildi → QA gerçekten PASSED döndü → export job'u gerçek bir `remotion render` çalıştırıp `exports/v001/` altına 4.05sn/1080x1920 gerçek bir export MP4 yazdı (teknik QC 4/4, ffprobe ile bağımsız doğrulandı). QA, `synthetic_test` kökenli asset'leri ve başarısız/belirsiz teknik QC'yi de doğru şekilde reddediyor (mock testlerle). Stüdyo'ya gerçek bir "Çıktı" ekranı eklendi (QA raporu + dışa aktar düğmesi, QA geçmeden devre dışı) — tarayıcıda CANLI denendi: gerçek eksik sahneler doğru listelendi, "Dışa aktar" düğmesi doğru şekilde devre dışı görünüyordu. İçerik/marka güvenliği reviewer'ı da eklendi ve CANLI doğrulandı: `POST /projects/{id}/shots/{shot_id}/review` gerçek bir gameplay klibinden 4 kare örnekleyip gerçek bir vision LLM çağrısıyla değerlendirdi — model "0 of 4 selected" → "2 of 4" gibi somut, gerçekten ekrandan okunan ayrıntılarla `pass` verdisi verdi, sonuç `qa_reports` tablosuna kalıcı yazıldı ve `run_revision_qa` bunu otomatik hesaba kattı (inceleme isteğe bağlı — hiç çalıştırılmamış bir take QA'yı bloklamıyor). Henüz yok: yerleşime (placement_id) özgü format doğrulaması, inceleme için UI düğmesi |
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
