# FAQ & Troubleshooting

## Umum

### Apakah data lokasi saya dikirim ke server manapun?
Tidak. `napaktilas.py` membaca dan memproses `Timeline.json` sepenuhnya di
komputer kamu. Satu-satunya koneksi jaringan keluar (opsional) adalah
permintaan gambar basemap ke CartoDB/OpenStreetMap lewat `contextily` —
itu pun cuma mengirim koordinat area peta yang sedang digambar, bukan isi
file `Timeline.json` kamu. Lihat [DEPENDENCIES.md](DEPENDENCIES.md) untuk
rincian tiap dependency.

### Dari mana saya dapat `Timeline.json`?
- **iPhone**: Google Maps → foto profil → Setelan → Konten pribadi →
  Ekspor Data Linimasa.
- **Android**: Google Maps → Setelan → Lokasi → Layanan Lokasi → Linimasa →
  Ekspor Data Linimasa.
- Lihat juga bagian [Format Timeline.json yang didukung](README.md#format-timelinejson-yang-didukung)
  di README untuk contoh isi file.

### Kenapa videonya tidak ada gambar peta di latar belakang?
Ada dua kemungkinan:
1. Package `contextily` belum terinstall (`pip install contextily`).
2. Komputer kamu tidak ada koneksi internet saat render (basemap butuh
   internet untuk unduh tile peta).

Video tetap akan dibuat, hanya tanpa gambar peta — garis rute & titik lokasi
tetap tampil normal di kanvas polos.

---

## Error yang sering muncul

### `Tidak ada titik lokasi ditemukan. Pastikan ini file ekspor resmi...`
Penyebab paling umum:
- File JSON bukan hasil ekspor resmi Google Maps Timeline (sudah diubah,
  digabung manual, atau formatnya beda dari yang didukung).
- Struktur file berubah lagi di versi ekspor terbaru Google (Google beberapa
  kali mengubah struktur ini). Cek bagian
  [Format Timeline.json yang didukung](README.md#format-timelinejson-yang-didukung)
  di README, bandingkan dengan isi file kamu.
- File kosong / rentang `--start`/`--end` tidak mencakup data yang ada.

**Cara cek cepat:**
```bash
python3 -c "import json; d = json.load(open('Timeline.json')); print(type(d), len(d) if isinstance(d, list) else list(d.keys()))"
```
Kalau hasilnya `<class 'list'> 0` atau `<class 'dict'> []`, filenya memang
kosong/tidak berisi data. Kalau ada data tapi script tetap gagal, kemungkinan
besar strukturnya beda dari yang didukung — silakan buka issue di repo ini
dengan contoh 1-2 entri JSON (hapus/samarkan koordinat asli kalau mau jaga
privasi, cukup ganti angkanya, strukturnya yang penting).

### `Titik lokasi kurang dari 2 setelah difilter tanggal. Cek rentang --start/--end.`
Rentang tanggal `--start`/`--end` yang kamu isi tidak ada datanya. Cek ulang
tanggal, atau jalankan tanpa `--start`/`--end` dulu untuk lihat rentang data
yang sebenarnya tersedia.

### `FFmpeg tidak ditemukan di sistem. Install dulu, lalu pastikan ada di PATH.`
FFmpeg belum terinstall atau tidak ada di `PATH`. Lihat panduan instalasi di
[DEPENDENCIES.md](DEPENDENCIES.md#2-ffmpeg-binary-eksternal-bukan-package-python).
Setelah install, cek dengan:
```bash
ffmpeg -version
```
Kalau command itu sendiri gagal ("command not found"), FFmpeg belum ada di
PATH — biasanya berarti perlu buka terminal baru setelah instalasi, atau
tambahkan folder `bin` FFmpeg ke PATH secara manual (khususnya di Windows).

### `Matplotlib is building the font cache; this may take a moment.`
Ini **bukan error** — cuma pesan satu kali dari matplotlib saat pertama kali
dipakai di sistem (membangun cache font). Tunggu saja, prosesnya lanjut
otomatis setelah itu. Di run berikutnya pesan ini tidak akan muncul lagi.

### `ModuleNotFoundError: No module named 'matplotlib'` (atau `numpy`, `contextily`)
Dependency Python belum terinstall. Jalankan:
```bash
pip install -r requirements.txt
```
Kalau masih gagal, cek kamu memakai `pip`/`python` dari environment yang
sama (terutama kalau pakai virtualenv/conda — pastikan environment-nya
aktif sebelum install & run).

### Instalasi FFmpeg lewat Homebrew menarik banyak dependency (`svt-av1`, `x265`, `sdl3`, dll)
Ini normal — build FFmpeg "penuh" dari Homebrew mendukung banyak codec
sekaligus, sebagian besar tidak dipakai script ini (yang dipakai cuma
`libx264`). Bukan error, aman dilanjutkan. Detail lengkap ada di
[DEPENDENCIES.md](DEPENDENCIES.md#kenapa-banyak-dependency-saat-install).

### `contextily` gagal diinstall / error saat `pip install`
`contextily` menarik dependency seperti `rasterio` yang kadang butuh library
sistem tambahan (GDAL) di sebagian OS. Kalau cuma butuh fungsi dasar
(video tanpa basemap), lewati saja `contextily` — hapus barisnya dari
`requirements.txt` atau jalankan `pip install numpy matplotlib` saja.
Script otomatis mendeteksi kalau `contextily` tidak ada dan lanjut tanpa
basemap.

### `A GDAL API version must be specified...` / error rasterio saat install contextily
Artinya library sistem **GDAL** belum terinstall — `rasterio` (dependency
`contextily`) butuh GDAL untuk bisa di-compile lewat `pip`. Ini bukan
package Python, jadi tidak cukup diinstall lewat `pip` saja. Cara install:

```bash
# Ubuntu/Debian
sudo apt install -y gdal-bin libgdal-dev
export GDAL_CONFIG=$(which gdal-config)
pip3 install rasterio==$(gdal-config --version) --break-system-packages
pip3 install contextily --break-system-packages
# atau lebih gampang: sudo apt install python3-rasterio, lalu pip3 install contextily

# macOS
brew install gdal
pip3 install rasterio contextily
```

Penjelasan lengkap apa itu GDAL dan kenapa dibutuhkan ada di
[DEPENDENCIES.md](DEPENDENCIES.md#gdal-dependency-sistem-untuk-rasterio--contextily).
Kalau malas ribet install GDAL, lewati saja `contextily` — pakai
`--labels coords` untuk label offline, video tetap jadi normal tanpa
gambar peta di latar belakang.

### `brew install gdal` menarik puluhan dependency (`aws-c-*`, `hdf5`, `poppler`, dll)
Normal — build GDAL "penuh" dari Homebrew mendukung puluhan format
geospasial sekaligus (termasuk baca data dari cloud AWS S3, format
ilmiah NetCDF/HDF5, PDF, dll), padahal `napaktilas.py` cuma butuh
kemampuan baca gambar tile PNG/JPEG biasa untuk basemap. Bukan tanda
ada yang salah — lihat contoh lengkap output-nya dan alasannya di
[DEPENDENCIES.md](DEPENDENCIES.md#kenapa-brew-install-gdal-menarik-puluhan-dependency).

### Video hasil akhir kosong / berdurasi 0 detik / tidak bisa diputar
Biasanya berarti frame PNG gagal dibuat (misalnya semua titik lokasi sama
persis sehingga area peta 0). Jalankan dengan `--keep-frames` untuk cek isi
folder `frames_output/` secara manual — kalau folder itu kosong atau
gambar-gambarnya aneh, kemungkinan besar data lokasinya bermasalah
(misalnya cuma 1 titik unik di seluruh rentang tanggal yang dipilih).

### Rendering terasa sangat lambat untuk data besar
`Timeline.json` bertahun-tahun bisa berisi puluhan ribu titik. Beberapa cara
mempercepat:
- Persempit dulu pakai `--start`/`--end` (misalnya per tahun/bulan).
- Turunkan `--fps` dan `--duration` supaya jumlah frame yang dirender
  lebih sedikit.
- Nonaktifkan basemap (uninstall/skip `contextily`) — permintaan tile
  jaringan per frame adalah bagian paling lambat kalau internet lambat.

### Peta/basemap terlihat kosong/putih meski `contextily` terinstall
Kemungkinan tidak ada koneksi internet saat render, atau tile server sedang
tidak bisa diakses. Script akan otomatis melanjutkan render tanpa basemap
kalau pengambilan tile gagal (tidak crash), jadi videonya tetap jadi —
cuma tanpa gambar peta.

### Tidak ada nama tempat di video, cuma garis rute
Ini sesuai desain default (`--labels off`). Data Timeline asli dari Google
tidak menyertakan nama tempat yang bisa dibaca manusia, cuma koordinat.
Pakai `--labels coords` (offline, tampilkan koordinat) atau
`--labels geocode` (butuh internet, tampilkan nama tempat asli via
OpenStreetMap Nominatim). Detail lengkap ada di bagian
[Label nama tempat](README.md#label-nama-tempat---labels) di README.

### `--labels geocode` hasilnya cuma angka koordinat, bukan nama tempat
Berarti request ke Nominatim gagal (offline, timeout, atau server sedang
sibuk) — script otomatis fallback ke teks koordinat supaya tidak crash.
Cek koneksi internet kamu, lalu coba lagi. Kalau baru sebagian titik yang
gagal (bukan semua), kemungkinan kena rate-limit sesaat — tunggu beberapa
menit lalu ulangi.

### `--labels geocode` terasa lama / macam ngegantung
Normal — script sengaja menunggu ±1 detik antar request untuk menghormati
kebijakan rate-limit Nominatim (maksimal 1 request/detik). Kalau titik
kunjungan unik kamu ada 50, prosesnya akan makan waktu sekitar 50 detik.
Progress-nya ditampilkan di terminal (`[1/50] ...`, `[2/50] ...`, dst) —
kalau tidak ada progress sama sekali setelah lama, kemungkinan koneksi
internet kamu bermasalah/timeout (coba `Ctrl+C` dan cek koneksi).

### Folder `frames_output/` berisi frame lebih banyak dari yang saya harapkan / video hasil `--keep-frames` aneh
Kalau kamu render ulang dengan `--keep-frames` ke folder yang sama, versi
terbaru script sudah otomatis membersihkan folder `frames_output/` sebelum
render baru. Kalau masih memakai versi lama, hapus manual dulu foldernya
(`rm -rf frames_output`) sebelum render ulang, supaya frame dari run
sebelumnya tidak ikut tercampur ke video baru.

---

Masih ada masalah lain yang belum tercantum di sini? Silakan buka issue di
repo ini dengan menyertakan pesan error lengkap dan (kalau memungkinkan)
contoh struktur JSON yang menyebabkan masalah.
