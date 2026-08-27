# napaktilas.py — Google Timeline Visualizer (Lokal & Privat)

Script Python untuk mengubah data ekspor Google Maps Timeline (`Timeline.json`)
menjadi video perjalanan (MP4) — **tanpa mengunggah data ke server manapun**.
Semua parsing JSON dan rendering peta dilakukan di komputer kamu sendiri.

## Preview

![Preview animasi](preview.gif)

## Privasi
Ada dua fitur **opsional** yang melakukan koneksi jaringan keluar — keduanya
bisa dimatikan sepenuhnya:

1. **Basemap** (kalau `contextily` terinstall) — minta gambar peta dasar
   (tile) dari CartoDB/OpenStreetMap. Hanya membocorkan **area peta yang
   dilihat**, bukan isi `Timeline.json` kamu.
2. **Label nama tempat** (`--labels geocode`) — mengirim **koordinat titik
   kunjungan** kamu ke OpenStreetMap Nominatim untuk diterjemahkan jadi
   nama tempat. Lihat [bagian Label nama tempat](#label-nama-tempat---labels)
   untuk detail.

Kalau mau benar-benar **0 koneksi keluar**: jangan install `contextily`,
dan jangan pakai `--labels geocode` (pakai `--labels coords` atau biarkan
default `--labels off`). Video tetap dibuat sepenuhnya — hanya tanpa
gambar peta dan/atau tanpa label nama tempat.

## 1. Ekspor data Timeline kamu

- **iPhone**: Google Maps → foto profil → Setelan → Konten pribadi →
  Ekspor Data Linimasa → simpan `Timeline.json` di app Files.
- **Android**: Google Maps → Setelan → Lokasi → Layanan Lokasi → Linimasa →
  Ekspor Data Linimasa.

## 2. Install dependensi

**Linux / macOS**
```bash
pip3 install -r requirements.txt
```

**Windows**
```powershell
pip install -r requirements.txt
```

Install juga FFmpeg (wajib):

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows: unduh dari https://ffmpeg.org/download.html
# lalu tambahkan folder bin/ hasil ekstrak ke PATH sistem
```

> **Soal `contextily` gagal install (error GDAL/rasterio)**: ini paling
> sering kejadian dan disebabkan oleh library sistem **GDAL** yang belum
> terinstall (dibutuhkan `rasterio`, dependency `contextily`). Cara
> install GDAL per OS, penjelasan lengkap apa itu GDAL, dan kenapa
> `brew install gdal`/`apt install gdal` bisa menarik puluhan dependency
> lain, ada di [DEPENDENCIES.md](DEPENDENCIES.md#gdal-dependency-sistem-untuk-rasterio--contextily).
> Kalau males ribet, `contextily` boleh dilewati — video tetap jadi
> normal, cuma tanpa gambar peta (pakai `--labels coords` untuk label
> offline sebagai gantinya).

## 3. Jalankan

Command dasar (paling sederhana, semua opsi default):

**Linux / macOS**
```bash
python3 napaktilas.py Timeline.json
```

**Windows** (Command Prompt atau PowerShell)
```powershell
python napaktilas.py Timeline.json
```

> Di Linux/macOS, `python` kadang mengarah ke Python 2 (atau tidak ada sama
> sekali) — pakai `python3` untuk memastikan Python 3 yang jalan. Di
> Windows, installer resmi Python biasanya hanya menyediakan command
> `python`, jadi pakai itu (`py` juga bisa dipakai sebagai alternatif:
> `py napaktilas.py Timeline.json`).

### Contoh lengkap dengan opsi

Filter rentang tanggal, atur durasi/fps, dan aktifkan label nama tempat
(reverse-geocoding, butuh internet):

**Linux / macOS**
```bash
python3 napaktilas.py Timeline.json \
    --start 2024-01-01 --end 2024-12-31 \
    --out perjalanan_2024.mp4 \
    --duration 20 --fps 24 \
    --labels geocode
```

**Windows (PowerShell)**
```powershell
python napaktilas.py Timeline.json `
    --start 2024-01-01 --end 2024-12-31 `
    --out perjalanan_2024.mp4 `
    --duration 20 --fps 24 `
    --labels geocode
```

**Windows (Command Prompt / cmd.exe)**
```bat
python napaktilas.py Timeline.json ^
    --start 2024-01-01 --end 2024-12-31 ^
    --out perjalanan_2024.mp4 ^
    --duration 20 --fps 24 ^
    --labels geocode
```

> Perhatikan karakter penyambung baris beda tiap shell: `\` di
> bash/zsh (Linux/macOS), `` ` `` (backtick) di PowerShell, `^` di
> Command Prompt. Kalau bingung, tulis saja semua opsi dalam satu baris
> panjang — hasilnya sama:
> ```
> python3 napaktilas.py Timeline.json --start 2024-01-01 --end 2024-12-31 --out perjalanan_2024.mp4 --duration 20 --fps 24 --labels geocode
> ```

### Contoh lain yang umum dipakai

```bash
# Video pendek & cepat untuk preview/testing (durasi 5 detik, fps rendah)
python3 napaktilas.py Timeline.json --out preview.mp4 --duration 5 --fps 10

# Hanya rute bulan tertentu, label koordinat offline (tanpa internet sama sekali)
python3 napaktilas.py Timeline.json --start 2024-06-01 --end 2024-06-30 \
    --out juni_2024.mp4 --labels coords

# Resolusi lebih tinggi untuk diunggah ke YouTube/Instagram
python3 napaktilas.py Timeline.json --out hasil_hd.mp4 --width 1920 --height 1080

# Simpan frame PNG untuk dicek manual / debug
python3 napaktilas.py Timeline.json --out video.mp4 --keep-frames
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
| `--labels`     | `off`                | Label nama tempat: `off` / `coords` / `geocode` (lihat bawah) |

## Label nama tempat (`--labels`)

Data `Timeline.json` asli dari Google **tidak menyertakan nama tempat**
yang bisa dibaca manusia — cuma `placeID` internal Google dan koordinat.
Ada 3 pilihan:

| Mode       | Butuh internet? | Hasil label                                  |
|------------|:----------------:|-----------------------------------------------|
| `off` (default) | Tidak       | Tanpa label sama sekali                        |
| `coords`   | **Tidak**         | Teks koordinat `lat, lon` di tiap titik kunjungan |
| `geocode`  | **Ya**            | Nama tempat asli, hasil reverse-geocoding via [OpenStreetMap Nominatim](https://nominatim.org/) |

**Linux / macOS**
```bash
# Tanpa label (default)
python3 napaktilas.py Timeline.json --out video.mp4

# Label koordinat, 100% offline
python3 napaktilas.py Timeline.json --out video.mp4 --labels coords

# Label nama tempat asli, butuh internet
python3 napaktilas.py Timeline.json --out video.mp4 --labels geocode
```

**Windows**
```powershell
python napaktilas.py Timeline.json --out video.mp4
python napaktilas.py Timeline.json --out video.mp4 --labels coords
python napaktilas.py Timeline.json --out video.mp4 --labels geocode
```

**Catatan penting soal `--labels geocode`:**
- Mengirim **koordinat titik kunjungan** kamu (bukan seluruh file
  `Timeline.json`) ke server Nominatim (OpenStreetMap) untuk diterjemahkan
  jadi nama tempat. Kalau kamu tidak mau ada koneksi keluar sama sekali,
  pakai `coords` atau `off`.
- Nominatim membatasi maksimal 1 request/detik dan **mewajibkan**
  `User-Agent` yang mengidentifikasi aplikasi dengan jelas (lihat
  [kebijakan Nominatim](https://operations.osmfoundation.org/policies/nominatim/)).
  Script ini sudah menyertakan `User-Agent` bawaan untuk pemakaian
  personal — kalau kamu pakai script ini secara rutin/otomatis atau
  redistribusi, ganti `USER_AGENT` di `napaktilas.py` dengan identitas &
  kontak kamu sendiri.
- Titik kunjungan yang berdekatan (< 300 meter) otomatis digabung jadi
  satu label, supaya tidak spam request untuk lokasi yang sama.
- Untuk Timeline dengan banyak titik kunjungan unik, proses ini bisa makan
  waktu (kira-kira 1 detik per lokasi unik).

## Format Timeline.json yang didukung

Google mengubah struktur file ekspor Timeline dari waktu ke waktu. Script ini
sudah dites kompatibel dengan varian berikut:

- **Root berupa array langsung** — `[ {startTime, endTime, visit|activity|timelinePath}, ... ]`
  (bentuk paling umum di ekspor terbaru dari HP)
- **Root berupa objek** — `{"semanticSegments": [...]}`
- **Format lama Google Takeout** — `{"locations": [{latitudeE7, longitudeE7, timestampMs}]}`

Di dalam tiap segmen, field koordinat (`placeLocation`, `start`, `end`, `point`)
juga bisa berupa string `"geo:lat,lng"` langsung atau dibungkus
`{"latLng": "geo:lat,lng"}` — keduanya otomatis dikenali.

### Contoh isi file (dengan penjelasan)

Ini contoh nyata satu blok segmen `visit` dan satu blok `activity` dari
ekspor Google Maps Timeline (format root-array, paling umum saat ini):

```jsonc
[
  {
    // "visit" = kamu berdiam di satu lokasi dalam rentang waktu ini
    "startTime": "2025-01-28T19:00:00.000+07:00",
    "endTime":   "2025-01-28T21:22:22.736+07:00",
    "visit": {
      "topCandidate": {
        "placeID": "ChIJ7z5zMFXsaS4Ruzprvnp9-dc",     // ID lokasi internal Google
        "placeLocation": "geo:-6.339292,106.862077",   // <-- koordinat yang dipakai script
        "semanticType": "Unknown"
      },
      "probability": "0.000000"                        // keyakinan Google atas titik ini (diabaikan script)
    }
  },
  {
    // "activity" = kamu sedang berpindah tempat (jalan kaki, mobil, dst)
    "startTime": "2025-01-28T21:22:22.019+07:00",
    "endTime":   "2025-01-29T01:06:49.489+07:00",
    "activity": {
      "start": "geo:-6.339306,106.861622",   // <-- titik awal perjalanan
      "end":   "geo:-6.303820,106.820600",   // <-- titik akhir perjalanan
      "distanceMeters": "6010.298340",
      "topCandidate": { "type": "in passenger vehicle", "probability": "0.439638" }
    }
  }
]
```

**Field yang benar-benar dipakai script:**

| Field                                  | Dipakai untuk                          |
|------------------------------------------|-------------------------------------------|
| `startTime`, `endTime`                    | Waktu tiap titik (dipakai untuk urutan & interpolasi) |
| `visit.topCandidate.placeLocation`        | Koordinat tempat kamu berdiam              |
| `activity.start`, `activity.end`          | Koordinat awal & akhir perjalanan          |
| `timelinePath[].point`, `timelinePath[].time` | Titik-titik rute detail (kalau ada di segmen) |

Field lain (`placeID`, `probability`, `distanceMeters`, `hierarchyLevel`,
`semanticType`, dll.) **diabaikan** — bukan berarti error kalau ada/tidak ada,
script memang tidak membutuhkannya.

Kalau suatu saat Google ubah lagi strukturnya dan script gagal menemukan titik
lokasi, cara paling cepat mendiagnosis: buka file JSON kamu, cari satu entri
`visit` atau `activity`, lalu bandingkan strukturnya dengan yang dijelaskan
di atas — biasanya cuma perlu sesuaikan fungsi `extract_points_from_segments()`
di `napaktilas.py`.

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

## FAQ & Troubleshooting

Ada FAQ lengkap dan daftar error umum (beserta cara mengatasinya) di
[FAQ.md](FAQ.md) — termasuk soal `Timeline.json` tidak terbaca, FFmpeg tidak
ditemukan, basemap tidak muncul, dan lainnya.

## Kustomisasi lanjutan

Beberapa hal yang gampang diubah langsung di `napaktilas.py`:

- Warna jalur/titik: cari `"#ff5a36"` di fungsi `render_frames`.
- Basemap: ganti `cx.providers.CartoDB.Positron` dengan provider lain,
  misal `cx.providers.OpenStreetMap.Mapnik`.
- Style titik kunjungan vs. titik jalur bisa dibedakan dengan menambah
  marker khusus untuk entri `visit` di `extract_points_new_format`.
