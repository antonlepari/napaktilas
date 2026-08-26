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
bagian dari script yang melakukan koneksi jaringan keluar — dan itu pun
hanya mengirim koordinat area yang sedang dilihat, **bukan** isi
`Timeline.json`. `contextily` sendiri menarik dependency tambahan
seperti `rasterio`, `geopy`, `mercantile`, dan `Pillow` di baliknya
(dikelola otomatis oleh `pip`, tidak perlu diinstall manual).

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
# 1. Python packages
pip install -r requirements.txt

# 2. FFmpeg
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Ubuntu/Debian
# atau unduh manual untuk Windows

# 3. Jalankan
python napaktilas.py Timeline.json --out perjalanan.mp4
```
