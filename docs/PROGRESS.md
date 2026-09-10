# İlerleme Takibi (PROGRESS.md)

Durumlar: `not-started`, `in-progress`, `implemented` (kod var, testler geçti),
`live-blocked` (kod/test tamam, canlı doğrulama donanım/anahtar eksikliğinden
engelli), `done` (kod + test + canlı doğrulama tamam).

Son güncelleme: 2026-09-11 (koordinatör oturumu başlangıcı).

## Safha durumu

| Safha | Konu | Durum | Not |
|---|---|---|---|
| 0 | Depo, ortam, kararlar | in-progress | İskelet kuruldu, bu commit ile |
| 1 | Kalıcı proje ve temel arayüz | not-started | |
| 2 | İş motoru, olaylar, bütçe | not-started | |
| 3 | Sağlayıcılar ve model keşfi | not-started | OpenRouter key yok → contract/mock testleri hedef |
| 4 | Emülatör köprüsü, eşzamanlı kayıt | done | synova_test AVD üzerinde CANLI doğrulandı: ADB keşif/screenshot/tap/swipe, normalize koordinat + stale-observation reddi, scrcpy ile 17.7sn gerçek kayıt (3 eylem sırasında, H264+opus, ffprobe ile doğrulandı), /devices preflight API'si (screenshot+touch+kayıt+ses testi) — 9/9 device_live pytest geçti |
| 5 | Görsel operatör, gerçek çekim | not-started | LLM key gerektirir → key gelene kadar live-blocked |
| 6 | Yönetmen, senaryo, animatic | not-started | LLM key gerektirir |
| 7 | Çekim arşivi, retake | not-started | |
| 8 | İnsanlı AI sahneler, ses | not-started | Video/TTS provider key gerektirir |
| 9 | Timeline ve final render | not-started | ffmpeg indirilecek |
| 10 | Revizyon, kilit, varyasyon | not-started | |
| 11 | QA, yerleşim, teslim | not-started | |
| 12 | Windows paketleme, regresyon | not-started | |

## Gereksinim (FR) durumu

| FR | Durum |
|---|---|
| FR-01..FR-22 | not-started (bkz. yukarıdaki safha eşlemesi, spec §21) |

## Kritik test matrisi (AT-01..AT-46)

Henüz çalıştırılmadı (`not-run`). Her AT, ilgili safha tamamlandığında bu
dosyada `passed / failed / blocked / not-run` olarak güncellenecek.
Ayrıntılı sonuçlar `docs/TEST_REPORT.md` içinde.

## Bilinen engeller (özet — ayrıntı KNOWN_LIMITATIONS.md)

- OpenRouter / ElevenLabs API anahtarı yapılandırılmamış → LLM, video, TTS
  canlı çağrıları `live-blocked`.
- `ffmpeg`, `scrcpy` bu makinede kurulu değildi → otomatik indirme betikleriyle
  temin edilecek.
- Node sürümü LTS değil (bkz. DECISIONS.md).

## Agent koordinasyon günlüğü

| Zaman | Agent / dal | Kapsam | Sonuç |
|---|---|---|---|
| 2026-09-11 | coordinator (main) | Repo iskeleti, sözleşmeler | done, main'e push edildi |
| 2026-09-11 | coordinator (device-bridge) | Safha 4: ADB/scrcpy köprüsü | done, canlı doğrulandı |
| 2026-09-11 | agent/backend-jobs-api | Safha 1-2: job motoru, proje API | çalışıyor |
| 2026-09-11 | agent/provider-adapters | Safha 3: OpenRouter/TTS adaptörleri | çalışıyor |
| 2026-09-11 | agent/frontend-web | Frontend UI iskeleti | çalışıyor |
| 2026-09-11 | agent/render-ffmpeg | Remotion + ffmpeg/scrcpy temini | çalışıyor |
