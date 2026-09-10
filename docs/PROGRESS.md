# İlerleme Takibi (PROGRESS.md)

Durumlar: `not-started`, `in-progress`, `implemented` (kod var, testler geçti),
`live-blocked` (kod/test tamam, canlı doğrulama donanım/anahtar eksikliğinden
engelli), `done` (kod + test + canlı doğrulama tamam).

Son güncelleme: 2026-09-11 (koordinatör oturumu başlangıcı).

## Safha durumu

| Safha | Konu | Durum | Not |
|---|---|---|---|
| 0 | Depo, ortam, kararlar | in-progress | İskelet kuruldu, bu commit ile |
| 1 | Kalıcı proje ve temel arayüz | in-progress | UI iskeleti (apps/web) implemented + `npm run build` geçti; backend tarafı (projects/brief/credentials uç noktaları) henüz yok, bkz. KNOWN_LIMITATIONS.md |
| 2 | İş motoru, olaylar, bütçe | not-started | |
| 3 | Sağlayıcılar ve model keşfi | implemented (canlı katalog dahil) | GET /providers/models CANLI: 437 model (OpenRouter), video kataloğu 29 model. generate_structured/video submit-poll-download/ElevenLabs mock (key yok, provider_live marker ile ayrı). 67/67 test geçti |
| 4 | Emülatör köprüsü, eşzamanlı kayıt | done | synova_test AVD üzerinde CANLI doğrulandı: ADB keşif/screenshot/tap/swipe, normalize koordinat + stale-observation reddi, scrcpy ile 17.7sn gerçek kayıt (3 eylem sırasında, H264+opus, ffprobe ile doğrulandı), /devices preflight API'si (screenshot+touch+kayıt+ses testi) — 9/9 device_live pytest geçti |
| 5 | Görsel operatör, gerçek çekim | not-started | LLM key gerektirir → key gelene kadar live-blocked |
| 6 | Yönetmen, senaryo, animatic | not-started | LLM key gerektirir |
| 7 | Çekim arşivi, retake | not-started | |
| 8 | İnsanlı AI sahneler, ses | not-started | Video/TTS provider key gerektirir |
| 9 | Timeline ve final render | in-progress | Remotion iskeleti + placeholder composition canlı render ile doğrulandı (FR-15); gerçek asset/editor entegrasyonu, crop/QA, cache kapsam dışı bu round'da |
| 10 | Revizyon, kilit, varyasyon | not-started | |
| 11 | QA, yerleşim, teslim | not-started | |
| 12 | Windows paketleme, regresyon | not-started | |

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
