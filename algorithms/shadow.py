# -*- coding: utf-8 -*-
# algorithms/shadow.py

import math
from typing import Optional, Dict, Any
from .preshadow import prepare_shadow_data

# Ha nincs kalibráció, valami default px/m skála kell a magasság–árnyék arányhoz.
DEFAULT_PX_PER_METER = 100.0
DEFAULT_OBJECT_HEIGHT_M = 1.70  # "átlagos ember" fallback


def _estimate_latitude_from_shadow(
    shadow_len_px: float,
    delta_rad: float,
    *,
    object_height_m: float = DEFAULT_OBJECT_HEIGHT_M,
    px_per_meter: float = DEFAULT_PX_PER_METER
) -> Optional[float]:
    """
    Egyszerű trig: alpha = arctan(H / L), phi = 90° - alpha + delta.
    Itt L pix → méter skálázás szükséges (px_per_meter).
    Ha bármelyik kritikus adat hiányzik / invalid, None-t adunk.
    """
    if shadow_len_px is None or delta_rad is None:
        return None
    if px_per_meter is None or px_per_meter <= 0:
        return None
    if object_height_m is None or object_height_m <= 0:
        return None

    L_m = shadow_len_px / px_per_meter
    if L_m <= 0:
        return None

    alpha = math.atan(object_height_m / L_m)           # nap magasságszög
    phi_rad = (math.pi / 2.0) - alpha + float(delta_rad)
    return math.degrees(phi_rad)


def compute_latitude(image_path: Optional[str] = None,
                     *,
                     object_height_m: float = DEFAULT_OBJECT_HEIGHT_M,
                     px_per_meter: float = DEFAULT_PX_PER_METER,
                     delta_rad: Optional[float] = None) -> Dict[str, Any]:
    """
    GUI-barát wrapper:
      - Ha image_path-et kap, mindent automatikusan előkészít és visszaad egy dict-et:
          {
            "shadow_direction": float | None,  # fok
            "estimated_latitude": float | None,
            "detected_lines": np.ndarray | None  # (N,1,4)
          }
      - Ha nincs kép, csak paraméteres módban használható (nem része a te GUI-nak).
    """
    if image_path is None:
        # Paraméteres mód – itt nem kell a te GUI-dnak
        return {"shadow_direction": None, "estimated_latitude": None, "detected_lines": None}

    prep = prepare_shadow_data(image_path)

    # Árnyék iránya (deg) – a GUI-d ezt kiírja és vonalakat rajzol
    angle_deg = prep.get("shadow_angle_deg")
    lines = prep.get("detected_lines")

    # Szélességi fok becslés – csak ha van deklináció és árnyékhossz
    delta = delta_rad if delta_rad is not None else prep.get("delta_rad")
    lat = _estimate_latitude_from_shadow(
        prep.get("shadow_length_px"),
        delta,
        object_height_m=object_height_m,
        px_per_meter=px_per_meter
    )

    # A GUI-d "if not shadow_results or shadow_results['shadow_direction'] is None"
    # tesztet használ. Ehhez biztosan adjunk vissza dict-et és a kulcsokat.
    return {
        "shadow_direction": angle_deg,
        "estimated_latitude": None if lat is None else round(float(lat), 2),
        "detected_lines": lines
    }
