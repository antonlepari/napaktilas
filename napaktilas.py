#!/usr/bin/env python3
"""
napaktilas.py - Google Timeline Visualizer (Lokal & Privat)
=============================================
Mengubah data ekspor Google Maps Timeline (Timeline.json) menjadi video
perjalanan (MP4). Semua parsing & rendering dilakukan sepenuhnya di
komputer kamu sendiri -- file Timeline.json TIDAK PERNAH dikirim ke
server manapun.

Catatan privasi: ada dua fitur OPSIONAL yang melakukan koneksi jaringan
keluar (keduanya bisa dimatikan sepenuhnya):
  1. Basemap (`contextily`)   -> minta gambar peta ke CartoDB/OpenStreetMap.
     Hanya membocorkan area peta yang dilihat, BUKAN isi Timeline kamu.
  2. Label nama tempat (`--labels geocode`) -> minta nama tempat ke
     OpenStreetMap Nominatim berdasarkan koordinat titik kunjungan.
     Ini MENGIRIM koordinat kunjungan kamu (bukan seluruh file) ke
     Nominatim untuk diterjemahkan jadi nama tempat. Kalau tidak mau
     ada koneksi apapun, jangan pakai `--labels geocode` -- pakai
     `--labels coords` (nama tempat diganti teks koordinat, 100% offline)
     atau biarkan default (`--labels off`, tanpa label sama sekali).

Kebutuhan:
    pip install matplotlib contextily numpy

    FFmpeg juga harus terinstall & tersedia di PATH:
      - Ubuntu/Debian : sudo apt install ffmpeg
      - macOS         : brew install ffmpeg
      - Windows       : https://ffmpeg.org/download.html

Cara pakai:
    python napaktilas.py Timeline.json \
        --start 2024-01-01 --end 2024-12-31 \
        --out perjalanan_2024.mp4 --duration 20 --fps 24 \
        --labels geocode
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import contextily as cx
    HAS_CONTEXTILY = True
except ImportError:
    HAS_CONTEXTILY = False


# ---------------------------------------------------------------------------
# 1. PARSING Timeline.json
# ---------------------------------------------------------------------------
# Setiap titik disimpan sebagai (waktu, lat, lon, kind).
# kind: "visit"    -> titik kunjungan/berdiam (kandidat untuk label nama tempat)
#       "activity" -> titik awal/akhir perjalanan
#       "path"     -> titik detail rute (timelinePath)
#       "location" -> titik dari format lama Google Takeout

def parse_geo_string(s):
    """Parse string 'geo:lat,lng' menjadi tuple (lat, lng)."""
    if not isinstance(s, str) or not s.startswith("geo:"):
        return None
    try:
        lat_str, lng_str = s[4:].split(",")
        return float(lat_str), float(lng_str)
    except (ValueError, IndexError):
        return None


def parse_iso_time(s):
    """Parse timestamp ISO8601 menjadi objek datetime (UTC)."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def get_latlng(value):
    """
    Ambil (lat, lng) dari sebuah field yang bisa berupa string langsung
    ('geo:lat,lng') ATAU dict berisi key 'latLng'/'LatLng'. Google
    memakai kedua bentuk ini tergantung versi ekspor.
    """
    if isinstance(value, str):
        return parse_geo_string(value)
    if isinstance(value, dict):
        return parse_geo_string(value.get("latLng") or value.get("LatLng"))
    return None


def extract_points_from_segments(segments):
    """
    Ekstrak titik lokasi dari daftar 'segmen' timeline. Setiap segmen bisa
    berisi 'timelinePath', 'visit', atau 'activity'. Menangani dua variasi
    struktur yang ditemukan di berbagai versi ekspor Google Maps:
      - placeLocation / start / end sebagai string 'geo:lat,lng' langsung
      - placeLocation / start / end sebagai dict {'latLng': 'geo:lat,lng'}
    """
    points = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue

        for tp in seg.get("timelinePath", []):
            latlng = get_latlng(tp.get("point"))
            t = parse_iso_time(tp.get("time"))
            if latlng and t:
                points.append((t, latlng[0], latlng[1], "path"))

        visit = seg.get("visit")
        if visit:
            place = visit.get("topCandidate", {}).get("placeLocation")
            latlng = get_latlng(place)
            t = parse_iso_time(seg.get("startTime"))
            if latlng and t:
                points.append((t, latlng[0], latlng[1], "visit"))

        activity = seg.get("activity")
        if activity:
            start_ll = get_latlng(activity.get("start"))
            end_ll = get_latlng(activity.get("end"))
            t_start = parse_iso_time(seg.get("startTime"))
            t_end = parse_iso_time(seg.get("endTime"))
            if start_ll and t_start:
                points.append((t_start, start_ll[0], start_ll[1], "activity"))
            if end_ll and t_end:
                points.append((t_end, end_ll[0], end_ll[1], "activity"))

    return points


