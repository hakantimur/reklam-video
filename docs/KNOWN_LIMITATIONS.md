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

## Donanım / oyun durumu (olumlu not)

- Hedef oyun `Synova` gerçek `.aab` dosyası ve iki AVD (`synova_shot`,
  `synova_test`) mevcut. Bu, emülatör köprüsü ve kontrol döngüsü testlerinin
  (Safha 4) API anahtarı gerekmeden canlı yapılabileceği anlamına gelir.

Bu bölüm ilerledikçe güncellenecektir.
