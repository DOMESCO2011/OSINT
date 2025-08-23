import cv2
import numpy as np
from PIL import Image
import pytesseract
import sqlite3

def create_db(db_path="plates.db"):
    """Adatbázis létrehozása (ha még nem létezik)"""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS cars (
                        plate TEXT PRIMARY KEY,
                        owner TEXT,
                        color TEXT,
                        year INT
                    )""")
        conn.commit()
        conn.close()
        print("[DB] Adatbázis kész.")
    except Exception as e:
        print(f"[DB] Hiba: {e}")

def correct_plate(text):
    """Rendszám karakterhibák javítása"""
    if text is None:
        return None
    return text.strip().upper().replace("O","0").replace("I","1").replace(" ","")

def plate_recognition(image_path, db_path="plates.db"):
    """Rendszám felismerés és adatbázis lekérdezés"""
    try:
        # Kép betöltése
        image_cv = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)

        # Előfeldolgozás
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        _, thresh = cv2.threshold(blur, 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # OCR használata Tesseract-tal
        pil_img = Image.fromarray(thresh)
        text = pytesseract.image_to_string(pil_img, config='--psm 7')
        plate = correct_plate(text)

        if not plate:
            return {"plate": None, "db_info": None}

        # Adatbázis lekérdezés
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM cars WHERE plate=?", (plate,))
        result = c.fetchone()
        conn.close()

        return {"plate": plate, "db_info": result}

    except Exception as e:
        print(f"[PLATE] Hiba: {e}")
        return None

# Példa használat
if __name__ == "__main__":
    create_db()  # egyszer kell csak futtatni az adatbázis létrehozásához
    result = plate_recognition("rendszam.jpg")
    print(result)
