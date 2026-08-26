# napaktilas.py — Google Timeline Visualizer (Lokal & Privat)

Script Python untuk mengubah data ekspor Google Maps Timeline (`Timeline.json`)
menjadi video perjalanan (MP4) — **tanpa mengunggah data ke server manapun**.
Semua parsing JSON dan rendering peta dilakukan di komputer kamu sendiri.

## Preview

![Preview animasi](preview.gif)

> Ketiga file preview di atas dirender dari **data rute sintetis**
> (Jakarta → Bandung → Yogyakarta → Surabaya, bukan data lokasi milik siapa
> pun) sebagai contoh, dan dirender **tanpa basemap** karena environment yang
> dipakai untuk generate demo ini tidak punya akses ke server tile peta.

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
