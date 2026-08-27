# Dependencies

Dokumen ini menjelaskan semua dependency yang dipakai `napaktilas.py`,
baik package Python maupun binary eksternal (FFmpeg), termasuk kenapa
masing-masing dibutuhkan dan apa yang sebenarnya *tidak* dipakai script
ini meski ikut ter-install.

## Ringkasan

| Kategori         | Nama          | Wajib?   | Fungsi di script                          |
|-------------------|---------------|----------|--------------------------------------------|
| Python package     | `numpy`       | Wajib    | Interpolasi titik lokasi antar frame       |
| Python package     | `matplotlib`  | Wajib    | Render tiap frame (jalur, titik, kanvas)   |
| Python package     | `contextily`  | Opsional | Ambil basemap tile (peta latar belakang)   |
| Library sistem      | `GDAL`        | Opsional | Dibutuhkan `rasterio` (dependency `contextily`) untuk baca raster |
| Binary eksternal    | `ffmpeg`      | Wajib    | Gabung frame PNG menjadi video MP4         |

Kalau `contextily` tidak diinstall, script tetap jalan — video tetap
dibuat, hanya tanpa gambar peta di latar belakang (garis rute & titik
tetap tampil di atas kanvas polos). Ini juga cara termudah untuk
memastikan **tidak ada koneksi jaringan sama sekali** saat render.

---

## 1. Python packages (`requirements.txt`)

```
numpy
matplotlib
contextily
```

Install dengan:

```bash
pip install -r requirements.txt
```

### `numpy`
Dipakai di fungsi `interpolate_points()` untuk `np.interp()` — menyebar
titik lokasi secara merata sepanjang durasi video berdasarkan waktu
asli tiap titik, supaya kamera bergerak halus, bukan patah-patah
mengikuti jarak antar sampel data mentah.

### `matplotlib`
Dipakai untuk menggambar tiap frame (`render_frames()`): jalur rute,
titik posisi saat ini, dan menyimpannya sebagai file PNG. Ini
dependency inti, tidak bisa diganti tanpa menulis ulang bagian
rendering.

### `contextily` (opsional)
Dipakai untuk mengambil ubin peta (basemap tile) dari penyedia publik
(default: CartoDB Positron) sebagai latar belakang peta. Ini satu-satunya
bagian dari script yang melakukan koneksi jaringan keluar untuk basemap —
dan itu pun hanya mengirim koordinat area yang sedang dilihat, **bukan**
isi `Timeline.json`. `contextily` menarik beberapa dependency Python
tambahan (`rasterio`, `geopy`, `mercantile`, `Pillow`, dll), yang paling
sering bikin instalasi ribet adalah **`rasterio`** — dijelaskan di bawah.

---

## GDAL (dependency sistem untuk `rasterio` → `contextily`)

**GDAL** (*Geospatial Data Abstraction Library*) adalah library standar
industri untuk membaca/menulis format data geospasial — peta raster
(gambar satelit, tile peta), data vektor (batas wilayah, garis jalan), dan
sejenisnya. Ini **bukan** package Python — ini library level sistem
operasi (mirip FFmpeg), yang harus terinstall duluan sebelum `pip` bisa
compile package Python yang bergantung padanya.

**Rantai dependency-nya:**

```
napaktilas.py
  └─ contextily        (basemap)
       └─ rasterio      (baca/tulis raster di Python)
            └─ GDAL     (library sistem, bukan package pip)
```

Kamu tidak pernah memanggil GDAL secara langsung — tapi `rasterio` (yang
dipakai `contextily`) butuh GDAL terinstall di sistem untuk bisa
di-compile/dipasang lewat `pip`. Kalau GDAL belum ada, `pip install
contextily` (atau `pip install rasterio`) akan gagal dengan error seperti:

```
A GDAL API version must be specified. Provide a path to gdal-config
using a GDAL_CONFIG environment variable or use a GDAL_VERSION
environment variable.
```

### Cara install GDAL

**Ubuntu/Debian**
```bash
sudo apt update && sudo apt install -y gdal-bin libgdal-dev build-essential python3-dev
export GDAL_CONFIG=$(which gdal-config)
pip3 install rasterio==$(gdal-config --version) --break-system-packages
pip3 install contextily --break-system-packages
```
Kalau versi `rasterio` yang persis cocok tidak ada di PyPI, coba versi
major.minor saja (misal `rasterio==3.6.*`). Alternatif yang sering lebih
gampang: pakai paket `rasterio` siap pakai dari `apt` alih-alih compile
sendiri lewat `pip`:
```bash
sudo apt install python3-rasterio
pip3 install contextily --break-system-packages
```

