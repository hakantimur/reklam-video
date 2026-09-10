# Kullanıcı Rehberi (USER_GUIDE_TR.md)

Bu rehber, uygulamanın **şu an gerçekten çalışan** kısımlarını anlatır.
Tam ürün vizyonu için `docs/IMPLEMENTATION_SPEC_TR.md`, hangi safhaların
tamamlandığı için `docs/PROGRESS.md` ve bilinen sınırlamalar için
`docs/KNOWN_LIMITATIONS.md` dosyalarına bakın. Burada anlatılmayan bir
özellik (otomatik oyun oynama, AI video üretimi, kurgu/render, dışa
aktarma) henüz uygulanmamıştır — bu rehber onları "yakında" diye vaat
etmez.

## 1. Kurulum

```bat
SETUP.bat
```

Bu betik: Python venv'i kurar, veritabanı şemasını uygular, ffmpeg/scrcpy'yi
resmi kaynaklardan indirir (varsa), web arayüzü bağımlılıklarını kurar ve
arayüzü derler. İlk çalıştırma birkaç dakika sürebilir (indirmeler
nedeniyle).

## 2. Başlatma ve durdurma

```bat
START.bat
```

Backend'i arka planda başlatır, hazır olmasını bekler ve tarayıcınızda
`http://127.0.0.1:8765` adresini açar.

```bat
STOP.bat
```

Yalnızca bu uygulamanın başlattığı süreci kapatır; başka hiçbir programa
dokunmaz.

## 3. Bugün yapabilecekleriniz

### Proje oluşturma

Projeler ekranında "Yeni proje" veya (ilk kullanımda) "Örnek proje
oluştur" ile bir proje açabilirsiniz. Proje, bilgisayarınızda
`Belgelerim\LocalAdDirector\Projects\` altında gerçek bir klasörle
saklanır; "Klasörde göster" ile bu klasörü açabilirsiniz.

### Brief (reklam özeti) doldurma

Stüdyo → Brief adımında şu bilgileri girersiniz: ürün adı, kısa gerçek
açıklama, hedef/CTA (zorunlu); hedef kitle, ana mesaj, dil, süre, tarz,
yerleşim, bütçe (isteğe bağlı, boş bırakılırsa mantıklı varsayılanlar
kullanılır). "Kaydet" dediğinizde bu bilgi kalıcı olarak veritabanına
yazılır ve uygulamayı kapatıp tekrar açsanız da kaybolmaz.

### Ayarlar

- **OpenRouter / ElevenLabs API anahtarı**: Buraya girdiğiniz anahtar
  Windows Credential Manager'da güvenle saklanır, hiçbir zaman düz metin
  olarak dosyaya veya log'a yazılmaz. Anahtar girilmeden proje oluşturma
  ve brief kaydetme çalışmaya devam eder; yalnızca AI (yönetmen, video,
  ses) işlemleri devre dışı kalır.
- **Çalışma zamanı tanılaması**: node/adb/scrcpy/ffmpeg/ffprobe'un gerçekten
  kurulu olup olmadığını ve disk alanını gösterir.
- **Model kataloğu**: "Modelleri yenile" ile OpenRouter'ın güncel model
  listesini (anahtar gerekmeden) gerçekten çeker ve gösterir.

## 4. Henüz çalışmayanlar (bilinçli olarak)

- Oyunu otomatik keşfetme, senaryo/çekim listesi üretme, oyunu kendi
  oynayarak kayıt alma (Safha 5-7) — bunlar için OpenRouter anahtarı ve
  daha fazla geliştirme gerekiyor. Emülatör köprüsünün kendisi (bağlantı,
  ekran görüntüsü, dokunma, kayıt) arka planda çalışıp test edilmiş
  durumda, ama uygulama arayüzünden henüz tetiklenmiyor.
- AI insanlı sahne/video üretimi, ses/altyazı, kurgu/render, dışa aktarma
  (Safha 8-11) — henüz yok.
- Malzemeler ve İşler ekranları şu an sadece "yakında" durumunu gösteriyor.
- Brief formu, daha önce kaydedilmiş bir brief'i geri yükleyip forma
  doldurmuyor; her seferinde varsayılanlardan başlıyor (veri kaybolmuyor,
  sadece formda görünmüyor).

## 5. Bir şeyler ters giderse

- Backend başlamazsa: `.run\backend.log` dosyasına bakın.
- "Backend bağlantısı yok" görüyorsanız: `START.bat` çalıştığından ve
  `http://127.0.0.1:8765/api/v1/health` adresinin tarayıcıda `{"status":"ok"...}`
  döndüğünden emin olun.
- Ayarlar'daki tanılama ffmpeg/scrcpy/adb için "bulunamadı" gösteriyorsa:
  `SETUP.bat`'ı tekrar çalıştırın veya `python scripts/setup/fetch_binaries.py`
  komutunu elle çalıştırın.
