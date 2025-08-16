# -*- coding: utf-8 -*-
# algorithms/shadow.py

import math
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

from .preshadow import (
    CameraSetup,
    prepare_shadow_data,
    solar_declination_rad,
)

# ---------- kis logger a projekt log-formátumához ----------

from time import strftime, localtime

def _log(tag: str, msg: str) -> None:
    print(f"[{strftime('%H:%M:%S', localtime())}] [{tag}] {msg}")


# ---------- fő képletek / segédfüggvények ----------

def _safe_arcsin(x: float) -> float:
    return math.asin(max(-1.0, min(1.0, x)))


def _azimuth_from_world_xy(v_world_unit) -> float:
    """
    Az árnyék (földi sík) iránya világkoordinátában – feltételezve, hogy a z a "felfelé".
    """
    vx, vy = float(v_world_unit[0]), float(v_world_unit[1])
    return math.atan2(vy, vx)


@dataclass
class ShadowInputs:
    # képi mérés
    base_px: Tuple[float, float]
    tip_px: Tuple[float, float]

    # kamera
    width: int
    height: int
    fov_deg: float
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    roll_deg: float = 0.0

    # fizikai/asztro paraméterek
    height_m: Optional[float] = None          # referencia tárgy magassága [m]
    px_per_meter: Optional[float] = None      # földsíkon skála [px/m]
    datetime_utc: Optional[datetime] = None   # készítés ideje (UTC vagy úgy kezeljük)


def compute_latitude(
    shadow_world_unit: Optional[Tuple[float, float, float]] = None,
    h: Optional[float] = None,
    delta_rad: Optional[float] = None,
    *,
    shadow_len_px: Optional[float] = None,
    px_per_meter: Optional[float] = None,
    fallback_azimuth_rad: Optional[float] = None
) -> Optional[float]:
    """
    'Back-compat' wrapper: rugalmas aláírás, hogy ne legyen TypeError, ha a hívó
    nem ad meg minden paramétert. Ha a kritikus adatok hiányoznak, None-t ad vissza,
    és a hívónak kell logolnia.
    """
    # Kritikus inputok ellenőrzése
    if shadow_world_unit is None and fallback_azimuth_rad is None:
        return None
    if h is None or delta_rad is None:
        return None

    # Árnyékhossz méterben (ha megvan), különben csak irányt használunk és elbukunk
    alpha = None
    if shadow_len_px is not None and px_per_meter is not None and px_per_meter > 0:
        L_m = shadow_len_px / px_per_meter
        if L_m > 0:
            alpha = math.atan2(h, L_m)

    if alpha is None:
        # nincs skála → nincs megbízható magasságszög
        return None

    # Azimut a világ-síkban
    if shadow_world_unit is not None:
        A = _azimuth_from_world_xy(shadow_world_unit)
    else:
        A = float(fallback_azimuth_rad)

    # "Nagy" egyenlet (az általad kért formában)
    # φ = arcsin( (sin α − sin δ · sin A) / (cos δ · cos A) )
    num = math.sin(alpha) - math.sin(delta_rad) * math.sin(A)
    den = math.cos(delta_rad) * math.cos(A)
    if abs(den) < 1e-9:
        return None

    phi = _safe_arcsin(num / den)
    return math.degrees(phi)


def run_shadow_analysis(inp: ShadowInputs) -> Dict[str, Any]:
    """
    Magas szintű futtató, amely:
      - előkészíti a kamera/árnyék adatokat (preshadow)
      - kiszámolja a Nap deklinációt (ha van idő)
      - ellenőrzi a skálát (px_per_meter) és a referencia magasságot
      - visszaad szélességi fokot + diagnosztikát
    """
    _log("SHADOW", "Árnyékok elemzése...")

    # Preshadow
    cam = CameraSetup(
        width=inp.width, height=inp.height, fov_deg=inp.fov_deg,
        pitch_deg=inp.pitch_deg, yaw_deg=inp.yaw_deg, roll_deg=inp.roll_deg
    )

    try:
        prep = prepare_shadow_data(inp.base_px, inp.tip_px, cam)
    except Exception as e:
        _log("SHADOW", f"Hiba az előkészítésnél: {e}")
        return {"ok": False, "error": str(e)}

    # Deklináció
    if inp.datetime_utc is None:
        _log("SHADOW", "Hiányzik a dátum/idő → deklináció nem számolható.")
        delta = None
    else:
        delta = solar_declination_rad(inp.datetime_utc)

    # Skála & magasság ellenőrzés
    if inp.height_m is None:
        _log("SHADOW", "Hiányzik a referencia magasság (height_m).")
    if inp.px_per_meter is None or (inp.px_per_meter is not None and inp.px_per_meter <= 0):
        _log("SHADOW", "Hiányzik vagy érvénytelen a px_per_meter (pixel/méter skála).")

    phi = compute_latitude(
        shadow_world_unit=prep["shadow_world_unit"],
        h=inp.height_m,
        delta_rad=delta,
        shadow_len_px=prep["shadow_len_px"],
        px_per_meter=inp.px_per_meter,
        fallback_azimuth_rad=_azimuth_from_world_xy(prep["shadow_world_unit"])
    )

    if phi is None:
        _log("SHADOW", "Nem sikerült szélességi fokot számolni (hiányzó/elégtelen bemenet).")
        return {
            "ok": False,
            "reason": "missing_inputs_or_degenerate_geometry",
            "needed": {
                "height_m": inp.height_m is not None,
                "datetime_utc": inp.datetime_utc is not None,
                "px_per_meter": inp.px_per_meter is not None and inp.px_per_meter > 0
            },
            "diagnostics": {
                "shadow_len_px": prep["shadow_len_px"],
                "azimuth_img_rad": prep["azimuth_img_rad"]
            }
        }

    _log("SHADOW", f"Becsült szélességi fok: {phi:.3f}°")
    return {
        "ok": True,
        "latitude_deg": float(phi),
        "diagnostics": {
            "shadow_len_px": prep["shadow_len_px"],
            "azimuth_img_rad": prep["azimuth_img_rad"],
            "pitch_deg": inp.pitch_deg,
            "yaw_deg": inp.yaw_deg,
            "roll_deg": inp.roll_deg,
            "fov_deg": inp.fov_deg
        }
    }
