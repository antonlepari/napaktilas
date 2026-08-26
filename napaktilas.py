#!/usr/bin/env python3
"""
napaktilas.py - Google Timeline Visualizer (Lokal & Privat)
=============================================
Mengubah data ekspor Google Maps Timeline (Timeline.json) menjadi video
perjalanan (MP4). Semua parsing & rendering dilakukan sepenuhnya di
komputer kamu sendiri -- file Timeline.json TIDAK PERNAH dikirim ke
server manapun.

Catatan privasi: satu-satunya lalu lintas keluar (jika `contextily`
terinstall) adalah permintaan gambar peta dasar (basemap tile) ke
CartoDB/OpenStreetMap untuk menggambar latar peta -- ini hanya
mengungkap area peta yang sedang dilihat, BUKAN isi file Timeline
kamu. Kalau mau 100% offline (tanpa permintaan jaringan sama sekali),
jalankan tanpa `contextily` terinstall; video tetap dibuat, hanya
tanpa gambar peta di latar belakang.

Kebutuhan:
    pip install matplotlib contextily numpy

    FFmpeg juga harus terinstall & tersedia di PATH:
      - Ubuntu/Debian : sudo apt install ffmpeg
      - macOS         : brew install ffmpeg
      - Windows       : https://ffmpeg.org/download.html

Cara pakai:
    python napaktilas.py Timeline.json \
        --start 2024-01-01 --end 2024-12-31 \
        --out perjalanan_2024.mp4 --duration 20 --fps 24
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
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


def extract_points_new_format(data):
    """
    Format baru ekspor Google Maps app: 'semanticSegments' berisi
    'timelinePath', 'visit', 'activity', dan opsional 'rawSignals'
    terpisah di level atas.
    """
    points = []
    for seg in data.get("semanticSegments", []):
        for tp in seg.get("timelinePath", []):
            latlng = parse_geo_string(tp.get("point"))
            t = parse_iso_time(tp.get("time"))
            if latlng and t:
                points.append((t, latlng[0], latlng[1]))

        visit = seg.get("visit")
        if visit:
            place = visit.get("topCandidate", {}).get("placeLocation", {})
            latlng = parse_geo_string(place.get("latLng"))
            t = parse_iso_time(seg.get("startTime"))
            if latlng and t:
                points.append((t, latlng[0], latlng[1]))

        activity = seg.get("activity")
        if activity:
            start_ll = parse_geo_string(activity.get("start", {}).get("latLng"))
            end_ll = parse_geo_string(activity.get("end", {}).get("latLng"))
            t_start = parse_iso_time(seg.get("startTime"))
            t_end = parse_iso_time(seg.get("endTime"))
            if start_ll and t_start:
                points.append((t_start, start_ll[0], start_ll[1]))
            if end_ll and t_end:
                points.append((t_end, end_ll[0], end_ll[1]))

    for raw in data.get("rawSignals", []):
        pos = raw.get("position")
        if pos:
            latlng = parse_geo_string(pos.get("LatLng") or pos.get("latLng"))
            t = parse_iso_time(pos.get("timestamp"))
            if latlng and t:
                points.append((t, latlng[0], latlng[1]))

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
                points.append((t, lat, lng))
    return points


def load_timeline(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    points = []
    if "semanticSegments" in data or "rawSignals" in data:
        points = extract_points_new_format(data)
    if not points and "locations" in data:
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
        t_prev, lat_prev, lon_prev = cleaned[-1]
        t_cur, lat_cur, lon_cur = points[i]
        dt_h = (t_cur - t_prev).total_seconds() / 3600
        if dt_h <= 0:
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
# 4. RENDER FRAME PETA
# ---------------------------------------------------------------------------

def render_frames(coords, out_dir, width_px=1280, height_px=720):
    dpi = 100
    fig_w, fig_h = width_px / dpi, height_px / dpi

    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    pad_lat = max((max(lats) - min(lats)) * 0.15, 0.01)
    pad_lon = max((max(lons) - min(lons)) * 0.15, 0.01)
    xlim = (min(lons) - pad_lon, max(lons) + pad_lon)
    ylim = (min(lats) - pad_lat, max(lats) + pad_lat)

    for i, (lat, lon) in enumerate(coords):
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal")
        ax.axis("off")

        ax.plot(lons[: i + 1], lats[: i + 1], color="#ff5a36", linewidth=2, alpha=0.85, zorder=3)
        ax.scatter([lon], [lat], color="#ff5a36", s=60, zorder=4, edgecolors="white", linewidths=1.5)

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
# 5. GABUNGKAN FRAME -> MP4 (FFMPEG)
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

    print("3/5  Interpolasi untuk animasi halus ...")
    coords, total_frames = interpolate_points(points, args.fps, args.duration)
    print(f"     {total_frames} frame akan dirender.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_dir = "frames_output" if args.keep_frames else tmp_dir
        if args.keep_frames:
            os.makedirs(frame_dir, exist_ok=True)

        print("4/5  Render frame peta ...")
        if not HAS_CONTEXTILY:
            print("     (contextily tidak terinstall -> render tanpa basemap, hanya jalur & titik)")
        render_frames(coords, frame_dir, args.width, args.height)

        print("5/5  Menggabungkan frame menjadi video (FFmpeg) ...")
        frames_to_video(frame_dir, args.out, args.fps)

    print(f"\nSelesai! Video tersimpan di: {args.out}")


if __name__ == "__main__":
    main()
