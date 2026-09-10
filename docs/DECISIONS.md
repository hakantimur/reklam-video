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

Bu makinede `ffmpeg` ve `scrcpy` kurulu değildi. `scripts/setup/fetch_binaries.py`,
resmi release kaynaklarından sürüm + checksum doğrulamasıyla bu ikili
dosyaları indirip `backend/.tools/` altına yerleştirir. Betik gerçekten
çalıştırıldı; ikisi de gerçekten indirildi, doğrulandı ve çalıştırıldı (bkz.
`docs/PROGRESS.md`).

Kaynak seçimleri ve gerekçeleri:

- **ffmpeg**: `ffmpeg.org/download.html`'in Windows sekmesi doğrudan iki
  kaynağa yönlendiriyor: gyan.dev build'leri ve `BtbN/FFmpeg-Builds`.
  gyan.dev build'leri `GyanD/codexffmpeg` GitHub deposu üzerinden, düzgün
  sürüm etiketleriyle (ör. `9.0.1`) dağıtılıyor; `BtbN/FFmpeg-Builds` ise
  git master'a bağlı otomatik/gece build'leri olup sabit bir sürüm numarası
  yerine commit/tarih bazlı etiketler kullanıyor. Sabit bir sürüm numarasına
  pinlemek istediğimiz için `GyanD/codexffmpeg` seçildi; `essentials_build`
  varyantı (tam build değil) alındı çünkü ihtiyacımız olan tek şey
  `ffmpeg`/`ffprobe` (spec §16.2, §16.4 — normalizasyon, miks, encode,
  doğrulama) ve essentials build bunun için yeterli.
  - **Checksum notu**: gyan.dev, zip'in yanında ayrı imzalı bir checksum
    dosyası yayınlamıyor. Bunun yerine GitHub Releases API'sinin o tam
    release asset'i için döndürdüğü `digest` alanındaki SHA-256 değeri
    kullanıldı (GitHub bunu asset yüklendiğinde sunucu tarafında hesaplıyor;
    bu, gyan.dev tarafından ayrıca imzalanmış bağımsız bir vendor checksum'ı
    DEĞİL, ama GitHub'ın o değişmez release asset'i için tuttuğu doğrulanabilir
    bir değer). Bu ayrım `scripts/setup/fetch_binaries.py` içindeki yorumlarda
    ve `THIRD_PARTY_NOTICES.md`'de de açıkça belirtildi. Sürüm ve SHA-256,
    betikte sabit (hardcoded) değerler olarak tutuluyor; kaynak değişirse
    betik boyut/SHA-256 uyuşmazlığında açıkça hata verip indirmeyi durduruyor.
- **scrcpy**: `Genymobile/scrcpy` (resmi proje deposu), sürüm `v4.1`.
  Bu depo her release'de imzalı bir `SHA256SUMS.txt` (+ `.asc` imzası)
  yayınlıyor; `scrcpy-win64-v4.1.zip` için oradaki SHA-256 değeri birebir
  kullanıldı (GitHub API'nin `digest` alanıyla da çapraz doğrulandı, ikisi
  eşleşiyor).

İkisi için de betik önce dosya boyutunu, sonra SHA-256'yı doğruluyor; ikisi de
sabit sürüme pinli (asla "latest" çekilmiyor). `backend/.tools/` içeriği
`.gitignore`'a eklendi; yalnızca `scripts/setup/fetch_binaries.py` commit
edilir, indirilen binary'ler asla commit edilmez.

## 2026-09-11 — apps/render Remotion sürümü ve Node uyumluluğu

Remotion `4.0.523` (npm'deki en güncel sürüm, tüm `@remotion/*` paketleri
aynı tam sürüme sabitlendi — spec §6.1) kuruldu. Bu makinedeki Node
`v25.9.0` LTS değil (yukarıdaki "Node.js sürümü" kararına bkz.). Gerçek
doğrulama yapıldı, sahte "çalışıyor" iddia edilmedi:

