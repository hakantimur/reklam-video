# Bilinen Sınırlamalar (KNOWN_LIMITATIONS.md)

Bu dosya, gerçek sağlayıcı/oyun/OS sınırlamalarını ve canlı doğrulaması
yapılamamış alanları listeler (spec §24.1). "Tüm testler geçti" iddiası bu
liste boşalana kadar kullanılmaz.

## Canlı doğrulama engelleri (2026-09-11 itibarıyla)

1. **OpenRouter API anahtarı yok.** Yönetmen (director), operatör (oyun
   kontrolü stratejisi), reviewer ve video/TTS üretimi bu anahtara bağlıdır.
   Anahtar girilene kadar bu akışlar yalnızca mock/contract testleriyle
   doğrulanabilir; gerçek model çıktısı doğrulanmamıştır.
2. **ElevenLabs API anahtarı yok (opsiyonel ikinci ses yolu).**
3. **ffmpeg / scrcpy** başta bu makinede kurulu değildi; geliştirme/test
   amacıyla resmi kaynaklardan (`Genymobile/scrcpy` GitHub releases v4.1,
   `BtbN/FFmpeg-Builds` GitHub releases) elle indirilip `backend/.tools/`
   altına yerleştirildi ve `app/core/tool_paths.py` bunları PATH'te yoksa
   otomatik buluyor. Bu geçici/geliştirme kurulumudur — üretim `SETUP.bat`
   akışı için sürüm sabitleme + checksum doğrulamalı resmi betik
   (`scripts/setup/fetch_binaries.py`) ayrı bir agent tarafından hazırlanıyor.
4. **Node sürümü LTS değil** (bkz. DECISIONS.md) — Remotion/derleme
   uyumluluğu bu sürümle doğrulanacak, sorun çıkarsa ayrıca raporlanacak.

## Donanım / oyun durumu (olumlu not)

- Hedef oyun `Synova` gerçek `.aab` dosyası ve iki AVD (`synova_shot`,
  `synova_test`) mevcut. Bu, emülatör köprüsü ve kontrol döngüsü testlerinin
  (Safha 4) API anahtarı gerekmeden canlı yapılabileceği anlamına gelir.

Bu bölüm ilerledikçe güncellenecektir.
