# Üçüncü Taraf Bildirimleri

Bu belge, projede kullanılan üçüncü taraf paket/araç/kaynakların lisans
bilgilerini listeler (spec §20.3). Her ekleme, gerçek lisans metni/sürümüyle
doğrulanmadan buraya "MIT/Apache" gibi genel bir etiketle yazılmaz.

## Durum

Safha 9 (apps/render Remotion iskeleti) ve Safha 0/12 (ffmpeg/scrcpy temini)
kapsamında eklenen bağımlılıklar aşağıda kaydedilmiştir. Yeni bağımlılık
eklendikçe bu tablo güncellenir.

| Bileşen | Sürüm | Lisans | Not |
|---|---|---|---|
| Remotion (`remotion`, `@remotion/cli`, ve ilişkili `@remotion/*` paketleri) | 4.0.523 | **Remotion License** (MIT/Apache DEĞİL) | Ücretsiz katman: bireyler ve ≤3 çalışanlı, kâr amaçlı şirketler için ücretsiz (ticari kullanım dahil); STK'lar serbest. Daha büyük kâr amaçlı kuruluşlar için "Company License" (remotion.pro) gerekir. Kaynak: `node_modules/remotion/LICENSE.md`. Kullanıcının/organizasyonun bu eşiğin neresinde olduğu bu ajan tarafından varsayılmamıştır — gerekiyorsa lisans durumu kullanıcı tarafından teyit edilmelidir. |
| React, React DOM | 18.3.1 | MIT | Remotion peer dependency. |
| TypeScript | 5.6.3 | Apache-2.0 | Yalnızca derleme zamanı bağımlılığı. |
| FFmpeg (ffmpeg.exe, ffprobe.exe, ffplay.exe) | 9.0.1 (essentials build, `GyanD/codexffmpeg` — gyan.dev'in Windows build'lerinin GitHub üzerindeki resmi dağıtım deposu; bkz. `docs/DECISIONS.md`) | **GPL v3** (bu build `--enable-gpl --enable-version3` ile derlenmiş; libx264/libx265 gibi GPL bileşenler içerir) | Binary, `scripts/setup/fetch_binaries.py` ile `backend/.tools/ffmpeg/` altına indirilir; repoya commit edilmez. Kaynak: `backend/.tools/ffmpeg/README.txt`. |
| scrcpy (scrcpy.exe + paketlenmiş adb.exe, FFmpeg/SDL DLL'leri) | v4.1 (`Genymobile/scrcpy` resmi proje deposu) | Apache License 2.0 | Binary, `scripts/setup/fetch_binaries.py` ile `backend/.tools/scrcpy/` altına indirilir; repoya commit edilmez. Not: scrcpy Windows paketi kendi FFmpeg/SDL DLL'lerini de içerir (ayrı lisans şartları, `backend/.tools/scrcpy/LICENSE.txt`). |
