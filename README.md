# Local Ad Director

Tek kullanıcılı, yerelde çalışan reklam video üretim aracı. Android
emülatöründeki oyunu gerçek oynanışla kaydeder, AI ile üretilmiş insanlı/ürün
sahneleriyle birleştirir, ses/altyazı/logo/CTA ekleyip Facebook/Instagram/
YouTube Shorts için MP4 üretir.

Tam ürün ve mühendislik şartnamesi: [`docs/IMPLEMENTATION_SPEC_TR.md`](docs/IMPLEMENTATION_SPEC_TR.md).
Kullanıcı rehberi (bugün ne çalışıyor): [`docs/USER_GUIDE_TR.md`](docs/USER_GUIDE_TR.md).
Güncel uygulama durumu: [`docs/PROGRESS.md`](docs/PROGRESS.md).
Test raporu: [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md).
Bilinen sınırlamalar: [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md).
Teknik/ürün kararları: [`docs/DECISIONS.md`](docs/DECISIONS.md).

## Depo yapısı

```text
apps/web/        React + TypeScript + Vite + Tailwind arayüz
apps/render/     Remotion tabanlı render motoru
backend/         Python 3.13 + FastAPI + SQLAlchemy + worker'lar
packages/contracts/  Paylaşılan JSON şema / tip sözleşmeleri
config/          Yerleşim profilleri, stil ön ayarları
prompts/         Sürümlü LLM sistem promptları (director/operator/reviewer/revision)
scripts/         Kurulum, başlatma, durdurma, tanı, paketleme betikleri
fixtures/        Açıkça etiketli sentetik test verisi
```

## Geliştirme ortamı

- Node: bkz. `.node-version` (bkz. `docs/DECISIONS.md` — LTS değil, kayıtlı sapma)
- Python: 3.13 (proje-özel venv, `backend/.venv`)
- Android SDK platform-tools (adb) kurulu olmalı; test AVD'leri: `synova_shot`, `synova_test`

## Doğrulama ortamı (bu depo için gerçek test kaydı)

- OS: Windows 11 Pro (build 10.0.26100)
- Emülatör: Android Studio AVD (`synova_shot`, `synova_test`)
- Hedef oyun: Synova (yerel `.aab` build, sürüm 0.1.1-2)
- Sağlayıcı: OpenRouter (anahtar henüz yapılandırılmadı — bkz. KNOWN_LIMITATIONS.md)

## Hızlı başlangıç (Windows)

```bat
SETUP.bat
START.bat
```

`STOP.bat` yalnızca bu uygulamanın başlattığı süreçleri kapatır.

## ffmpeg / scrcpy ve ortam tanısı

`ffmpeg` ve `scrcpy` sisteme kurulu değilse (veya sürümü doğrulanmak
isteniyorsa):

```bash
python scripts/setup/fetch_binaries.py   # backend/.tools/{ffmpeg,scrcpy}/ altına indirir, sürüm+SHA-256 doğrular
python scripts/doctor/check_env.py       # node/python/adb/ffmpeg/scrcpy varlık+sürüm tanısı
```

`backend/.tools/` commit edilmez (bkz. `.gitignore`); yalnızca indirme betiği
repoda tutulur. Kaynak seçimleri ve checksum doğrulama detayları
`docs/DECISIONS.md`'de kayıtlıdır.

## apps/render (Remotion)

```bash
npm install
cd apps/render
npx remotion studio src/index.ts          # interaktif önizleme
npx remotion render src/index.ts AdComposition out/sample.mp4
```

Bu turda `video`/`audio` track item'ları gerçek asset yerine açıkça
"PLACEHOLDER" etiketli render çıktısı üretir (bkz.
`docs/KNOWN_LIMITATIONS.md`).
