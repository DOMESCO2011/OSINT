# -*- coding: utf-8 -*-
# algorithms/preshadow.py

import math
from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional
from datetime import datetime

import numpy as np


# ---------- HELPER: intrinsics / rotations ----------

def get_intrinsic_matrix(fov_deg: float, width: int, height: int) -> np.ndarray:
    """
    Egyszerű pinhole intrinsics. A fov_deg itt VÍZSZINTES FOV-ként értelmezzük.
    """
    fov_rad = math.radians(fov_deg)
    fx = width / (2.0 * math.tan(fov_rad / 2.0))
    fy = fx  # feltételezzük square pixel-t
    cx = width / 2.0
    cy = height / 2.0
    return np.array([[fx, 0.0, cx],
                     [0.0, fy, cy],
                     [0.0, 0.0, 1.0]], dtype=np.float64)


def rotation_matrix(pitch_deg: float, yaw_deg: float, roll_deg: float) -> np.ndarray:
    """
    R = Rz(roll) * Ry(yaw) * Rx(pitch) konvenció; fok → radián.
    """
    px = math.radians(pitch_deg)
    yw = math.radians(yaw_deg)
    rl = math.radians(roll_deg)

    Rx = np.array([[1, 0, 0],
                   [0, math.cos(px), -math.sin(px)],
                   [0, math.sin(px),  math.cos(px)]], dtype=np.float64)
    Ry = np.array([[ math.cos(yw), 0, math.sin(yw)],
                   [0, 1, 0],
                   [-math.sin(yw), 0, math.cos(yw)]], dtype=np.float64)
    Rz = np.array([[math.cos(rl), -math.sin(rl), 0],
                   [math.sin(rl),  math.cos(rl), 0],
                   [0, 0, 1]], dtype=np.float64)
    return Rz @ Ry @ Rx


# ---------- HELPER: sun declination ----------

def solar_declination_rad(t_utc: datetime) -> float:
    """
    Nap deklináció radiánban (Spencer-szerű közelítés).
    t_utc: timezone-aware UTC datetime, de elfogadunk naive datetime-et is (úgy kezeljük, mint UTC).
    """
    if t_utc.tzinfo is not None:
        n = int(t_utc.timetuple().tm_yday)
    else:
        n = int(t_utc.timetuple().tm_yday)
    B = 2.0 * math.pi * (n - 1) / 365.0
    delta = (0.006918
             - 0.399912 * math.cos(B)
             + 0.070257 * math.sin(B)
             - 0.006758 * math.cos(2 * B)
             + 0.000907 * math.sin(2 * B)
             - 0.002697 * math.cos(3 * B)
             + 0.00148  * math.sin(3 * B))
    return float(delta)


# ---------- PRESHADOW PIPE ----------

@dataclass
class CameraSetup:
    width: int
    height: int
    fov_deg: float
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    roll_deg: float = 0.0


def shadow_vector_world_from_pixels(
    base_px: Tuple[float, float],
    tip_px: Tuple[float, float],
    K: np.ndarray,
    R: np.ndarray
) -> Tuple[np.ndarray, float, float]:
    """
    Pixelből világkoordinátás irány (egységvektor), + pixelhossz és kép-sík azimut.
    Megjegyzés: a hosszt MÉTERRE külön skálázni kell (px_per_meter-rel).
    """
    u0, v0 = base_px
    u1, v1 = tip_px
    v_img = np.array([u1 - u0, v1 - v0, 0.0], dtype=np.float64)
    length_px = float(np.hypot(v_img[0], v_img[1]))
    if length_px == 0.0:
        raise ValueError("[PRESHADOW] üres (0 hosszú) árnyékvektor")

    # homogén irány (képsíkban) → kamera tér
    p0_cam = np.linalg.inv(K) @ np.array([u0, v0, 1.0], dtype=np.float64)
    p1_cam = np.linalg.inv(K) @ np.array([u1, v1, 1.0], dtype=np.float64)
    v_cam = p1_cam - p0_cam  # irány a kamera térben
    v_world = np.linalg.inv(R) @ v_cam
    # normalizálás iránynak
    norm = float(np.linalg.norm(v_world))
    if norm == 0.0:
        raise ValueError("[PRESHADOW] degenerált világvektor")
    v_world_unit = v_world / norm

    # képsík azimut (diagnosztika)
    az_img = math.atan2(v_img[1], v_img[0])

    return v_world_unit, length_px, az_img


def prepare_shadow_data(
    base_px: Tuple[float, float],
    tip_px: Tuple[float, float],
    cam: CameraSetup
) -> Dict[str, Any]:
    """
    Előkészítés: K, R, világvektor, px-hossz, azimut.
    """
    K = get_intrinsic_matrix(cam.fov_deg, cam.width, cam.height)
    R = rotation_matrix(cam.pitch_deg, cam.yaw_deg, cam.roll_deg)
    v_world, length_px, az_img = shadow_vector_world_from_pixels(base_px, tip_px, K, R)
    return {
        "K": K,
        "R": R,
        "shadow_world_unit": v_world,
        "shadow_len_px": length_px,
        "azimuth_img_rad": az_img,
        "cam": cam,
    }