**macOS (Homebrew)**
```bash
brew install gdal
pip3 install rasterio
pip3 install contextily
```
macOS/Homebrew biasanya menyediakan wheel prebuilt untuk `rasterio`,
jadi umumnya tidak perlu mencocokkan versi seperti di Linux. Kalau
`pip3` menolak dengan pesan `externally-managed-environment`, tambahkan
`--break-system-packages`, atau lebih rapi pakai virtual environment:
```bash
python3 -m venv venv && source venv/bin/activate
pip install rasterio contextily
```

**Windows**
Cara termudah: install lewat [conda-forge](https://conda-forge.org/)
(binary GDAL untuk Windows lewat `pip` sering bermasalah):
```powershell
conda install -c conda-forge gdal rasterio contextily
```
Alternatif tanpa conda: unduh wheel `GDAL` dan `rasterio` yang sudah
di-compile untuk Windows dari
[Christoph Gohlke's unofficial wheels](https://www.lfd.uci.edu/~gohlke/pythonlibs/)
(cari `GDAL` dan `rasterio` sesuai versi Python kamu), lalu:
```powershell
pip install GDAL‑<versi>.whl
pip install rasterio‑<versi>.whl
pip install contextily
```

### Kenapa `brew install gdal` menarik puluhan dependency?

Mirip dengan FFmpeg (lihat bagian FFmpeg di bawah), GDAL adalah library
"serba bisa" yang mendukung puluhan format geospasial sekaligus — jadi
Homebrew menarik banyak library pendukung meski `napaktilas.py` cuma
butuh fungsi paling dasar (baca tile PNG/JPEG dari basemap). Contoh nyata
output `brew install gdal` (dry-run):

```
==> Would install 1 formula:
gdal
==> Would install 73 dependencies for gdal:
abseil, aws-c-common, aws-c-cal, aws-c-compression, s2n, aws-c-io,
aws-c-http, aws-c-sdkutils, aws-c-auth, aws-checksums, aws-c-event-stream,
aws-c-mqtt, aws-c-s3, aws-crt-cpp, aws-sdk-cpp, protobuf, re2, grpc,
llvm@22, thrift, utf8proc, apache-arrow, c-blosc, cfitsio, popt, epsilon,
minizip, freexl, geos, isl, mpfr, libmpc, gcc, libaec, pkgconf, hdf5,
json-c, proj, libgeotiff, libde265, libheif, uriparser, libkml, liblerc,
librttopo, libxml2, libspatialite, netcdf, libomp, openblas, numpy,
libgpg-error, libassuan, libgcrypt, libksba, libusb, npth, pinentry,
gnupg, gpgme, gpgmepp, nspr, nss, poppler, qhull, boost, eigen, cgal,
sfcgal, m4, libtool, unixodbc, xerces-c
==> Would upgrade 20 dependencies for gdal:
imath, jpeg-turbo, highway, libtiff, little-cms2, libdeflate, openjph,
openexr, jpeg-xl, libarchive, aom, libpq, fontconfig, glib, libtasn1,
nettle, p11-kit, gnutls, expat, python@3.14
```

Kenapa sebanyak ini? Beberapa contoh: dukungan baca format `NetCDF`/HDF5
(`hdf5`, `netcdf`) untuk data ilmiah/klimatologi, dukungan cloud storage
AWS S3 (`aws-c-*`, `aws-sdk-cpp`) untuk baca data geospasial langsung
dari cloud, dukungan format PDF (`poppler`) dan berbagai library
kompresi/kriptografi pendukung transitif. **Tidak satupun dari ini
dipakai `napaktilas.py`** — yang dipakai cuma kemampuan baca gambar tile
peta biasa (PNG/JPEG). Ini normal untuk build "penuh" dari package
manager, bukan tanda ada yang salah.

Kalau ukuran instalasi ini terasa berat dan kamu cuma butuh basemap
sesekali, ingat: **basemap sepenuhnya opsional**. Skip saja `contextily`
dan pakai `--labels coords` untuk label offline — video tetap jadi
normal, cuma tanpa gambar peta di latar belakang.

---

## 2. FFmpeg (binary eksternal, bukan package Python)

Script memanggil FFmpeg lewat `subprocess` (`frames_to_video()`) untuk
meng-encode kumpulan frame PNG menjadi satu file MP4 (codec `libx264`).
FFmpeg **tidak** diinstall lewat `pip` — harus diinstall terpisah di
level sistem operasi.

### Kenapa banyak dependency saat install?

Package manager (Homebrew, apt, dll) biasanya mendistribusikan build
FFmpeg "full/complete" yang mendukung puluhan format audio-video
sekaligus — bukan cuma yang dipakai script ini. Sebagai contoh, build
Homebrew menarik dependency seperti:

| Dependency     | Fungsi umum di FFmpeg              | Dipakai `napaktilas.py`? |
|-----------------|--------------------------------------|----------------------------|
| `sdl2`/`sdl3`   | Preview/playback window (`ffplay`)  | Tidak                      |
| `dav1d`         | Decoder codec video AV1              | Tidak                      |
| `svt-av1`       | Encoder codec video AV1              | Tidak                      |
| `libvpx`        | Codec video VP8/VP9                  | Tidak                      |
| `x265`          | Encoder codec video H.265/HEVC       | Tidak                      |
| `lame`, `mpg123`| Encode/decode MP3                    | Tidak                      |
| `opus`          | Codec audio Opus                     | Tidak                      |
| `libvmaf`       | Metrik kualitas video (VMAF)         | Tidak                      |

Script ini **hanya** memakai `libx264` (encoder H.264) dan `yuv420p`
sebagai pixel format — dua hal yang sudah termasuk default di hampir
semua distribusi FFmpeg. Dependency lain di atas ikut terinstall
sebagai bagian dari build lengkap, bukan karena dibutuhkan script ini.

### Cara install

**macOS (Homebrew)**
```bash
brew install ffmpeg
```

**Ubuntu/Debian**
```bash
sudo apt update && sudo apt install ffmpeg
```
Build FFmpeg dari repo apt Ubuntu/Debian umumnya sudah menyertakan
`libx264` secara default, dependency tambahannya jauh lebih ringan
dibanding build Homebrew.

**Windows**
Unduh build statis dari [ffmpeg.org/download.html](https://ffmpeg.org/download.html),
lalu tambahkan folder `bin/`-nya ke PATH sistem.

**Verifikasi instalasi**
```bash
ffmpeg -version
```
Script akan otomatis mengecek `ffmpeg` ada di PATH sebelum jalan
(lewat `shutil.which("ffmpeg")`), dan akan berhenti dengan pesan error
yang jelas kalau tidak ditemukan.

### Opsi instalasi lebih ringan (opsional)

Kalau ukuran instalasi jadi masalah, beberapa alternatif:

- **Homebrew**: gunakan formula pihak ketiga yang lebih minimal, atau
  build FFmpeg sendiri dari source dengan flag `--disable-everything
  --enable-encoder=libx264 --enable-decoder=png ...` (butuh waktu &
  familiar dengan `configure` FFmpeg).
- **Docker**: pakai image FFmpeg minimal seperti `jrottenberg/ffmpeg:alpine`
  yang buildnya jauh lebih kecil dari distribusi "full".
- **Linux**: banyak distro punya paket `ffmpeg-minimal` atau serupa di
  repository-nya — cek dengan `apt search ffmpeg` / package manager
  masing-masing distro.

Untuk kebanyakan pengguna, instalasi penuh via package manager standar
tetap cara paling praktis — ukuran ekstra (~100–300MB tergantung OS)
biasanya bukan masalah besar untuk pemakaian sekali/beberapa kali.

---

## 3. Ringkasan instalasi cepat

```bash
# 1. FFmpeg (wajib)
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Ubuntu/Debian
# atau unduh manual untuk Windows

# 2. GDAL + Python packages (contextily/GDAL/rasterio opsional, hanya untuk basemap)
sudo apt install -y gdal-bin libgdal-dev python3-rasterio   # Ubuntu/Debian
brew install gdal                                            # macOS

pip install -r requirements.txt
# kalau contextily gagal karena rasterio/GDAL, lihat bagian
# "GDAL (dependency sistem untuk rasterio -> contextily)" di atas,
# atau lewati saja contextily dan pakai --labels coords (100% offline)

# 3. Jalankan
python3 napaktilas.py Timeline.json --out perjalanan.mp4   # Linux/macOS
python napaktilas.py Timeline.json --out perjalanan.mp4    # Windows
```
