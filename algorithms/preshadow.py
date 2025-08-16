# -*- coding: utf-8 -*-
# algorithms/preshadow.py

import math
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List

import cv2
import numpy as np
from PIL import Image, ExifTags


# ---------------- EXIF / dátum / deklináció ----------------

def _read_exif(image_path: str) -> Dict[str, Any]:
    try:
        img = Image.open(image_path)
        raw = img._getexif() or {}
        exif = {ExifTags.TAGS.get(k, k): v for k, v in raw.items()}
        return exif
    except Exception:
        return {}


def extract_datetime_utc(image_path: str) -> Optional[datetime]:
    """
    EXIF DateTimeOriginal -> UTC-nek tekintjük, ha nincs zóna.
    Ha nincs EXIF, fájl módosítási idejével próbálkozunk.
    """
    exif = _read_exif(image_path)
    dt_str = exif.get("DateTimeOriginal") or exif.get("DateTime")
    if dt_str:
        # Formátum tipikusan: 'YYYY:MM:DD HH:MM:SS'
        try:
            naive = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
            return naive.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    try:
        ts = os.path.getmtime(image_path)
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:
        return None


def solar_declination_rad(dt_utc: datetime) -> Optional[float]:
    """
    Nap deklinációja radiánban (Spencer-féle közelítés).
    """
    if dt_utc is None:
        return None
    n = dt_utc.timetuple().tm_yday
    B = 2.0 * math.pi * (n - 1) / 365.0
    δ = (0.006918
         - 0.399912 * math.cos(B)
         + 0.070257 * math.sin(B)
         - 0.006758 * math.cos(2 * B)
         + 0.000907 * math.sin(2 * B)
         - 0.002697 * math.cos(3 * B)
         + 0.00148  * math.sin(3 * B))
    return float(δ)


# ---------------- Árnyék detektálás ----------------

def detect_shadow_lines(image_path: str) -> Tuple[Optional[np.ndarray], Optional[Tuple[int,int,int,int]]]:
    """
    Canny + Probabilistic Hough. Visszaadja:
      - lines: alak (N,1,4), int, hogy a GUI-d közvetlen kirajzolhassa,
      - longest: (x1,y1,x2,y2) a leghosszabb vonal vagy None.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None, None

    # enyhe zajszűrés + élek
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    # probabilistic Hough
    raw = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=40, maxLineGap=12)
    if raw is None or len(raw) == 0:
        return None, None

    # leghosszabb vonal kiválasztása
    longest = None
    best_len = -1.0
    for r in raw:
        x1, y1, x2, y2 = r[0]
        L = float(np.hypot(x2 - x1, y2 - y1))
        if L > best_len:
            best_len = L
            longest = (int(x1), int(y1), int(x2), int(y2))

    # lines-t olyan formában adjuk vissza, ahogy a GUI elvárja: (N,1,4)
    lines = np.array(raw, dtype=np.int32)
    return lines, longest


def line_angle_deg(x1: int, y1: int, x2: int, y2: int) -> float:
    """
    Vonal irányszöge fokban, képsíkban (x jobbra, y lefelé).
    """
    angle_rad = math.atan2((y2 - y1), (x2 - x1))
    angle_deg = math.degrees(angle_rad)
    # 0° = vízszintes jobbra; állítsuk 0..360 tartományba
    if angle_deg < 0:
        angle_deg += 360.0
    return angle_deg


# ---------------- FOV becslés (opcionális) ----------------

def estimate_fov_deg(image_path: str) -> float:
    """
    Ha van EXIF FocalLength, kiszámoljuk a vízszintes FOV-ot.
    Ha nincs, default: 60°.
    """
    exif = _read_exif(image_path)
    focal = None
    try:
        fl = exif.get("FocalLength")
        if isinstance(fl, tuple) and len(fl) == 2 and fl[1] != 0:
            focal = fl[0] / fl[1]
        elif fl is not None:
            focal = float(fl)
    except Exception:
        focal = None

    # egyszerű default szenzorszélesség (mm) – mobilszenzor becslés
    if focal:
        sensor_w_mm = 6.4
        fov_rad = 2.0 * math.atan((sensor_w_mm * 0.5) / focal)
        return math.degrees(fov_rad)
    return 60.0


# ---------------- mindent összefogó előkészítő ----------------

def prepare_shadow_data(image_path: str) -> Dict[str, Any]:
    """
    Minden automatikus előkészítés:
      - Hough vonalak + leghosszabb
      - árnyék iránya (deg)
      - árnyékhossz (pix)
      - EXIF dátum -> nap deklináció
      - FOV (ha kell)
    """
    lines, longest = detect_shadow_lines(image_path)

    angle_deg = None
    length_px = None
    if longest is not None:
        x1, y1, x2, y2 = longest
        angle_deg = line_angle_deg(x1, y1, x2, y2)
        length_px = float(np.hypot(x2 - x1, y2 - y1))

    dt_utc = extract_datetime_utc(image_path)
    delta = solar_declination_rad(dt_utc) if dt_utc is not None else None
    fov_deg = estimate_fov_deg(image_path)

    return {
        "detected_lines": lines,          # (N,1,4) vagy None
        "longest_line": longest,          # (x1,y1,x2,y2) vagy None
        "shadow_angle_deg": angle_deg,    # vagy None
        "shadow_length_px": length_px,    # vagy None
        "datetime_utc": dt_utc,           # vagy None
        "delta_rad": delta,               # vagy None
        "fov_deg": fov_deg
    }
