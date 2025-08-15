import cv2
import numpy as np
import math

def analyze_shadow(image_path):
    """Árnyék alapú helymeghatározás és elemzés"""
    try:
        # Kép betöltése
        img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        
        # Árnyék detektálás
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        # Vonalak detektálása (Hough transzformáció)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, 
                              minLineLength=100, maxLineGap=10)
        
        if lines is None:
            return {"shadow_direction": None, "estimated_latitude": None}
        
        # Árnyék irányának meghatározása (átlagos vonal irány)
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            angles.append(angle)
        
        if not angles:
            return {"shadow_direction": None, "estimated_latitude": None}
        
        avg_angle = np.mean(angles)
        
        # Becsült szélességi fok (nagyon egyszerűsített modell)
        estimated_lat = None
        if -45 <= avg_angle <= 45:   # Dél környéke
            estimated_lat = 47.0  # Példaérték (Budapest)
        elif 45 < avg_angle < 135:    # Kelet
            estimated_lat = 40.0      # Példaérték
        else:                        # Nyugat/Észak
            estimated_lat = 50.0      # Példaérték
            
        return {
            "shadow_direction": avg_angle,
            "estimated_latitude": estimated_lat,
            "detected_lines": lines
        }
        
    except Exception as e:
        print(f"[SHADOW] Hiba: {e}")
        return None
