from imports import *

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

def correct_plate(text):
    """Rendszám karakterhibák javítása"""
    if text is None:
        return None, None
    
    text = text.strip().upper()
    
    # Gyakori OCR hibák javítása
    common_errors = {
        'R': 'H',  # R → H (gyakori hiba)
        'O': '0',  # O → 0
        'I': '1',  # I → 1
        'S': '5',  # S → 5
        'B': '8',  # B → 8
        'Z': '2',  # Z → 2
    }
    
    # Karakterenkénti javítás
    corrected_text = ''.join(common_errors.get(c, c) for c in text)
    
    # Országkód és rendszám szétválasztása
    # Tipikus formátumok: "H ABC123", "D-ABC123", "H:ABC123"
    country_code_pattern = r'^([A-Z]{1,3})[\s\-:]*([A-Z0-9]+)$'
    match = re.match(country_code_pattern, corrected_text)
    
    if match:
        country_code = match.group(1)
        plate_number = match.group(2)
        
        # Országkód érvényesítése (ismert európai országkódok)
        valid_country_codes = ['H', 'D', 'A', 'I', 'F', 'GB', 'E', 'PL', 'CZ', 'SK', 'RO', 'HR']
        if country_code not in valid_country_codes:
            # Ha nem ismert országkód, akkor valószínűleg OCR hiba
            # Egyesítjük a szöveget és újra próbálkozunk
            plate_number = corrected_text.replace(' ', '')
            country_code = None
    else:
        # Ha nincs explicit országkód, csak a rendszám
        country_code = None
        plate_number = corrected_text.replace(' ', '')
    
    # Csak érvényes karaktereket tartunk meg
    valid_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    if plate_number:
        plate_number = ''.join(c for c in plate_number if c in valid_chars)
    
    return plate_number, country_code

def detect_plates_simple(img):
    """Egyszerűsített rendszám detektálás"""
    # Kép előfeldolgozása
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    
    # Élek detektálása
    edged = cv2.Canny(gray, 30, 200)
    
    # Kontúrok keresése - egyszerűsített változat
    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
    
    plate_contours = []
    for contour in contours:
        # Kontúr közelítése
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        
        # Ha négyszög alakú, akkor valószínűleg rendszám
        if len(approx) == 4:
            # Szűrés aspektus arány alapján (rendszámok tipikusan szélesek)
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h
            if 2.0 <= aspect_ratio <= 5.0:  # Rendszám tipikus aspektus aránya
                plate_contours.append(approx)
    
    return plate_contours

def extract_plate(img, contour):
    """Rendszám kivágása a kontúr alapján"""
    # Get the bounding rect
    x, y, w, h = cv2.boundingRect(contour)
    
    # Kivágjuk a területet
    plate_img = img[y:y+h, x:x+w]
    
    return plate_img, (x, y, w, h)

