# Karar Günlüğü (DECISIONS.md)

Bu dosya, `IMPLEMENTATION_SPEC_TR.md` içinde açıkça belirtilmemiş düşük riskli teknik
tercihleri ve varsayılanlardan sapmaları kaydeder. Kullanıcıya rutin sorular
sorulmaz (§2.2); bu kararlar burada gerekçesiyle birlikte tutulur.

## 2026-09-11 — Depo kökü ve isimlendirme

Spec §6.3 örnek depo adı `local-ad-director/` kullanıyor. Gerçek GitHub deposu
`hakantimur/reklam-video` olarak önceden oluşturulmuş; bu yüzden repo kökü
doğrudan bu isimle kullanıldı, ekstra iç içe klasör açılmadı.

## 2026-09-11 — Node.js sürümü

Spec, uygulama anında güncel LTS'nin seçilip `.node-version`'a tam sürümle
yazılmasını istiyor. Bu makinede kurulu olan Node **v25.9.0** bir LTS sürümü
değil (mevcut LTS hattı 22.x/24.x). Ayrı bir LTS toolchain'i (ör. nvm-windows
ile) kurmak sistem genelinde yeni bir runtime kurulumu gerektirir; bu, kullanıcı
onayı olmadan yapılabilecek rutin bir paket kararı değil, sistem ortam
değişikliğine yakın bir eylemdir. Bu nedenle mevcut kurulu Node sürümü
kullanılmaya devam ediliyor ve `.node-version` bu sürüme sabitlendi.
Kullanıcı isterse ileride gerçek bir LTS toolchain kurulumu istenebilir; bu
karar tersine çevrilebilir ve `package.json#engines` alanında da not edildi.

## 2026-09-11 — Python sürümü

Spec Python 3.11 öneriyor; bu makinede kurulu olan 3.13.14 kullanıldı (proje
kendi venv'i içinde izole, global ortam etkilenmiyor). Uyumsuzluk çıkarsa
`backend/pyproject.toml` içindeki `requires-python` daraltılacak.

## 2026-09-11 — ffmpeg / scrcpy binary temini

Bu makinede `ffmpeg` ve `scrcpy` kurulu değildi. `scripts/setup/` altındaki
kurulum betikleri, resmi release kaynaklarından sürüm + checksum doğrulamasıyla
bu ikili dosyaları indirip `backend/.tools/` altına yerleştirecek şekilde
tasarlandı (bkz. `scripts/setup/fetch_binaries.py`).

## 2026-09-11 — Hedef oyun ve emülatör

Masaüstünde `Synova` (hafıza/beyin egzersizi) oyununun gerçek `.aab` build'i
(`Desktop/SYNOVA_yeni_surum/SYNOVA-0.1.1-2.aab`) ve bu proje için önceden
hazırlanmış iki AVD (`synova_shot`, `synova_test`) bulundu. İlk canlı emülatör
kabul testleri bu oyun ve bu AVD'ler üzerinden yürütülüyor. Örnek proje/brief
(spec §23.1) de zaten Synova ile örtüşüyor.

## 2026-09-11 — Paket yöneticisi

Node tarafında npm workspaces kullanıldı (npm zaten kurulu, ek araç kurulumu
gerekmedi). pnpm/yarn'a geçiş ileride düşük riskli bir değişikliktir.
