import math
from typing import List, Dict, Optional

# ============ CSILLAGÁSZATI ALAP FÜGGVÉNYEK ============

def solar_declination(day_of_year: int) -> float:
    return math.radians(23.44) * math.sin(math.radians(360 / 365.0 * (day_of_year - 81)))

def equation_of_time(day_of_year: int) -> float:
    B = math.radians(360 / 365.0 * (day_of_year - 81))
    return 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)

def hour_angle(local_time_hours: float, utc_offset: int, day_of_year: int, lon_deg: float, use_eot=True) -> float:
    eot = equation_of_time(day_of_year) if use_eot else 0.0
    lon_tz = 15.0 * utc_offset
    lst = local_time_hours + (eot + 4 * (lon_deg - lon_tz)) / 60.0
    return math.radians(15.0 * (lst - 12.0))

# ============ IMU / KORREKCIÓ ============

def effective_height(height: float, pitch_deg: float = 0.0, roll_deg: float = 0.0) -> float:
    tilt = math.acos(
        max(-1.0, min(1.0, math.cos(math.radians(pitch_deg)) * math.cos(math.radians(roll_deg))))
    )
    return height * math.cos(tilt)

def effective_shadow(shadow: float, ground_pitch_deg: float = 0.0, ground_roll_deg: float = 0.0) -> float:
    ground_tilt = math.acos(
        max(-1.0, min(1.0, math.cos(math.radians(ground_pitch_deg)) * math.cos(math.radians(ground_roll_deg))))
    )
    return shadow * math.cos(ground_tilt)

def elevation_from_shadow(height: float, shadow: float) -> float:
    return math.atan2(height, shadow)

def refraction_deg(elev_deg: float) -> float:
    h = max(elev_deg, 0.01)
    R = 1.02 / math.tan(math.radians(h + 10.3 / (h + 5.11))) / 60.0
    return R

# ============ SZÉLESSÉG SZÁMÍTÁS ============

def latitude_from_single(h_rad: float, delta_rad: float, H_rad: float) -> float:
    phi = 0.5
    for _ in range(30):
        f = math.sin(h_rad) - (
            math.sin(phi) * math.sin(delta_rad) + math.cos(phi) * math.cos(delta_rad) * math.cos(H_rad)
        )
        df = -(
            math.cos(phi) * math.sin(delta_rad)
            - math.sin(phi) * math.cos(delta_rad) * math.cos(H_rad)
        )
        if abs(df) < 1e-12:
            break
        step = f / df
        phi -= step
        if abs(step) < 1e-10:
            break
    return phi

def fit_lat_lonoffset(samples: List[Dict], utc_offset: int):
    phi = math.radians(47.0)
    dlon = 0.0
    for _ in range(80):
        Fphi = Flon = 0.0
        Gpp = Gpl = Gll = 0.0
        for s in samples:
            delta = solar_declination(s['day_of_year'])
            H = hour_angle(s['local_hour'], utc_offset, s['day_of_year'], lon_deg=15 * utc_offset + dlon)
            model = math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.cos(H)
            r = math.sin(s['h_rad']) - model
            dmodel_dphi = math.cos(phi) * math.sin(delta) - math.sin(phi) * math.cos(delta) * math.cos(H)
            dmodel_dlon = math.cos(phi) * math.cos(delta) * math.sin(H) * math.radians(1.0)
            Fphi += r * dmodel_dphi
            Flon += r * dmodel_dlon
            Gpp += dmodel_dphi ** 2
            Gpl += dmodel_dphi * dmodel_dlon
            Gll += dmodel_dlon ** 2
        det = Gpp * Gll - Gpl * Gpl
        if abs(det) < 1e-12:
            break
        dphi = (Fphi * Gll - Flon * Gpl) / det
        dlon = dlon + (Flon * Gpp - Fphi * Gpl) / det
        phi = phi + dphi
        if abs(dphi) < 1e-10:
            break
    return phi, dlon

# ============ FŐ OSZTÁLY ============

class ShadowCalculator:
    def __init__(self, utc_offset: int = 1, longitude: Optional[float] = None):
        self.utc_offset = utc_offset
        self.longitude = longitude

    def process_measurement(self, m: Dict) -> Dict:
        H_eff = effective_height(m['height'], m.get('pitch', 0), m.get('roll', 0))
        S_eff = effective_shadow(m['shadow'], m.get('ground_pitch', 0), m.get('ground_roll', 0))
        h_rad = elevation_from_shadow(H_eff, S_eff)
        h_deg = math.degrees(h_rad)
        h_corr = h_deg + refraction_deg(h_deg)

        delta = solar_declination(m['day_of_year'])
        lon = self.longitude if self.longitude is not None else 15 * self.utc_offset
        H = hour_angle(m['local_hour'], self.utc_offset, m['day_of_year'], lon)
        phi = latitude_from_single(math.radians(h_corr), delta, H)

        return {
            'latitude_deg': float(math.degrees(phi)),
            'elevation_deg': float(h_corr),
            'declination_deg': float(math.degrees(delta)),
            'hour_angle_deg': float(math.degrees(H))
        }

    def process_multiple(self, measurements: List[Dict]) -> Dict:
        samples = []
        for m in measurements:
            H_eff = effective_height(m['height'], m.get('pitch', 0), m.get('roll', 0))
            S_eff = effective_shadow(m['shadow'], m.get('ground_pitch', 0), m.get('ground_roll', 0))
            h_rad = elevation_from_shadow(H_eff, S_eff)
            h_deg = math.degrees(h_rad)
            h_corr = h_deg + refraction_deg(h_deg)
            samples.append({
                'h_rad': math.radians(h_corr),
                'local_hour': m['local_hour'],
                'day_of_year': m['day_of_year']
            })

        phi, dlon = fit_lat_lonoffset(samples, self.utc_offset)
        return {
            'latitude_deg': float(math.degrees(phi)),
            'longitude_offset_deg': float(dlon)
        }