- `npx remotion versions` Node v25.9.0 altında hatasız çalıştı ve "All
  packages have the correct version" raporu verdi; Remotion'ın kendi sürüm
  tutarlılık kontrolü bir Node sürüm uyumsuzluğu bayrağı kaldırmadı.
- `npx remotion render` ile örnek composition gerçekten bir MP4'e render
  edildi (bkz. `docs/PROGRESS.md` — dosya boyutu/süre kanıtıyla). Chrome
  Headless Shell otomatik indirildi ve sorunsuz çalıştı.
- Bilinen tek gerçek uyumsuzluk `remotion.config.ts` içindeydi: Remotion'ın
  config loader'ı bu dosyayı CommonJS olarak bundle'layıp çalıştırıyor (proje
  genelinde ESM kullansak da), bu yüzden `import.meta.url` boş/`undefined`
  dönüyordu; `__dirname` (CJS'de otomatik mevcut) kullanılarak düzeltildi.
  Bu, Node 25 uyumsuzluğu değil, Remotion'ın config dosyasını nasıl
  bundle'ladığıyla ilgili bir detaydı.
- Sonuç: Node v25.9.0 ile Remotion 4.0.523 arasında engelleyici bir
  uyumsuzluk GÖZLEMLENMEDİ, ama Node 25 resmi olarak Remotion'ın "desteklenen
  LTS" matrisinde değildir (Remotion resmi olarak belirli bir Node sürüm
  listesi yayınlamıyor; en güvenli varsayım güncel LTS'dir). İleride resmi
  bir LTS'e (22.x/24.x) geçilirse bu render tekrar doğrulanmalıdır.

## 2026-09-11 — Timeline JSON şema uzantı alanları (grafik/placeholder)

`packages/contracts/timeline.schema.json` kasıtlı olarak `track_item.transform`
alanını serbest bir `object` bırakıyor ve hiçbir yerde
`additionalProperties: false` kullanmıyor. `apps/render/src/schemas/timeline.ts`
bu boşluğu, şemayı DEĞİŞTİRMEDEN, iki render-only uzantı alanıyla dolduruyor:

- `transform.graphic`: grafik track item'ları için şablon adı (`title`,
  `cta_card`, `logo`, `lower_third`, `challenge_counter`), metin/alt metin,
  renk ve keyframe listesi.
- `transform.placeholderLabel` / `transform.placeholderColor`: video/audio
  track item'ları için bu turda gerçek asset olmadığını açıkça gösteren
  placeholder render bilgisi.

Bu alanlar şemayı ihlal etmiyor (şema onları ne zorunlu kılıyor ne de
yasaklıyor); ancak gerçek asset boru hattı (Safha 7/8) geldiğinde backend'in
bu render-only sözleşmeye de uyması veya bu alanları kendi ürettiği
Timeline JSON'larında doldurması gerekecek. Bu, `packages/contracts/timeline.schema.json`'a
yeni zorunlu alan eklemekten farklı, geriye dönük uyumlu bir yaklaşımdır.

## 2026-09-11 — Hedef oyun ve emülatör

Masaüstünde `Synova` (hafıza/beyin egzersizi) oyununun gerçek `.aab` build'i
(`Desktop/SYNOVA_yeni_surum/SYNOVA-0.1.1-2.aab`) ve bu proje için önceden
hazırlanmış iki AVD (`synova_shot`, `synova_test`) bulundu. İlk canlı emülatör
kabul testleri bu oyun ve bu AVD'ler üzerinden yürütülüyor. Örnek proje/brief
(spec §23.1) de zaten Synova ile örtüşüyor.

## 2026-09-11 — Paket yöneticisi

Node tarafında npm workspaces kullanıldı (npm zaten kurulu, ek araç kurulumu
gerekmedi). pnpm/yarn'a geçiş ileride düşük riskli bir değişikliktir.