def extract_points_new_format(data):
    """
    Format baru ekspor Google Maps. Ada dua variasi bentuk file yang
    beredar:
      1. Root file langsung berupa array segmen: [ {...}, {...}, ... ]
      2. Root file berupa objek dengan key 'semanticSegments': [ ... ]
    Keduanya berisi struktur segmen yang sama di dalamnya.
    """
    if isinstance(data, list):
        points = extract_points_from_segments(data)
    else:
        points = extract_points_from_segments(data.get("semanticSegments", []))
        for raw in data.get("rawSignals", []):
            pos = raw.get("position")
            if pos:
                latlng = get_latlng(pos.get("LatLng") or pos.get("latLng"))
                t = parse_iso_time(pos.get("timestamp"))
                if latlng and t:
                    points.append((t, latlng[0], latlng[1], "path"))
    return points


def extract_points_old_format(data):
    """Format lama Google Takeout: {'locations': [{latitudeE7, longitudeE7, timestampMs}]}."""
    points = []
    for loc in data.get("locations", []):
        if "latitudeE7" in loc and "longitudeE7" in loc:
            lat = loc["latitudeE7"] / 1e7
            lng = loc["longitudeE7"] / 1e7
            ts_ms = loc.get("timestampMs")
            t = (
                datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc)
                if ts_ms else parse_iso_time(loc.get("timestamp"))
            )
            if t:
                points.append((t, lat, lng, "location"))
    return points


