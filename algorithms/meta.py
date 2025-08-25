from PIL.ExifTags import TAGS, GPSTAGS
from PIL import Image, ImageTk
import hashlib
import time
import numpy as np
import json
import os

def exif_reading(self, image_path, json_path="exif_results.json"):
    """EXIF + kiterjesztett metaellenőrzés"""
    try:
        self.log("info", "EXIF", f"EXIF/meta ellenőrzés: {image_path}")

        img = Image.open(image_path)
        exif_data = img._getexif()

        result = {
            "image": os.path.basename(image_path),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "exif": {},
            "gps": {},
            "fingerprints": {}
        }

        # --- EXIF feldolgozás ---
        if exif_data:
            gps_info = {}
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                if tag_name == "GPSInfo":
                    for key in value.keys():
                        gps_tag = GPSTAGS.get(key, key)
                        gps_info[gps_tag] = value[key]
                else:
                    result["exif"][tag_name] = str(value)

            if gps_info:
                def convert_to_degrees(value):
                    d, m, s = value
                    return float(d[0] / d[1] + m[0] / m[1] / 60 + s[0] / s[1] / 3600)

                lat = convert_to_degrees(gps_info['GPSLatitude'])
                if gps_info['GPSLatitudeRef'] != "N":
                    lat = -lat

                lon = convert_to_degrees(gps_info['GPSLongitude'])
                if gps_info['GPSLongitudeRef'] != "E":
                    lon = -lon

                result["gps"] = {"latitude": lat, "longitude": lon}
                self.log("success", "EXIF", f"GPS koordináták: {lat:.6f}, {lon:.6f}")
            else:
                self.log("warning", "EXIF", "Nem található GPS információ.")
        else:
            self.log("warning", "EXIF", "Nincsenek EXIF adatok a képben.")

        # --- File hash + fingerprint ---
        self.log("info", "FINGERPRINT", "Ujjlegyomatok elemzése")
        with open(image_path, "rb") as f:
            file_bytes = f.read()
            md5 = hashlib.md5(file_bytes).hexdigest()
            sha256 = hashlib.sha256(file_bytes).hexdigest()
        result["fingerprints"]["md5"] = md5
        result["fingerprints"]["sha256"] = sha256
        self.log("success", "HASH", f"MD5: {md5}, SHA256: {sha256}")

        # --- JPEG quantization tables ---
        if hasattr(img, "quantization") and img.quantization:
            result["fingerprints"]["jpeg_quant_tables"] = str(img.quantization)
            self.log("success", "JPEG", f"Kvantizációs táblák kinyerve: {len(img.quantization)} darab")

        # --- PRNU zajminta ---
        try:
            gray = np.array(img.convert("L"), dtype=np.float32)
            noise = gray - np.mean(gray)
            prnu_signature = np.mean(noise)
            result["fingerprints"]["prnu_signature"] = float(prnu_signature)
            self.log("success", "PRNU", f"Zaj aláírás (átlag): {prnu_signature:.6f}")
        except Exception as e:
            self.log("warning", "PRNU", f"Nem sikerült zajminta: {e}")


        # --- JSON mentés ---
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    all_results = json.loads(content)
                else:
                    all_results = []
        except FileNotFoundError:
            all_results = []


        all_results.append(result)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=4, ensure_ascii=False)

    except Exception as e:
        self.log("error", "EXIF", f"Hiba: {str(e)}")
