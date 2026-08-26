# Google Timeline Visualizer (Lokal & Privat)

Script Python untuk mengubah data ekspor Google Maps Timeline (`Timeline.json`)
menjadi video perjalanan (MP4) — **tanpa mengunggah data ke server manapun**.
Semua parsing JSON dan rendering peta dilakukan di komputer kamu sendiri.

## Privasi
Satu-satunya lalu lintas jaringan (jika `contextily` terinstall) adalah
permintaan gambar peta dasar (basemap tile) dari CartoDB/OpenStreetMap untuk
menggambar latar peta. Ini hanya membocorkan **area peta yang dilihat**,
bukan isi `Timeline.json` kamu. Kalau mau benar-benar 0 koneksi keluar,
jangan install `contextily` — video tetap dibuat, hanya tanpa gambar peta
di belakang jalur/rute (garis & titik tetap tampil di kanvas polos).

## 1. Ekspor data Timeline kamu

- **iPhone**: Google Maps → foto profil → Setelan → Konten pribadi →
  Ekspor Data Linimasa → simpan `Timeline.json` di app Files.
- **Android**: Google Maps → Setelan → Lokasi → Layanan Lokasi → Linimasa →
  Ekspor Data Linimasa.

## 2. Install dependensi

```bash
pip install -r requirements.txt
```

Install juga FFmpeg (wajib):

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows: unduh dari https://ffmpeg.org/download.html
```

## 3. Jalankan

```bash
python napaktilas.py Timeline.json \
    --start 2024-01-01 --end 2024-12-31 \
    --out perjalanan_2024.mp4 \
    --duration 20 --fps 24
```

## Opsi yang tersedia

| Flag           | Default              | Keterangan                                    |
|----------------|----------------------|------------------------------------------------|
| `--start`      | (semua data)         | Tanggal mulai, format `YYYY-MM-DD`             |
| `--end`        | (semua data)         | Tanggal akhir, format `YYYY-MM-DD`             |
| `--out`        | `timeline_video.mp4` | Nama file video output                         |
| `--fps`        | `24`                 | Frame per detik                                |
| `--duration`   | `15`                 | Durasi video (detik)                           |
| `--width`      | `1280`               | Lebar video (px)                               |
| `--height`     | `720`                | Tinggi video (px)                              |
| `--max-speed`  | `1000`                | Ambang kecepatan (km/jam) untuk buang outlier GPS |
| `--keep-frames`| off                  | Simpan folder `frames_output/` berisi tiap PNG |

## Cara kerja singkat

1. **Parsing** — membaca `semanticSegments` (`timelinePath`, `visit`,
   `activity`) dari format ekspor terbaru, atau `locations[]` dari format
   Google Takeout lama.
2. **Filter outlier** — titik yang menyiratkan kecepatan mustahil (misal
   lompat benua dalam hitungan detik) dibuang.
3. **Interpolasi** — titik-titik disebar merata sepanjang durasi video
   berdasarkan waktu asli, supaya kamera bergerak halus.
4. **Render frame** — tiap frame digambar dengan `matplotlib` (+ basemap
   opsional dari `contextily`).
5. **Encode video** — semua frame PNG digabung jadi MP4 lewat FFmpeg.

## Kustomisasi lanjutan

Beberapa hal yang gampang diubah langsung di `napaktilas.py`:

- Warna jalur/titik: cari `"#ff5a36"` di fungsi `render_frames`.
- Basemap: ganti `cx.providers.CartoDB.Positron` dengan provider lain,
  misal `cx.providers.OpenStreetMap.Mapnik`.
- Style titik kunjungan vs. titik jalur bisa dibedakan dengan menambah
  marker khusus untuk entri `visit` di `extract_points_new_format`.