def load_timeline(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    points = []
    if isinstance(data, list):
        # Root file langsung berupa array segmen (format yang paling umum
        # ditemukan pada ekspor Google Maps Timeline terbaru).
        points = extract_points_new_format(data)
    elif "semanticSegments" in data or "rawSignals" in data:
        points = extract_points_new_format(data)
    if not points and isinstance(data, dict) and "locations" in data:
        points = extract_points_old_format(data)

    if not points:
        sys.exit(
            "Tidak ada titik lokasi ditemukan. Pastikan ini file ekspor resmi "
            "Google Maps Timeline (Profil > Setelan > Konten pribadi > "
            "Ekspor Data Linimasa), bukan file yang sudah diubah."
        )

    points.sort(key=lambda p: p[0])
    return points


# ---------------------------------------------------------------------------
# 2. FILTER OUTLIER GPS
# ---------------------------------------------------------------------------

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def filter_outliers(points, max_speed_kmh=1000):
    """Buang titik yang menyiratkan kecepatan mustahil dibanding titik sebelumnya."""
    if len(points) < 3:
        return points
    cleaned = [points[0]]
    for i in range(1, len(points)):
        t_prev, lat_prev, lon_prev = cleaned[-1][0], cleaned[-1][1], cleaned[-1][2]
        t_cur, lat_cur, lon_cur = points[i][0], points[i][1], points[i][2]
        dt_h = (t_cur - t_prev).total_seconds() / 3600
        if dt_h <= 0:
            # Waktu sama persis (atau mundur karena pembulatan) dengan titik
            # sebelumnya -- kecepatan tidak bisa dihitung, tapi titik ini
            # tetap valid (kasus umum: titik 'visit' dimulai persis saat
            # titik jalur sebelumnya berakhir). Jangan dibuang.
            cleaned.append(points[i])
            continue
        speed = haversine_km(lat_prev, lon_prev, lat_cur, lon_cur) / dt_h
        if speed <= max_speed_kmh:
            cleaned.append(points[i])
    return cleaned


# ---------------------------------------------------------------------------
# 3. INTERPOLASI UNTUK ANIMASI HALUS
# ---------------------------------------------------------------------------

def interpolate_points(points, target_fps, duration_sec):
    total_frames = max(int(target_fps * duration_sec), len(points))
    times = [p[0].timestamp() for p in points]
    lats = [p[1] for p in points]
    lons = [p[2] for p in points]

    t0, t1 = times[0], times[-1]
    if t1 == t0:
        t1 = t0 + 1

    frame_times = np.linspace(t0, t1, total_frames)
    frame_lats = np.interp(frame_times, times, lats)
    frame_lons = np.interp(frame_times, times, lons)
    return list(zip(frame_lats, frame_lons)), total_frames


# ---------------------------------------------------------------------------
# 4. LABEL NAMA TEMPAT (OPSIONAL)
# ---------------------------------------------------------------------------

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
# Nominatim MEWAJIBKAN User-Agent yang jelas mengidentifikasi aplikasi
# (bukan User-Agent generik/browser). Kalau kamu deploy/pakai script ini
# secara rutin, ganti dengan identitas & kontak kamu sendiri sesuai
# kebijakan Nominatim: https://operations.osmfoundation.org/policies/nominatim/
USER_AGENT = "napaktilas.py-personal-use (no-reply@example.com)"


def reverse_geocode(lat, lon, timeout=5):
    """
    Terjemahkan koordinat menjadi nama tempat via OpenStreetMap Nominatim.
    Mengirim HANYA koordinat titik ini ke Nominatim (bukan file Timeline
    kamu). Mengembalikan None kalau request gagal (offline, timeout, dll)
    -- pemanggil harus punya fallback.
    """
    params = urllib.parse.urlencode({
        "format": "jsonv2",
        "lat": f"{lat:.6f}",
        "lon": f"{lon:.6f}",
        "zoom": "16",
        "addressdetails": "1",
    })
    url = f"{NOMINATIM_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    if not data:
        return None

    if data.get("name"):
        return data["name"]

    addr = data.get("address", {})
    for key in ("suburb", "city", "town", "village", "county", "state"):
        if addr.get(key):
            return addr[key]

    display_name = data.get("display_name")
    if display_name:
        return display_name.split(",")[0]

    return None


def build_place_labels(points, mode, dedup_radius_km=0.3):
    """
    Bangun daftar label (lat, lon, teks) dari titik-titik ber-kind 'visit'.
    mode:
      "off"     -> list kosong, tidak ada label
      "coords"  -> teks = koordinat 'lat, lon' (100% offline)
      "geocode" -> teks = nama tempat asli via Nominatim (BUTUH INTERNET,
                   1 request/detik sesuai kebijakan rate-limit Nominatim)
    Titik-titik yang berdekatan (< dedup_radius_km) digabung jadi satu
    label supaya tidak spam permintaan/label untuk lokasi yang sama.
    """
    if mode == "off":
        return []

    visits = [p for p in points if p[3] == "visit"]
    if not visits:
        return []

    # Dedup: gabungkan titik kunjungan yang saling berdekatan
    unique_spots = []
    for _, lat, lon, _ in visits:
        merged = False
        for spot in unique_spots:
            if haversine_km(lat, lon, spot["lat"], spot["lon"]) < dedup_radius_km:
                merged = True
                break
        if not merged:
            unique_spots.append({"lat": lat, "lon": lon})

    labels = []
    if mode == "coords":
        for spot in unique_spots:
            text = f"{spot['lat']:.4f}, {spot['lon']:.4f}"
            labels.append((spot["lat"], spot["lon"], text))
        return labels

    if mode == "geocode":
        print(f"     Mencari nama tempat untuk {len(unique_spots)} lokasi kunjungan unik "
              f"via OpenStreetMap Nominatim (~{len(unique_spots)} detik, butuh internet) ...")
        for idx, spot in enumerate(unique_spots):
            name = reverse_geocode(spot["lat"], spot["lon"])
            if not name:
                name = f"{spot['lat']:.4f}, {spot['lon']:.4f}"  # fallback offline
            labels.append((spot["lat"], spot["lon"], name))
            print(f"       [{idx + 1}/{len(unique_spots)}] {name}")
            time.sleep(1.1)  # hormati rate-limit Nominatim (maks 1 request/detik)
        return labels

    return []


# ---------------------------------------------------------------------------
# 5. RENDER FRAME PETA
# ---------------------------------------------------------------------------

def render_frames(coords, out_dir, width_px=1280, height_px=720, labels=None):
    dpi = 100
    fig_w, fig_h = width_px / dpi, height_px / dpi
    labels = labels or []

    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    pad_lat = max((max(lats) - min(lats)) * 0.15, 0.01)
    pad_lon = max((max(lons) - min(lons)) * 0.15, 0.01)
    xlim = (min(lons) - pad_lon, max(lons) + pad_lon)
    ylim = (min(lats) - pad_lat, max(lats) + pad_lat)

    label_reveal_km = 0.3  # jarak dari jalur sebelum label dianggap "terlewati"

    for i, (lat, lon) in enumerate(coords):
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal")
        ax.axis("off")

        path_lons = lons[: i + 1]
        path_lats = lats[: i + 1]
        ax.plot(path_lons, path_lats, color="#ff5a36", linewidth=2, alpha=0.85, zorder=3)
        ax.scatter([lon], [lat], color="#ff5a36", s=60, zorder=4, edgecolors="white", linewidths=1.5)

        for lbl_lat, lbl_lon, text in labels:
            passed = any(
                haversine_km(lbl_lat, lbl_lon, plat, plon) < label_reveal_km
                for plat, plon in zip(path_lats, path_lons)
            )
            if not passed:
                continue
            ax.scatter([lbl_lon], [lbl_lat], color="#2b2b2b", s=20, zorder=2, edgecolors="none")
            ax.annotate(
                text, (lbl_lon, lbl_lat),
                textcoords="offset points", xytext=(6, 6),
                fontsize=9, fontweight="bold", color="#2b2b2b", zorder=5,
            )

        if HAS_CONTEXTILY:
            try:
                cx.add_basemap(ax, crs="EPSG:4326", source=cx.providers.CartoDB.Positron)
            except Exception:
                pass  # kalau tile gagal diambil (mis. offline), lanjut tanpa basemap

        fig.savefig(os.path.join(out_dir, f"frame_{i:05d}.png"), bbox_inches="tight", pad_inches=0)
        plt.close(fig)

        if i % 20 == 0 or i == len(coords) - 1:
            print(f"  Render frame {i + 1}/{len(coords)}")


# ---------------------------------------------------------------------------
# 6. GABUNGKAN FRAME -> MP4 (FFMPEG)
# ---------------------------------------------------------------------------

def frames_to_video(frame_dir, out_path, fps):
    if shutil.which("ffmpeg") is None:
        sys.exit("FFmpeg tidak ditemukan di sistem. Install dulu, lalu pastikan ada di PATH.")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", os.path.join(frame_dir, "frame_%05d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        out_path,
    ]
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Visualisasikan Google Timeline JSON menjadi video, 100% lokal.")
    ap.add_argument("timeline_json", help="Path ke file Timeline.json hasil ekspor Google Maps")
    ap.add_argument("--start", help="Tanggal mulai (YYYY-MM-DD)", default=None)
    ap.add_argument("--end", help="Tanggal akhir (YYYY-MM-DD)", default=None)
    ap.add_argument("--out", default="timeline_video.mp4", help="Nama file output MP4")
    ap.add_argument("--fps", type=int, default=24, help="Frame per detik video")
    ap.add_argument("--duration", type=float, default=15, help="Durasi video (detik)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--max-speed", type=float, default=1000, help="Batas kecepatan (km/jam) untuk filter outlier GPS")
    ap.add_argument("--keep-frames", action="store_true", help="Simpan folder frame PNG setelah selesai (untuk debug)")
    ap.add_argument(
        "--labels", choices=["off", "coords", "geocode"], default="off",
        help=(
            "off (default): tanpa label. "
            "coords: label koordinat lat/lon di titik kunjungan, 100%% offline. "
            "geocode: label nama tempat asli via OpenStreetMap Nominatim, BUTUH INTERNET "
            "(mengirim koordinat titik kunjungan ke Nominatim, ~1 detik per lokasi unik)."
        ),
    )
    args = ap.parse_args()

    print("1/5  Membaca Timeline.json ...")
    points = load_timeline(args.timeline_json)
    print(f"     {len(points)} titik lokasi ditemukan.")

    if args.start:
        d0 = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
        points = [p for p in points if p[0] >= d0]
    if args.end:
        d1 = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
        points = [p for p in points if p[0] <= d1]

    if len(points) < 2:
        sys.exit("Titik lokasi kurang dari 2 setelah filter tanggal. Cek rentang --start/--end.")

    print("2/5  Membuang outlier GPS ...")
    points = filter_outliers(points, max_speed_kmh=args.max_speed)
    print(f"     {len(points)} titik tersisa setelah filter.")

    labels = []
    if args.labels != "off":
        print(f"     Menyiapkan label tempat (mode: {args.labels}) ...")
        labels = build_place_labels(points, args.labels)
        print(f"     {len(labels)} label disiapkan.")

    print("3/5  Interpolasi untuk animasi halus ...")
    coords, total_frames = interpolate_points(points, args.fps, args.duration)
    print(f"     {total_frames} frame akan dirender.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_dir = "frames_output" if args.keep_frames else tmp_dir
        if args.keep_frames:
            if os.path.isdir(frame_dir):
                shutil.rmtree(frame_dir)  # bersihkan sisa frame dari run sebelumnya
            os.makedirs(frame_dir, exist_ok=True)

        print("4/5  Render frame peta ...")
        if not HAS_CONTEXTILY:
            print("     (contextily tidak terinstall -> render tanpa basemap, hanya jalur & titik)")
        render_frames(coords, frame_dir, args.width, args.height, labels=labels)

        print("5/5  Menggabungkan frame menjadi video (FFmpeg) ...")
        frames_to_video(frame_dir, args.out, args.fps)

    print(f"\nSelesai! Video tersimpan di: {args.out}")


if __name__ == "__main__":
    main()
