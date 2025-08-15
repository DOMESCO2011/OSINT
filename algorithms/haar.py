import cv2
import numpy as np

def haar_detection(image_path):
    """Haar Cascade arc- és szemfelismerés (visszaadja a koordinátákat)"""
    try:
        # Kép betöltése
        image_cv = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)

        # Cascade modellek betöltése
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

        # Arcok és szemek detektálása
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        results = {"faces": [], "eyes": []}

        for (x, y, w, h) in faces:
            results["faces"].append((x, y, w, h))
            
            # Szemek keresése az arc területén belül
            roi_gray = gray[y:y+h, x:x+w]
            eyes = eye_cascade.detectMultiScale(roi_gray)
            for (ex, ey, ew, eh) in eyes:
                results["eyes"].append((x+ex, y+ey, ew, eh))

        return results

    except Exception as e:
        print(f"[HAAR] Hiba: {e}")
        return None