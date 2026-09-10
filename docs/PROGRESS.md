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
| 4 | Emülatör köprüsü, eşzamanlı kayıt | not-started | synova_test AVD hazır, key gerekmiyor → canlı test yapılabilir |
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
| 2026-09-11 | coordinator (main) | Repo iskeleti, sözleşmeler | in-progress |