def preprocess_plate(plate_img):
    """Rendszám előfeldolgozása OCR-hez"""
    # Átalakítás szürkeárnyalatossá
    gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
    
    # Zaj csökkentése
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    
    # Kontraszt növelése
    gray = cv2.equalizeHist(gray)
    
    # Adaptív küszöbölés - jobb eredményt ad változó megvilágításnál
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY, 11, 2)
    
    # Morfológiai műveletek a zaj eltávolítására
    kernel = np.ones((2, 2), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    
    return thresh

def recognize_plate_text(plate_img):
    """Szöveg felismerése a rendszámon (országkóddal együtt)"""
    # Előfeldolgozás
    processed = preprocess_plate(plate_img)
    
    # Különböző OCR konfigurációk kipróbálása
    configs = [
        r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        r'--oem 3 --psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    ]
    
    best_text = ""
    for config in configs:
        text = pytesseract.image_to_string(processed, config=config).strip()
        if len(text) > len(best_text):
            best_text = text
    
    return correct_plate(best_text)

def detect_country_code_from_visual(plate_img):
    """Országkód vizuális detektálása a rendszám bal oldalán"""
    try:
        # A rendszám bal oldalának kivágása (országkód terület)
        height, width = plate_img.shape[:2]
        left_portion = plate_img[:, :width//3]  # Bal oldali 33%
        
        # Előfeldolgozás az országkód részre
        gray_left = cv2.cvtColor(left_portion, cv2.COLOR_BGR2GRAY)
        
        # Kontraszt növelése
        gray_left = cv2.equalizeHist(gray_left)
        
        # Adaptív küszöbölés
        thresh_left = cv2.adaptiveThreshold(gray_left, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                          cv2.THRESH_BINARY, 11, 2)
        
        # OCR csak a bal oldalon, csak betűkre korlátozva
        custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        country_text = pytesseract.image_to_string(thresh_left, config=custom_config)
        
        country_text = country_text.strip().upper()
    
        
        # Csak érvényes országkódok elfogadása
        valid_country_codes = ['H', 'D', 'A', 'I', 'F', 'GB', 'E', 'PL', 'CZ', 'SK', 'RO', 'HR']
        if country_text in valid_country_codes:
            return country_text
        
        return None
    except:
        return None

def enhance_country_code_detection(plate_img, initial_country_code):
    """További feldolgozás az országkód pontosabb detektálásához"""
    if initial_country_code:
        return initial_country_code
    
    try:
        # További képfeldolgozási lépések
        height, width = plate_img.shape[:2]
        
        # Különböző régiók kipróbálása
        regions = [
            plate_img[:, :width//4],    # Bal 25%
            plate_img[:, :width//3],    # Bal 33%
            plate_img[:, :width//2],    # Bal 50%
        ]
        
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

def query_online_database(plate_number, country_code=None, api_key=None):
    """
    Online adatbázis lekérdezése a rendszámhoz országkóddal együtt
    """
    try:
        # Szimulált válasz - országkóddal bővítve
        simulated_data = {
            "H-ABC123": {"owner": "Kovács János", "color": "Kék", "year": 2018, "make": "Toyota", "model": "Corolla", "country": "Hungary"},
            "H-RAP235": {"owner": "Kovács János", "color": "Kék", "year": 2018, "make": "Toyota", "model": "Corolla", "country": "Hungary"},
            "D-XYZ789": {"owner": "Nagy Eszter", "color": "Fehér", "year": 2020, "make": "Volkswagen", "model": "Golf", "country": "Germany"},
            "A-DEF456": {"owner": "Szabó István", "color": "Piros", "year": 2019, "make": "BMW", "model": "3 Series", "country": "Austria"},
        }
        
        # Kulcs generálása országkóddal
        key = f"{country_code}-{plate_number}" if country_code else plate_number
        
        if key in simulated_data:
            return simulated_data[key]
        elif plate_number in simulated_data:  # Visszamenőleges kompatibilitás
            return simulated_data[plate_number]
        else:
            return None
            
    except Exception as e:
        print(f"Online query error: {e}")
        return None

def plate_recognition(image_path, db_path="plates.db", use_online_db=False, api_key=None):
    """Rendszám felismerés és adatbázis lekérdezés országkóddal"""
    try:
        # Kép betöltése
        if not os.path.exists(image_path):
            print(f"[ERROR] A képfájl nem található: {image_path}")
            return None
            
        img = cv2.imread(image_path)
        if img is None:
            print("[ERROR] Nem sikerült betölteni a képet.")
            return None
        
        # Kép méretének csökkentése nagy felbontású képekhez
        height, width = img.shape[:2]
        if width > 1000:
            scale = 1000 / width
            new_width = 1000
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height))
        
        # Rendszámok detektálása
        plate_contours = detect_plates_simple(img)
        
        if not plate_contours:
            print("[INFO] Nem található rendszám a képen.")
            return None
        
        results = []
        
        # Minden detektált rendszám feldolgozása
        for i, contour in enumerate(plate_contours):
            # Rendszám kivágása
            plate_img, (x, y, w, h) = extract_plate(img, contour)
            
            # Szöveg felismerése
            plate_text, country_code = recognize_plate_text(plate_img)
            
            # További országkód detektálás
            country_code = enhance_country_code_detection(plate_img, country_code)
            
            if not plate_text or len(plate_text) < 4:  # Legalább 4 karakter legyen
                continue
            
            # Lokális adatbázis lekérdezés
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Keresés rendszám alapján, figyelembe véve az országkódot is
            if country_code:
                c.execute("SELECT * FROM cars WHERE plate=? OR plate=?", 
                         (plate_text, f"{country_code}-{plate_text}"))
            else:
                c.execute("SELECT * FROM cars WHERE plate=?", (plate_text,))
                
            db_result = c.fetchone()
            conn.close()
            
            # Online adatbázis lekérdezés (ha engedélyezve van)
            online_info = None
            if use_online_db:
                online_info = query_online_database(plate_text, country_code, api_key)
            
            # Eredmény összeállítása
            plate_data = {
                "plate": plate_text,
                "country_code": country_code,
                "position": (x, y, w, h),
                "local_db_info": db_result,
                "online_info": online_info
            }
            
            results.append(plate_data)
        
        return results

    except Exception as e:
        print(f"[PLATE] Kritikus hiba: {e}")
        import traceback
        traceback.print_exc()
        return None