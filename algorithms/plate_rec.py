import os
import re
import cv2
import numpy as np
import sqlite3
import pytesseract
import easyocr

# EasyOCR reader egyszeri inicializálás
reader = easyocr.Reader(['en'], gpu=False)

# ------------------------------
# SZIMULÁLT ADATBÁZIS
# ------------------------------
SIMULATED_DB = {
    "H-ABC123": {"owner": "Kovács János", "color": "Kék", "year": 2018, "make": "Toyota", "model": "Corolla"},
    "H-RAP235": {"owner": "Nagy Péter", "color": "Fekete", "year": 2019, "make": "Ford", "model": "Focus"},
    "D-XYZ789": {"owner": "Müller Anna", "color": "Fehér", "year": 2020, "make": "Volkswagen", "model": "Golf"},
}

# ------------------------------
# ADATBÁZIS LÉTREHOZÁS (OPCIONÁLIS)
# ------------------------------
def create_db(db_path="plates.db"):
    """Adatbázis létrehozása (ha még nem létezik)"""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS cars (
                        plate TEXT PRIMARY KEY,
                        owner TEXT,
                        color TEXT,
                        year INT,
                        make TEXT,
                        model TEXT,
                        country_code TEXT
                    )""")
        conn.commit()
        conn.close()
        print("[DB] Adatbázis kész.")
    except Exception as e:
        print(f"[DB] Hiba: {e}")

# ------------------------------
# RENDSZÁM NORMALIZÁLÁS
# ------------------------------
def correct_plate(text):
    if text is None:
        return None, None
    text = text.strip().upper().replace(" ", "")

    # Első karakter javítása I -> R ha kell
    if len(text) >= 4 and text[0] == "I" and text[1:4].isalpha():
        text = "R" + text[1:]

    # Országkód és rendszám szétválasztása
    country_code_pattern = r'^([A-Z]{1,3})[\-]*([A-Z0-9]+)$'
    match = re.match(country_code_pattern, text)
    if match:
        country_code = match.group(1)
        plate_number = match.group(2)
    else:
        country_code = None
        plate_number = text

    valid_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
    plate_number = ''.join(c for c in plate_number if c in valid_chars)
    return plate_number, country_code

# ------------------------------
# ELŐFELDOLGOZÁS OCR-HEZ
# ------------------------------
def preprocess_plate(plate_img):
    gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    gray = cv2.equalizeHist(gray)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY, 11, 2)
    kernel = np.ones((2, 2), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    return thresh

# ------------------------------
# MULTI-OCR FUNKCIÓ
# ------------------------------
def ocr_multi_method(plate_img):
    candidates = []

    # 1. Tesseract
    processed = preprocess_plate(plate_img)
    configs = [
        r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-',
        r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-',
        r'--oem 3 --psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
    ]
    for config in configs:
        text = pytesseract.image_to_string(processed, config=config).strip().upper().replace(" ", "")
        if text: candidates.append(text)

    # 2. EasyOCR
    result = reader.readtext(plate_img)
    for bbox, text, conf in result:
        text = text.upper().replace(" ", "")
        if text: candidates.append(text)

    # Legjobb jelölt kiválasztása: legtöbb alfanumerikus karakter
    best_text = ""
    for text in candidates:
        if sum(c.isalnum() for c in text) > sum(c.isalnum() for c in best_text):
            best_text = text

    return correct_plate(best_text)

# ------------------------------
# RENDSZÁM DETEKTÁLÁS
# ------------------------------
def detect_plates_simple(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    edged = cv2.Canny(gray, 30, 200)
    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    plate_contours = []
    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h
            if 2.0 <= aspect_ratio <= 5.0:
                plate_contours.append(approx)
    return plate_contours

def extract_plate(img, contour):
    x, y, w, h = cv2.boundingRect(contour)
    plate_img = img[y:y+h, x:x+w]
    return plate_img, (x, y, w, h)

def enhance_country_code_detection(plate_img, initial_country_code):
    if initial_country_code:
        return initial_country_code
    try:
        height, width = plate_img.shape[:2]
        regions = [plate_img[:, :width//4], plate_img[:, :width//3], plate_img[:, :width//2]]
        for region in regions:
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (3, 3), 0)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            custom_config = r'--oem 3 --psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            text = pytesseract.image_to_string(thresh, config=custom_config).strip().upper()
            if text in ['H', 'D', 'A', 'I', 'F']:
                return text
        return None
    except:
        return None

# ------------------------------
# TELJES MULTI-OCR + SZIMULÁLT DB
# ------------------------------
def plate_recognition(self, image_path):
    try:
        if not os.path.exists(image_path):
            self.log("error", "[PLATE]", f"A képfájl nem található: {image_path}")
            return None
        img = cv2.imread(image_path)
        if img is None:
            self.log("error", "[PLATE]", "Nem sikerült betölteni a képet.")
            return None

        height, width = img.shape[:2]
        if width > 1000:
            img = cv2.resize(img, (1000, int(height * 1000 / width)))

        plate_contours = detect_plates_simple(img)
        if not plate_contours:
            self.log("info", "[PLATE]", "Nem található rendszám a képen.")
            return None

        results = []
        for contour in plate_contours:
            plate_img, (x, y, w, h) = extract_plate(img, contour)
            plate_text, country_code = ocr_multi_method(plate_img)
            country_code = enhance_country_code_detection(plate_img, country_code)

            if not plate_text or len(plate_text) < 4:
                continue

            plate_data = {
                "plate": plate_text,
                "country_code": country_code,
                "position": (x, y, w, h),
                "local_db_info": SIMULATED_DB.get(f"{country_code}-{plate_text}", None),
                "online_info": None
            }
            results.append(plate_data)

        return results
    except Exception as e:
        import traceback
        self.log("error", "[OSINT]", f"Kritikus hiba: {e}\n{traceback.format_exc()}")
        return None
