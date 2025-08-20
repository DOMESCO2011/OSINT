import math
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


def _weighted_orientation_deg(angles_deg: List[float], weights: List[float]) -> Optional[float]:
    """Domináns orientáció 0-180° tartományban (iránytól független),
    vonalhosszakkal súlyozva. Ha nincs értelmes adat, None."""
    if not angles_deg or not any(w > 0 for w in weights):
        return None
    # 180°-periodikus mennyiség → 2θ trükk
    c = 0.0
    s = 0.0
    for a, w in zip(angles_deg, weights):
        theta2 = math.radians(2.0 * a)
        c += w * math.cos(theta2)
        s += w * math.sin(theta2)
    if c == 0 and s == 0:
        return None
    ori_rad = 0.5 * math.atan2(s, c)
    ori_deg = math.degrees(ori_rad)
    # normalizálás 0..180
    ori_deg = (ori_deg + 180.0) % 180.0
    return float(ori_deg)


def detect_shadow(
    image_path: str,
    canny_low: int = 50,
    canny_high: int = 150,
    hough_threshold: int = 80,
    min_line_length_ratio: float = 0.1,
    max_line_gap: int = 10,
    vertical_tolerance_deg: float = 35.0  # Új paraméter: tolerancia a függőleges vonalakhoz
) -> Dict:
    """
    Árnyékvonalak detektálása, domináns árnyék-orientáció és roll (kamera forgatás) becslése.

    Visszatérés:
      {
        "shadow_direction": <float|None>,   # fok, 0..180
        "detected_lines": [ [[x1,y1,x2,y2]], ... ],
        "estimated_latitude": None,
        "roll_deg": <float|None>            # Új: a kamera roll szöge (fokban)
      }
    """
    # [A meglévő képbetöltés és előfeldolgozás változatlan]
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Kép nem olvasható: {image_path}")
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, canny_low, canny_high)
    min_len = int(min(h, w) * max(0.0, min_line_length_ratio))
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180.0,
        threshold=hough_threshold,
        minLineLength=max(10, min_len),
        maxLineGap=max_line_gap,
    )

    if lines is None or len(lines) == 0:
        return {
            "shadow_direction": None,
            "detected_lines": [],
            "estimated_latitude": None,
            "roll_deg": None  # Új
        }

    angles_deg: List[float] = []
    lengths: List[float] = []
    detected_lines: List[List[List[int]]] = []
    vertical_angles: List[float] = []   # Új: csak a függőleges vonalak szögei
    vertical_weights: List[float] = []  # Új: a függőleges vonalak súlyai (hosszuk)

    for l in lines:
        x1, y1, x2, y2 = map(int, l[0])
        dx = x2 - x1
        dy = y2 - y1
        length = float(math.hypot(dx, dy))
        if length < max(10.0, 0.02 * (h + w)):
            continue
        angle = math.degrees(math.atan2(dy, dx))
        angle = (angle + 180.0) % 180.0

        angles_deg.append(angle)
        lengths.append(length)
        detected_lines.append([[x1, y1, x2, y2]])

        # Új: Függőleges vonalak kiválogatása a roll számításához
        # A függőleges irány 90 fok. +/- tolerancia.
        if abs(angle - 90.0) <= vertical_tolerance_deg:
            vertical_angles.append(angle)
            vertical_weights.append(length)

    shadow_dir = _weighted_orientation_deg(angles_deg, lengths) if angles_deg else None

    # Új: Roll számítás a függőleges vonalakból
    roll_deg = None
    if vertical_angles:
        # Minden vonal eltérése a 90 fokos ideálistól
        deviations = [angle - 90.0 for angle in vertical_angles]
        # Súlyozott átlag számítás a vonalhosszakkal
        total_weight = sum(vertical_weights)
        roll_deg = sum(dev * weight for dev, weight in zip(deviations, vertical_weights)) / total_weight
        # A roll értéke most az eltérés átlaga. Pozitív: az óramutató járásával megegyező forgatás.

    return {
        "shadow_direction": shadow_dir,
        "detected_lines": detected_lines,
        "estimated_latitude": None,
        "roll_deg": roll_deg  # Új
    }

def detect_shadow(
    image_path: str,
    canny_low: int = 50,
    canny_high: int = 150,
    hough_threshold: int = 80,
    min_line_length_ratio: float = 0.1,
    max_line_gap: int = 10,
) -> Dict:
    """
    Árnyékvonalak detektálása és domináns árnyék-orientáció becslése.

    Visszatérés:
      {
        "shadow_direction": <float|None>,   # fok, 0..180 (kép koordinátarendszerben)
        "detected_lines": [ [[x1,y1,x2,y2]], ... ],  # HoughLinesP formátumhoz hasonló, hogy a main-ben a line[0] működjön
        "estimated_latitude": None           # helykitöltő kulcs a main kompatibilitás miatt
      }
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Kép nem olvasható: {image_path}")

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Kontrasztjavítás és zajcsökkentés
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Éldetektálás
    edges = cv2.Canny(gray, canny_low, canny_high)

    # Hough transform vonalakra
    min_len = int(min(h, w) * max(0.0, min_line_length_ratio))
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180.0,
        threshold=hough_threshold,
        minLineLength=max(10, min_len),
        maxLineGap=max_line_gap,
    )

    if lines is None or len(lines) == 0:
        return {
            "shadow_direction": None,
            "detected_lines": [],
            "estimated_latitude": None,
        }

    # Szögek és hosszok gyűjtése
    angles_deg: List[float] = []
    lengths: List[float] = []
    detected_lines: List[List[List[int]]] = []  # [[x1,y1,x2,y2]] alak a main-hez

    for l in lines:
        x1, y1, x2, y2 = map(int, l[0])
        dx = x2 - x1
        dy = y2 - y1
        length = float(math.hypot(dx, dy))
        if length < max(10.0, 0.02 * (h + w)):
            continue
        angle = math.degrees(math.atan2(dy, dx))  # -180..180
        angle = (angle + 180.0) % 180.0           # 0..180 (irányt elhagyjuk)

        angles_deg.append(angle)
        lengths.append(length)
        detected_lines.append([[x1, y1, x2, y2]])

    if not angles_deg:
        return {
            "shadow_direction": None,
            "detected_lines": [],
            "estimated_latitude": None,
        }

    shadow_dir = _weighted_orientation_deg(angles_deg, lengths)

    return {
        "shadow_direction": shadow_dir,
        "detected_lines": detected_lines,
        "estimated_latitude": None,
    }
